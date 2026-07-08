import os
import json
import pandas as pd
import random
from datetime import datetime
from recommender import rerank_recommendations, is_item_in_promotion, format_price_vnd

def run_backtest_simulation(seed=42):
    # Seeded runs are useful for tests; seed=None gives the web demo a fresh
    # Monte Carlo replay instead of the same fixed result on every click.
    if seed is not None:
        random.seed(seed)
    rng = random.Random(seed)
    
    # 1. Resolve paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "_bmad-output", "data")
    menu_path = os.path.join(data_dir, "menu.csv")
    promo_path = os.path.join(data_dir, "promotions.csv")
    rules_path = os.path.join(data_dir, "affinity_rules.json")
    orders_path = os.path.join(data_dir, "orders.csv")
    
    # 2. Check if all required files exist
    for p in [menu_path, promo_path, rules_path, orders_path]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Required file not found: {p}")
            
    # 3. Load files
    menu_df = pd.read_csv(menu_path)
    promotions_df = pd.read_csv(promo_path)
    promotions_list = promotions_df.to_dict(orient="records")
    
    with open(rules_path, "r", encoding="utf-8") as f:
        affinity_rules = json.load(f)
        
    orders_df = pd.read_csv(orders_path)
    
    # 4. Build lookups
    menu_price_lookup = {}
    menu_category_lookup = {}
    for _, row in menu_df.iterrows():
        menu_price_lookup[row['name']] = float(row['price'])
        menu_category_lookup[row['name']] = row['category']
        
    # Calculate baseline support from orders.csv
    total_orders = orders_df['order_id'].nunique()
    item_counts = orders_df['item_name'].value_counts()
    baseline_support = {}
    for item_name, count in item_counts.items():
        baseline_support[item_name] = count / max(1, total_orders)
        
    # Default item for baseline model
    default_baseline_item = "Pepsi"
    default_baseline_price = menu_price_lookup.get(default_baseline_item, 0.0)
    default_baseline_support = baseline_support.get(default_baseline_item, 0.0)
    
    # Sort items by baseline support descending for fallback recommendations
    sorted_by_popularity = [
        item for item, _ in sorted(baseline_support.items(), key=lambda x: x[1], reverse=True)
    ]
    
    # Group orders by order_id
    grouped_orders = orders_df.groupby('order_id')['item_name'].apply(list).to_dict()
    
    baseline_totals = []
    hybrid_totals = []
    
    # Initialize bandit weights with priors
    bandit_weights = {
        "alpha_promo": 2.0,
        "beta_promo": 8.0,
        "alpha_time": 1.5,
        "beta_time": 8.5
    }
    
    # Create temporary file for bandit weights during simulation run
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        temp_weights_path = tmp.name
        
    from bandit import save_bandit_weights, update_bandit_weights
    save_bandit_weights(bandit_weights, path=temp_weights_path)
    
    # Deterministic hour cycling to simulate contextual variety
    hours = [10, 12, 13, 15, 16, 18, 19, 20]
    
    # Loop over transactions
    for idx, (order_id, original_items) in enumerate(grouped_orders.items()):
        original_value = sum(menu_price_lookup.get(item, 0.0) for item in original_items)
        
        # 5. Determine context for this transaction
        hour = hours[idx % len(hours)]
        minute = (idx * 7) % 60
        # date: 2026-07-06 (within active range of promotions.csv)
        timestamp_str = f"2026-07-06T{hour:02d}:{minute:02d}:00Z"
        
        # Determine time category boosts
        time_minutes = hour * 60 + minute
        is_lunch = 11 * 60 <= time_minutes <= 14 * 60
        is_dinner = 17 * 60 <= time_minutes <= 21 * 60
        
        # Determine active promos for this date and time
        active_promos = []
        try:
            timestamp_date = datetime.strptime("2026-07-06", "%Y-%m-%d").date()
            for promo in promotions_list:
                start_date_str = promo.get('start_date', '')
                end_date_str = promo.get('end_date', '')
                if start_date_str and end_date_str:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                    if start_date <= timestamp_date <= end_date:
                        promo_name_lower = promo.get('name', '').lower()
                        if "lunch" in promo_name_lower and not is_lunch:
                            continue
                        if "dinner" in promo_name_lower and not is_dinner:
                            continue
                        active_promos.append(promo)
        except (ValueError, TypeError, KeyError):
            pass
                
        # ─── Baseline Model Simulation ───
        baseline_val = original_value
        if default_baseline_item not in original_items:
            # Customer accepts default item based on its baseline support
            if rng.random() < default_baseline_support:
                baseline_val += default_baseline_price
        baseline_totals.append(baseline_val)
        
        # ─── Hybrid Model Simulation ───
        hybrid_val = original_value
        
        # Get context-aware recommendations using bandit weights and Thompson Sampling
        recs = rerank_recommendations(
            cart_items=original_items,
            active_promotions=promotions_list,
            affinity_rules=affinity_rules,
            menu_items=menu_df,
            timestamp=timestamp_str,
            bandit_weights=bandit_weights,
            bandit_mode="sample"
        )
        
        rec_item = None
        p_accept = 0.0
        
        if recs:
            # Top candidate from reranker is already sorted by score desc and excludes cart items
            rec_item = recs[0]["name"]
            p_accept = recs[0]["score"]
        else:
            # Fallback to the most popular item not in cart
            for item in sorted_by_popularity:
                if item not in original_items:
                    rec_item = item
                    break
            
            if rec_item:
                p_accept = baseline_support.get(rec_item, 0.0)
                
        accepted = False
        if rec_item:
            # Cap probability at 1.0
            p_accept = min(1.0, max(0.0, p_accept))
            if rng.random() < p_accept:
                hybrid_val += menu_price_lookup.get(rec_item, 0.0)
                accepted = True
                
        # Update bandit parameters based on simulated customer response
        if rec_item:
            item_category = menu_category_lookup.get(rec_item, "")
            item_category_lower = item_category.lower()
            
            promo_active = False
            for promo in active_promos:
                if is_item_in_promotion(rec_item, item_category, promo.get('name', '')):
                    promo_active = True
                    break
                    
            time_active = False
            if is_lunch and item_category_lower in ["burgers", "combos"]:
                time_active = True
            elif is_dinner and item_category_lower in ["combos", "sides"]:
                time_active = True
                
            # Update bandit parameters using the official helper on the temp path
            bandit_weights = update_bandit_weights(
                accepted=accepted,
                promo_active=promo_active,
                time_active=time_active,
                path=temp_weights_path
            )
                
        hybrid_totals.append(hybrid_val)
        
    # Calculate metrics
    if not baseline_totals:
        return {
            "baseline_aov": 0.0,
            "hybrid_aov": 0.0,
            "absolute_change": 0.0,
            "percentage_uplift": 0.0,
            "total_simulated": 0
        }
        
    # Clean up the temporary weights file
    try:
        os.unlink(temp_weights_path)
    except Exception:
        pass
    
    baseline_aov = sum(baseline_totals) / len(baseline_totals)
    hybrid_aov = sum(hybrid_totals) / len(hybrid_totals)
    absolute_change = hybrid_aov - baseline_aov
    percentage_uplift = (absolute_change / baseline_aov) * 100 if baseline_aov > 0 else 0.0
    
    return {
        "baseline_aov": round(baseline_aov, 2),
        "hybrid_aov": round(hybrid_aov, 2),
        "absolute_change": round(absolute_change, 2),
        "percentage_uplift": round(percentage_uplift, 2),
        "total_simulated": len(grouped_orders),
        "final_weights": bandit_weights
    }

if __name__ == "__main__":
    print("Starting AOV Uplift Backtest Simulation...")
    try:
        results = run_backtest_simulation(seed=42)
        print("\n================ BACKTEST SIMULATION RESULTS ================")
        print(f"Total Transactions Simulated: {results.get('total_simulated', 0)}")
        print(f"Baseline AOV:                 {format_price_vnd(results['baseline_aov'])} VND")
        print(f"Hybrid Recommender AOV:       {format_price_vnd(results['hybrid_aov'])} VND")
        print(f"Absolute AOV Uplift:          +{format_price_vnd(results['absolute_change'])} VND")
        print(f"Percentage AOV Uplift:        +{results['percentage_uplift']:.2f}%")
        print(f"Final Learned Promo Weights:  alpha={results['final_weights']['alpha_promo']:.1f}, beta={results['final_weights']['beta_promo']:.1f}")
        print(f"Final Learned Time Weights:   alpha={results['final_weights']['alpha_time']:.1f}, beta={results['final_weights']['beta_time']:.1f}")
        print("=============================================================")
    except Exception as e:
        print(f"Error running simulation: {e}")
        import traceback
        traceback.print_exc()
