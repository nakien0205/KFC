from datetime import datetime, time
import os
import json
import requests
import logging
import unicodedata
from bandit import load_bandit_weights, get_bandit_boosts
from promo_engine import (
    URGENCY_BOOST_CAP,
    build_discount_view,
    calculate_promotion_urgency,
    promotion_targets_item,
)

logger = logging.getLogger("recommender")

VIETNAMESE_DISCOUNT_PREFIX = "gi\u1ea3m "
VIETNAMESE_DONG_SYMBOL = "\u0111"
VIETNAMESE_DONG_SYMBOL_UPPER = "\u0110"

DRINK_KEYWORDS = ("pepsi", "7up", "lipton")
DESSERT_KEYWORDS = ("eggtart", "tart", "dessert")
SIDE_KEYWORDS = (
    "fries",
    "popcorn",
    "coleslaw",
    "mashed",
    "potato",
    "soup",
    "salad",
    "cheese",
)
def is_item_in_promotion(item_name: str, item_category: str, promo_name: str) -> bool:
    if isinstance(promo_name, dict):
        if promotion_targets_item(promo_name, item_name, item_category):
            return True
        promo_name = promo_name.get("name", "")

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

def _safe_lower(value) -> str:
    return str(value or "").strip().lower()

def _clean_optional(value):
    if value is None:
        return None
    try:
        if value != value:
            return None
    except Exception:
        pass
    if str(value).strip() == "" or str(value).strip().lower() == "nan":
        return None
    return value

def _safe_float(value, default=0.0):
    value = _clean_optional(value)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def _contains_vietnamese_text(*values) -> bool:
    text = " ".join(str(value or "") for value in values)
    if VIETNAMESE_DONG_SYMBOL in text or VIETNAMESE_DONG_SYMBOL_UPPER in text:
        return True
    normalized = unicodedata.normalize("NFD", text)
    return any("\u0300" <= char <= "\u036f" for char in normalized)

def _copy_response_is_english(parsed: dict) -> bool:
    copy_text = parsed.get("copy")
    rationale_text = parsed.get("rationale")
    return (
        isinstance(copy_text, str)
        and isinstance(rationale_text, str)
        and not _contains_vietnamese_text(copy_text, rationale_text)
        and VIETNAMESE_DONG_SYMBOL not in copy_text
        and VIETNAMESE_DONG_SYMBOL not in rationale_text
    )

def _format_price_vnd_label(price: float) -> str:
    return f"{format_price_vnd(price)} VND"

def _normalize_discount_label(label) -> str:
    text = str(label or "").strip()
    if not text:
        return ""

    lower_text = text.lower()
    if lower_text.startswith(VIETNAMESE_DISCOUNT_PREFIX):
        value = text[len(VIETNAMESE_DISCOUNT_PREFIX):].strip()
        if value.endswith("%"):
            return f"{value} off"
        value = value.replace(VIETNAMESE_DONG_SYMBOL, "").replace(VIETNAMESE_DONG_SYMBOL_UPPER, "").strip()
        return f"Save {value} VND"

    if text.endswith(VIETNAMESE_DONG_SYMBOL) or text.endswith(VIETNAMESE_DONG_SYMBOL_UPPER):
        return text[:-1].strip() + " VND"

    return text

def _build_menu_records(menu_items):
    records = []
    if menu_items is None:
        return records

    if isinstance(menu_items, list):
        source_rows = menu_items
    else:
        try:
            source_rows = menu_items.to_dict(orient="records")
        except AttributeError:
            return records

    seen = set()
    for row in source_rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        records.append({
            "name": name,
            "category": str(row.get("category", "") or ""),
            "price": row.get("price", 0.0),
        })
    return records

def _item_role(item_name: str, item_category: str) -> str:
    name = _safe_lower(item_name)
    category = _safe_lower(item_category)

    if category == "drinks" or any(word in name for word in DRINK_KEYWORDS):
        return "drink"
    if category == "desserts" or any(word in name for word in DESSERT_KEYWORDS):
        return "dessert"
    if category in ("burgers", "combos") or any(word in name for word in ("burger", "combo", "bucket")):
        return "main"
    if any(word in name for word in ("rice", "pasta")) and "fries" not in name:
        return "main"
    if any(word in name for word in ("chicken", "tender", "fish", "fillet")):
        return "main"
    if category == "sides" or any(word in name for word in SIDE_KEYWORDS):
        return "side"
    return "side"

