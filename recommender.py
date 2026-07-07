from datetime import datetime, time
import os
import json
import requests
import logging
from bandit import load_bandit_weights, get_bandit_boosts

logger = logging.getLogger("recommender")

def is_item_in_promotion(item_name: str, item_category: str, promo_name: str) -> bool:
    if not (item_name and item_category and promo_name):
        return False
        
    promo_name_lower = promo_name.lower()
    item_name_lower = item_name.lower()
    item_category_lower = item_category.lower()
    
    if "burger" in promo_name_lower and "combo" in promo_name_lower:
        # Burger combos only
        return "burger" in item_name_lower and ("combo" in item_name_lower or item_category_lower == "combos")
    elif "bucket" in promo_name_lower:
        return "bucket" in item_name_lower
    elif "free drink" in promo_name_lower:
        # Promotes drinks
        return item_category_lower == "drinks" or any(d in item_name_lower for d in ["pepsi", "7up", "lipton"])
    elif "fried chicken" in promo_name_lower:
        # Fried chicken items only (combos and sides, excluding burger/rice/pasta chicken items)
        is_chicken = "chicken" in item_name_lower or "ga" in item_name_lower
        is_excluded = any(ex in item_name_lower for ex in ["burger", "pasta", "rice", "com"])
        return is_chicken and not is_excluded and item_category_lower in ["combos", "sides"]
    elif "dessert" in promo_name_lower:
        return item_category_lower == "desserts" or "eggtart" in item_name_lower
    elif "sides" in promo_name_lower:
        return item_category_lower == "sides" or "fries" in item_name_lower or "popcorn" in item_name_lower
    return False

def rerank_recommendations(cart_items, active_promotions, affinity_rules, menu_items, timestamp, bandit_weights=None, bandit_mode="expected"):
    if not timestamp:
        return []
        
    try:
        ts_str = timestamp.replace("Z", "+00:00")
        timestamp_dt = datetime.fromisoformat(ts_str)
    except (ValueError, AttributeError, TypeError):
        return []
        
    timestamp_date = timestamp_dt.date()
    time_minutes = timestamp_dt.hour * 60 + timestamp_dt.minute
    
    # Define time category boosts (in minutes)
    lunch_start_min = 11 * 60
    lunch_end_min = 14 * 60
    dinner_start_min = 17 * 60
    dinner_end_min = 21 * 60
    
    is_lunch = lunch_start_min <= time_minutes <= lunch_end_min
    is_dinner = dinner_start_min <= time_minutes <= dinner_end_min
    
    # Load dynamic boosts
    if bandit_weights is None:
        bandit_weights = load_bandit_weights()
    promo_boost_val, time_boost_val = get_bandit_boosts(bandit_weights, mode=bandit_mode)
    
    # 1. Find active promotions for this timestamp date & hour
    active_promos = []
    for promo in (active_promotions or []):
        try:
            start_date = datetime.strptime(promo.get('start_date', ''), "%Y-%m-%d").date()
            end_date = datetime.strptime(promo.get('end_date', ''), "%Y-%m-%d").date()
            if start_date <= timestamp_date <= end_date:
                promo_name = promo.get('name', '')
                promo_name_lower = promo_name.lower()
                # Apply lunch/dinner hour validation to promotions if named as such
                if "lunch" in promo_name_lower and not is_lunch:
                    continue
                if "dinner" in promo_name_lower and not is_dinner:
                    continue
                active_promos.append(promo)
        except (ValueError, KeyError, TypeError):
            continue
            
    # 2. Build menu category lookup table for O(1) searches
    menu_lookup = {}
    if menu_items is not None:
        if isinstance(menu_items, list):
            for i in menu_items:
                if isinstance(i, dict) and 'name' in i:
                    menu_lookup[i['name']] = i.get('category', '')
        else: # pandas DataFrame
            for idx, row in menu_items.iterrows():
                menu_lookup[row['name']] = row['category']
                
    # 3. Find matching rules and calculate scores
    cart_set = set(cart_items or [])
    candidates = {}
    
    for rule in (affinity_rules or []):
        try:
            antecedents = rule.get("antecedents", [])
            consequents = rule.get("consequents", [])
            
            # A rule matches if antecedents is subset of cart_items
            if set(antecedents).issubset(cart_set):
                base_confidence = rule.get("confidence", rule.get("support", 0.0))
                
                for item in consequents:
                    # Exclusion Constraint: Do not recommend items already in cart
                    if item in cart_set:
                        continue
                        
                    # Look up category from lookup table
                    item_category = menu_lookup.get(item, "")
                    
                    # Promo Boost
                    promo_boost = 0.0
                    for promo in active_promos:
                        if is_item_in_promotion(item, item_category, promo.get('name', '')):
                            promo_boost = promo_boost_val
                            break # Only apply one promo boost
                            
                    # Time Boost
                    time_boost = 0.0
                    # Standardize category strings check in case-insensitive way
                    item_category_lower = item_category.lower()
                    if is_lunch and item_category_lower in ["burgers", "combos"]:
                        time_boost = time_boost_val
                    elif is_dinner and item_category_lower in ["combos", "sides"]:
                        time_boost = time_boost_val
                        
                    # Calculate Score
                    score = base_confidence * (1.0 + promo_boost) * (1.0 + time_boost)
                    
                    # Keep highest score if item is suggested multiple times
                    if item not in candidates or score > candidates[item]:
                        candidates[item] = score
        except (AttributeError, TypeError):
            continue
            
    # Sort and format output
    sorted_recs = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
    return [{"name": name, "score": score} for name, score in sorted_recs]