def _cart_profile(cart_items, menu_lookup):
    profile = {
        "has_main": False,
        "has_drink": False,
        "has_side": False,
        "has_dessert": False,
        "has_combo": False,
        "has_single_main": False,
    }

    for item in cart_items or []:
        category = menu_lookup.get(item, "")
        role = _item_role(item, category)
        item_lower = _safe_lower(item)
        profile[f"has_{role}"] = True
        if role == "main" and not any(word in item_lower for word in ("combo", "bucket")):
            profile["has_single_main"] = True
        if any(word in item_lower for word in ("combo", "bucket")):
            profile["has_combo"] = True
    return profile

def _fallback_base_score(item_name, item_category, cart_profile):
    role = _item_role(item_name, item_category)
    item_lower = _safe_lower(item_name)

    if role == "drink":
        if not cart_profile["has_drink"]:
            return 0.34 if cart_profile["has_main"] else 0.26
        return 0.0

    if role == "side":
        if not cart_profile["has_side"] and cart_profile["has_main"]:
            if any(word in item_lower for word in ("fries", "coleslaw", "mashed", "popcorn")):
                return 0.31
            return 0.24
        if cart_profile["has_drink"] and not cart_profile["has_main"]:
            return 0.22
        return 0.0

    if role == "dessert":
        if not cart_profile["has_dessert"]:
            return 0.25 if cart_profile["has_main"] else 0.18
        return 0.0

    if role == "main":
        if not cart_profile["has_main"]:
            if cart_profile["has_dessert"] and not cart_profile["has_drink"]:
                return 0.20
            if any(word in item_lower for word in ("combo", "bucket")):
                return 0.32
            return 0.28
        if cart_profile["has_single_main"] and any(word in item_lower for word in ("combo", "bucket")):
            return 0.23
        return 0.0

    return 0.0

def _promotion_context_for_item(item_name, item_category, item_price, active_promos, timestamp_dt):
    best_context = None
    best_rank = (-1.0, -1.0)

    for promo in active_promos:
        if not isinstance(promo, dict):
            continue
        if not is_item_in_promotion(item_name, item_category, promo):
            continue

        urgency = calculate_promotion_urgency(promo, timestamp_dt)
        discount_pct = _safe_float(promo.get("discount_pct"), 0.0)
        context = {
            "promo_id": promo.get("promo_id"),
            "promotion_name": promo.get("name", ""),
            "urgency": urgency,
            "discount_pct": discount_pct,
        }

        display_text = _clean_optional(promo.get("display_text"))
        sale_price = _clean_optional(promo.get("sale_price"))
        amount_off = _clean_optional(promo.get("amount_off_vnd"))
        is_dynamic = str(promo.get("is_dynamic", "")).strip().lower() in ("1", "true", "yes")
        has_precise_target = bool(_clean_optional(promo.get("target_item")) or _clean_optional(promo.get("target_category")))

        if display_text:
            context["discount_label"] = _normalize_discount_label(display_text)
        if sale_price is not None:
            context["sale_price"] = max(0.0, _safe_float(sale_price, item_price))
        if amount_off is not None:
            context["amount_off_vnd"] = max(0.0, _safe_float(amount_off, 0.0))

        if (is_dynamic or has_precise_target) and "sale_price" not in context:
            discount_view = build_discount_view(item_price, discount_pct)
            context.update({
                "discount_pct": discount_view["discount_pct"],
                "amount_off_vnd": discount_view["amount_off_vnd"],
                "sale_price": discount_view["sale_price"],
                "discount_label": discount_view["display_text"],
            })

        rank = (urgency, discount_pct)
        if best_context is None or rank > best_rank:
            best_context = context
            best_rank = rank

    return best_context

def _candidate_record(item_name, score, promo_context):
    record = {"name": item_name, "score": score}
    if promo_context:
        for key in (
            "promo_id",
            "promotion_name",
            "discount_pct",
            "discount_label",
            "amount_off_vnd",
            "sale_price",
            "urgency",
        ):
            value = promo_context.get(key)
            if value is not None:
                record[key] = value
    return record

def _apply_context_boosts(base_score, item_name, item_category, item_price, active_promos, is_lunch, is_dinner, promo_boost_val, time_boost_val, timestamp_dt):
    promo_boost = 0.0
    promo_context = _promotion_context_for_item(item_name, item_category, item_price, active_promos, timestamp_dt)
    if promo_context:
        promo_boost = promo_boost_val

    time_boost = 0.0
    item_category_lower = _safe_lower(item_category)
    role = _item_role(item_name, item_category)
    if is_lunch and (item_category_lower in ["burgers", "combos"] or role == "main"):
        time_boost = time_boost_val
    elif is_dinner and (item_category_lower in ["combos", "sides"] or role in ("main", "side")):
        time_boost = time_boost_val

    urgency = promo_context.get("urgency", 0.0) if promo_context else 0.0
    score = base_score * (1.0 + promo_boost) * (1.0 + time_boost) * (1.0 + (URGENCY_BOOST_CAP * urgency))
    return score, promo_context