def format_price_vnd(price: float) -> str:
    try:
        val = int(price)
        return f"{val:,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(price)

def generate_local_fallback(item_name: str, item_price: float) -> dict:
    return {
        "copy": f"Hoàn thành bữa ăn! Thêm {item_name} chỉ với {format_price_vnd(item_price)}đ",
        "rationale": "Thường được mua kèm với các sản phẩm trong giỏ hàng."
    }

def generate_ollama_recommendation_copy(item_name: str, item_price: float, cart_items: list, host: str = None, model: str = None, timeout: float = 5.0) -> dict:
    if not host:
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    if not model:
        model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
        
    # Ensure host is a string to prevent rstrip crashes
    host = str(host)
    url = f"{host.rstrip('/')}/api/chat"
    headers = {"Content-Type": "application/json"}
    
    try:
        cart_str = ', '.join(map(str, cart_items)) if cart_items else 'Trống'
        prompt = (
            "You are a sales-driven copywriter for a premium KFC kiosk in Vietnam.\n"
            "Generate a localized, highly engaging promotional copy (in Vietnamese) and a brief statistical rationale (in Vietnamese) "
            "for recommending a candidate item based on the customer's current cart items.\n\n"
            f"Candidate Item: {item_name}\n"
            f"Price: {format_price_vnd(item_price)}đ\n"
            f"Current Cart: {cart_str}\n\n"
            "Rules:\n"
            "1. Promotional copy must be appetizing, concise, and encourage adding the item (maximum 2 sentences).\n"
            "2. Rationale must provide a simple reason why the item was suggested. Keep it short and natural.\n"
            "3. Output MUST be in Vietnamese.\n"
            "4. Follow the JSON schema exactly: {\"copy\": \"...\", \"rationale\": \"...\"}"
        )
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "format": "json",
            "stream": False
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            content = data.get("message", {}).get("content", "")
            parsed = json.loads(content)
            if isinstance(parsed.get("copy"), str) and isinstance(parsed.get("rationale"), str):
                return {
                    "copy": parsed["copy"],
                    "rationale": parsed["rationale"]
                }
            else:
                logger.warning(f"Ollama response JSON missing string 'copy' or 'rationale'. Parsed: {parsed}")
        else:
            logger.warning(f"Ollama server returned error status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Ollama connection or timeout error: {e}")
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON response from Ollama: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error in Ollama copy generation: {e}")
        
    return generate_local_fallback(item_name, item_price)