def _fallback_recommendations(cart_items, menu_records, menu_lookup, active_promos, is_lunch, is_dinner, promo_boost_val, time_boost_val, timestamp_dt=None, limit=5):
    cart_set = set(cart_items or [])
    profile = _cart_profile(cart_items, menu_lookup)
    candidates = []

    for row in menu_records:
        name = row["name"]
        if name in cart_set:
            continue
        category = row.get("category", "")
        base_score = _fallback_base_score(name, category, profile)
        if base_score <= 0:
            continue
        item_price = _safe_float(row.get("price"), 0.0)
        score, promo_context = _apply_context_boosts(
            base_score,
            name,
            category,
            item_price,
            active_promos,
            is_lunch,
            is_dinner,
            promo_boost_val,
            time_boost_val,
            timestamp_dt,
        )
        candidates.append(_candidate_record(name, score, promo_context))

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]

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
    menu_records = _build_menu_records(menu_items)
    menu_lookup = {row["name"]: row.get("category", "") for row in menu_records}
    menu_price_lookup = {row["name"]: _safe_float(row.get("price"), 0.0) for row in menu_records}
                
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
                    
                    item_price = menu_price_lookup.get(item, 0.0)
                    score, promo_context = _apply_context_boosts(
                        base_confidence,
                        item,
                        item_category,
                        item_price,
                        active_promos,
                        is_lunch,
                        is_dinner,
                        promo_boost_val,
                        time_boost_val,
                        timestamp_dt,
                    )
                    
                    # Keep highest score if item is suggested multiple times
                    if item not in candidates or score > candidates[item]["score"]:
                        candidates[item] = _candidate_record(item, score, promo_context)
        except (AttributeError, TypeError):
            continue
            
    # Sort and format output
    sorted_recs = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)
    if sorted_recs:
        return sorted_recs

    return _fallback_recommendations(
        cart_items=cart_items,
        menu_records=menu_records,
        menu_lookup=menu_lookup,
        active_promos=active_promos,
        is_lunch=is_lunch,
        is_dinner=is_dinner,
        promo_boost_val=promo_boost_val,
        time_boost_val=time_boost_val,
        timestamp_dt=timestamp_dt,
    )

def format_price_vnd(price: float) -> str:
    try:
        val = int(price)
        return f"{val:,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(price)

def generate_local_fallback(item_name: str, item_price: float, promotion_context: dict = None) -> dict:
    if isinstance(promotion_context, dict) and promotion_context.get("discount_label"):
        urgency = _safe_float(promotion_context.get("urgency"), 0.0)
        prefix = "Sale ending soon" if urgency >= 0.5 else "Active deal"
        discount_label = _normalize_discount_label(promotion_context["discount_label"])
        return {
            "copy": f"{prefix}: {discount_label} on {item_name}, now only {_format_price_vnd_label(item_price)}.",
            "rationale": "Prioritized because this item has an active promotion that fits the cart."
        }
    return {
        "copy": f"Complete your meal: add {item_name} for only {_format_price_vnd_label(item_price)}.",
        "rationale": "Often purchased with items in your cart."
    }

def _promotion_prompt_context(promotion_context):
    if not isinstance(promotion_context, dict) or not promotion_context.get("discount_label"):
        return ""
    urgency_note = "Sale is ending soon." if _safe_float(promotion_context.get("urgency"), 0.0) >= 0.5 else "Sale is active."
    return (
        f"Promotion: {_normalize_discount_label(promotion_context.get('discount_label'))}.\n"
        f"Promotion urgency: {urgency_note}\n"
    )

def generate_ollama_recommendation_copy(item_name: str, item_price: float, cart_items: list, host: str = None, model: str = None, timeout: float = 5.0, promotion_context: dict = None) -> dict:
    if not host:
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    if not model:
        model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
        
    # Ensure host is a string to prevent rstrip crashes
    host = str(host)
    url = f"{host.rstrip('/')}/api/chat"
    headers = {"Content-Type": "application/json"}
    
    try:
        cart_str = ', '.join(map(str, cart_items)) if cart_items else 'Empty'
        prompt = (
            "You are a sales-driven copywriter for a premium KFC kiosk in Vietnam.\n"
            "Generate localized, highly engaging promotional copy in English and a brief statistical rationale in English "
            "for recommending a candidate item based on the customer's current cart items.\n\n"
            f"Candidate Item: {item_name}\n"
            f"Price: {_format_price_vnd_label(item_price)}\n"
            f"Current Cart: {cart_str}\n\n"
            f"{_promotion_prompt_context(promotion_context)}"
            "Rules:\n"
            "1. Promotional copy must be appetizing, concise, and encourage adding the item (maximum 2 sentences).\n"
            "2. Rationale must provide a simple reason why the item was suggested. Keep it short and natural.\n"
            "3. Output MUST be in English. Do not use Vietnamese words, Vietnamese diacritics, or the Vietnamese dong currency symbol.\n"
            "4. Use \"VND\" for prices.\n"
            "5. Follow the JSON schema exactly: {\"copy\": \"...\", \"rationale\": \"...\"}"
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
            if _copy_response_is_english(parsed):
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
        
    return generate_local_fallback(item_name, item_price, promotion_context=promotion_context)

def generate_openrouter_recommendation_copy(item_name: str, item_price: float, cart_items: list, api_key: str = None, timeout: float = 1.2, promotion_context: dict = None) -> dict:
    if not api_key:
        api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return generate_local_fallback(item_name, item_price, promotion_context=promotion_context)
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/nakien0205/KFC",
        "X-Title": "KFC Kiosk Recommendation System"
    }
    
    model = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")
    
    try:
        cart_str = ', '.join(map(str, cart_items)) if cart_items else 'Empty'
        prompt = (
            "You are a sales-driven copywriter for a premium KFC kiosk in Vietnam.\n"
            "Generate localized, highly engaging promotional copy in English and a brief statistical rationale in English "
            "for recommending a candidate item based on the customer's current cart items.\n\n"
            f"Candidate Item: {item_name}\n"
            f"Price: {_format_price_vnd_label(item_price)}\n"
            f"Current Cart: {cart_str}\n\n"
            f"{_promotion_prompt_context(promotion_context)}"
            "Rules:\n"
            "1. Promotional copy must be appetizing, concise, and encourage adding the item (maximum 2 sentences).\n"
            "2. Rationale must provide a simple reason why the item was suggested. Keep it short and natural.\n"
            "3. Output MUST be in English. Do not use Vietnamese words, Vietnamese diacritics, or the Vietnamese dong currency symbol.\n"
            "4. Use \"VND\" for prices.\n"
            "5. Follow the JSON schema exactly: {\"copy\": \"...\", \"rationale\": \"...\"}"
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
            if _copy_response_is_english(parsed):
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
        
    return generate_local_fallback(item_name, item_price, promotion_context=promotion_context)

def generate_recommendation_copy(item_name: str, item_price: float, cart_items: list, api_key: str = None, timeout: float = 1.2, promotion_context: dict = None) -> dict:
    use_ollama = os.environ.get("USE_OLLAMA", "false").lower() in ("true", "1", "yes")
    
    if use_ollama:
        ollama_timeout = 5.0 if timeout == 1.2 else timeout
        return generate_ollama_recommendation_copy(item_name, item_price, cart_items, timeout=ollama_timeout, promotion_context=promotion_context)
        
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
        return generate_ollama_recommendation_copy(item_name, item_price, cart_items, timeout=ollama_timeout, promotion_context=promotion_context)
        
    if is_openrouter:
        return generate_openrouter_recommendation_copy(
            item_name=item_name,
            item_price=item_price,
            cart_items=cart_items,
            api_key=effective_key,
            timeout=timeout,
            promotion_context=promotion_context
        )
        
    # Gemini API Call
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={effective_key}"
    headers = {"Content-Type": "application/json"}
    
    try:
        cart_str = ', '.join(map(str, cart_items)) if cart_items else 'Empty'
        prompt = (
            "You are a sales-driven copywriter for a premium KFC kiosk in Vietnam.\n"
            "Generate localized, highly engaging promotional copy in English and a brief statistical rationale in English "
            "for recommending a candidate item based on the customer's current cart items.\n\n"
            f"Candidate Item: {item_name}\n"
            f"Price: {_format_price_vnd_label(item_price)}\n"
            f"Current Cart: {cart_str}\n\n"
            f"{_promotion_prompt_context(promotion_context)}"
            "Rules:\n"
            "1. Promotional copy must be appetizing, concise, and encourage adding the item (maximum 2 sentences).\n"
            "2. Rationale must provide a simple reason why the item was suggested. Keep it short and natural.\n"
            "3. Output MUST be in English. Do not use Vietnamese words, Vietnamese diacritics, or the Vietnamese dong currency symbol.\n"
            "4. Use \"VND\" for prices.\n"
            "5. Follow the JSON schema exactly."
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
            if _copy_response_is_english(parsed):
                return {
                    "copy": parsed["copy"],
                    "rationale": parsed["rationale"]
                }
    except Exception:
        pass
        
    return generate_local_fallback(item_name, item_price, promotion_context=promotion_context)