def generate_openrouter_recommendation_copy(item_name: str, item_price: float, cart_items: list, api_key: str = None, timeout: float = 1.2) -> dict:
    if not api_key:
        api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return generate_local_fallback(item_name, item_price)
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/nakien0205/KFC",
        "X-Title": "KFC Kiosk Recommendation System"
    }
    
    model = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")
    
    try:
        cart_str = ', '.join(map(str, cart_items)) if cart_items else 'Trống'
        prompt = (
            "You are a sales-driven copywriter for a premium KFC kiosk in Vietnam.\n"
            "Generate a localized, highly engaging promotional copy (in Vietnamese) and a brief statistical rationale (in Vietnamese) "
            "for recommending a candidate item based on the customer's current cart items.\n\n"
            f"Candidate Item: {item_name}\n"
            f"Price: {format_price_vnd(item_price)}đ\n"
            f"Current Cart: {cart_str}\n\n"
            "Rules:\n"
            "1. Promotional copy must be appetizing, concise, and encourage adding the item (maximum 2 sentences).\n"
            "2. Rationale must provide a simple reason why the item was suggested. Keep it short and natural.\n"
            "3. Output MUST be in Vietnamese.\n"
            "4. Follow the JSON schema exactly: {\"copy\": \"...\", \"rationale\": \"...\"}"
        )
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "response_format": {
                "type": "json_object"
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            parsed = json.loads(content)
            if "copy" in parsed and "rationale" in parsed:
                return {
                    "copy": parsed["copy"],
                    "rationale": parsed["rationale"]
                }
            else:
                logger.warning(f"OpenRouter response JSON missing 'copy' or 'rationale'. Parsed: {parsed}")
        else:
            logger.warning(f"OpenRouter server returned error status code: {response.status_code}")
    except Exception as e:
        logger.warning(f"OpenRouter connection or error: {e}")
        
    return generate_local_fallback(item_name, item_price)

def generate_recommendation_copy(item_name: str, item_price: float, cart_items: list, api_key: str = None, timeout: float = 1.2) -> dict:
    use_ollama = os.environ.get("USE_OLLAMA", "false").lower() in ("true", "1", "yes")
    
    if use_ollama:
        ollama_timeout = 5.0 if timeout == 1.2 else timeout
        return generate_ollama_recommendation_copy(item_name, item_price, cart_items, timeout=ollama_timeout)
        
    # Check if we should use OpenRouter
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    is_openrouter = False
    
    if api_key:
        if api_key.startswith("sk-or-") or "openrouter" in api_key.lower():
            is_openrouter = True
            effective_key = api_key
        else:
            effective_key = api_key
    elif openrouter_api_key:
        is_openrouter = True
        effective_key = openrouter_api_key
    else:
        effective_key = os.environ.get("GEMINI_API_KEY")
        
    if not effective_key:
        # If no API key is provided, fall back to Ollama copy generator (which internally falls back to local template on failure)
        ollama_timeout = 5.0 if timeout == 1.2 else timeout
        return generate_ollama_recommendation_copy(item_name, item_price, cart_items, timeout=ollama_timeout)
        
    if is_openrouter:
        return generate_openrouter_recommendation_copy(
            item_name=item_name,
            item_price=item_price,
            cart_items=cart_items,
            api_key=effective_key,
            timeout=timeout
        )
        
    # Gemini API Call
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={effective_key}"
    headers = {"Content-Type": "application/json"}
    
    try:
        cart_str = ', '.join(map(str, cart_items)) if cart_items else 'Trống'
        prompt = (
            "You are a sales-driven copywriter for a premium KFC kiosk in Vietnam.\n"
            "Generate a localized, highly engaging promotional copy (in Vietnamese) and a brief statistical rationale (in Vietnamese) "
            "for recommending a candidate item based on the customer's current cart items.\n\n"
            f"Candidate Item: {item_name}\n"
            f"Price: {format_price_vnd(item_price)}đ\n"
            f"Current Cart: {cart_str}\n\n"
            "Rules:\n"
            "1. Promotional copy must be appetizing, concise, and encourage adding the item (maximum 2 sentences).\n"
            "2. Rationale must provide a simple reason why the item was suggested. Keep it short and natural.\n"
            "3. Output MUST be in Vietnamese.\n"
            "4. Follow the JSON schema exactly."
        )
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "object",
                    "properties": {
                        "copy": {"type": "string"},
                        "rationale": {"type": "string"}
                    },
                    "required": ["copy", "rationale"]
                }
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            text_content = data['candidates'][0]['content']['parts'][0]['text']
            parsed = json.loads(text_content)
            if "copy" in parsed and "rationale" in parsed:
                return {
                    "copy": parsed["copy"],
                    "rationale": parsed["rationale"]
                }
    except Exception:
        pass
        
    return generate_local_fallback(item_name, item_price)
