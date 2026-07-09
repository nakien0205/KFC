import os
import json
import pandas as pd
import random
import tempfile
from datetime import datetime
from recommender import rerank_recommendations, is_item_in_promotion, format_price_vnd

DEFAULT_PANEL_SIZE = 3
DEFAULT_BENCHMARK_MODE = "partial_cart_panel"
CONSERVATIVE_MODE = "conservative_full_order"
DEFAULT_BANDIT_WEIGHTS = {
    "alpha_promo": 2.0,
    "beta_promo": 8.0,
    "alpha_time": 1.5,
    "beta_time": 8.5
}
CONTEXT_HOURS = [10, 12, 13, 15, 16, 18, 19, 20]
DEFAULT_PROMO_DATE = "2026-07-06"


def _build_data_paths():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "_bmad-output", "data")
    return {
        "menu": os.path.join(data_dir, "menu.csv"),
        "promotions": os.path.join(data_dir, "promotions.csv"),
        "rules": os.path.join(data_dir, "affinity_rules.json"),
        "orders": os.path.join(data_dir, "orders.csv"),
    }


def _load_backtest_inputs():
    paths = _build_data_paths()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "_bmad-output", "data", "kiosk.db")

    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"SQLite database is missing at {db_path}. "
            "Please rebuild it using the command: python init_db.py"
        )

    import sqlite3
    try:
        conn = sqlite3.connect(db_path)

        # 1. Load menu
        menu_df = pd.read_sql_query("SELECT name, category, price, image FROM menu", conn)
        required_menu_cols = {'name', 'category', 'price'}
        if not required_menu_cols.issubset(menu_df.columns):
            raise ValueError(f"SQLite menu table is missing required columns: {required_menu_cols - set(menu_df.columns)}")

        # 2. Load promotions
        promotions_df = pd.read_sql_query("SELECT * FROM promotions", conn)

        # 3. Load affinity rules
        cursor = conn.cursor()
        cursor.execute("SELECT antecedents, consequents, support, confidence, lift FROM affinity_rules")
        rules_rows = cursor.fetchall()
        affinity_rules = []
        for r_row in rules_rows:
            affinity_rules.append({
                "antecedents": json.loads(r_row[0]),
                "consequents": json.loads(r_row[1]),
                "support": float(r_row[2]),
                "confidence": float(r_row[3]),
                "lift": float(r_row[4])
            })

        # 4. Load orders
        orders_df = pd.read_sql_query("SELECT order_id, item_name, scenario FROM orders", conn)
        required_orders_cols = {'order_id', 'item_name'}
        if not required_orders_cols.issubset(orders_df.columns):
            raise ValueError(f"SQLite orders table is missing required columns: {required_orders_cols - set(orders_df.columns)}")

        conn.close()
    except Exception as e:
        raise ValueError(
            f"SQLite database is stale or invalid: {e}. "
            "Please rebuild it using the command: python init_db.py"
        ) from e

    menu_records = menu_df.to_dict(orient="records")
    menu_price_lookup = {}
    menu_category_lookup = {}
    for row in menu_records:
        name = row.get("name")
        if not name:
            continue
        menu_price_lookup[name] = float(row.get("price", 0.0))
        menu_category_lookup[name] = str(row.get("category", "") or "")

    total_orders = orders_df["order_id"].nunique()
    item_counts = orders_df["item_name"].value_counts()
    baseline_support = {
        item_name: count / max(1, total_orders)
        for item_name, count in item_counts.items()
    }
    grouped_orders = orders_df.groupby("order_id")["item_name"].apply(list).to_dict()
    sorted_by_popularity = [
        item for item, _ in sorted(baseline_support.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "menu_records": menu_records,
        "promotions_list": promotions_df.to_dict(orient="records"),
        "affinity_rules": affinity_rules,
        "grouped_orders": grouped_orders,
        "menu_price_lookup": menu_price_lookup,
        "menu_category_lookup": menu_category_lookup,
        "baseline_support": baseline_support,
        "sorted_by_popularity": sorted_by_popularity,
    }


def _timestamp_for_index(idx):
    hour = CONTEXT_HOURS[idx % len(CONTEXT_HOURS)]
    minute = (idx * 7) % 60
    timestamp_str = f"{DEFAULT_PROMO_DATE}T{hour:02d}:{minute:02d}:00Z"
    time_minutes = hour * 60 + minute
    is_lunch = 11 * 60 <= time_minutes <= 14 * 60
    is_dinner = 17 * 60 <= time_minutes <= 21 * 60
    return timestamp_str, is_lunch, is_dinner


def _active_promos_for_context(promotions_list, is_lunch, is_dinner):
    active_promos = []
    try:
        timestamp_date = datetime.strptime(DEFAULT_PROMO_DATE, "%Y-%m-%d").date()
        for promo in promotions_list:
            start_date_str = promo.get("start_date", "")
            end_date_str = promo.get("end_date", "")
            if not start_date_str or not end_date_str:
                continue
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if start_date <= timestamp_date <= end_date:
                promo_name_lower = promo.get("name", "").lower()
                if "lunch" in promo_name_lower and not is_lunch:
                    continue
                if "dinner" in promo_name_lower and not is_dinner:
                    continue
                active_promos.append(promo)
    except (ValueError, TypeError, KeyError):
        pass
    return active_promos


def _unique_preserve_order(items):
    unique_items = []
    seen = set()
    for item in items:
        if item not in seen:
            unique_items.append(item)
            seen.add(item)
    return unique_items


def _item_role(item_name, item_category):
    name = str(item_name or "").lower()
    category = str(item_category or "").lower()
    if category == "drinks" or any(word in name for word in ("pepsi", "7up", "lipton")):
        return "drink"
    if category == "desserts" or any(word in name for word in ("eggtart", "tart", "dessert")):
        return "dessert"
    if any(word in name for word in ("fries", "popcorn", "coleslaw", "mashed", "soup", "salad", "cheese")):
        return "side"
    return "main"


def _select_anchor_cart(original_items, menu_category_lookup):
    for item in original_items:
        if _item_role(item, menu_category_lookup.get(item, "")) == "main":
            return [item]
    return [original_items[0]] if original_items else []


def _empty_result(mode, panel_size):
    return {
        "baseline_aov": 0.0,
        "hybrid_aov": 0.0,
        "absolute_change": 0.0,
        "percentage_uplift": 0.0,
        "total_simulated": 0,
        "benchmark_mode": mode,
        "panel_size": panel_size,
        "final_weights": dict(DEFAULT_BANDIT_WEIGHTS)
    }


def _recommended_price(recommendation, menu_price_lookup):
    if not isinstance(recommendation, dict):
        return 0.0
    name = recommendation.get("name")
    if not name:
        return 0.0
    try:
        sale_price = float(recommendation.get("sale_price"))
        if sale_price >= 0:
            return sale_price
    except (TypeError, ValueError):
        pass
    return float(menu_price_lookup.get(name, 0.0))


def _calculate_metrics(baseline_totals, hybrid_totals, mode, panel_size, extra=None):
    if not baseline_totals:
        return _empty_result(mode, panel_size)

    baseline_aov = sum(baseline_totals) / len(baseline_totals)
    hybrid_aov = sum(hybrid_totals) / len(hybrid_totals)
    absolute_change = hybrid_aov - baseline_aov
    percentage_uplift = (absolute_change / baseline_aov) * 100 if baseline_aov > 0 else 0.0

    result = {
        "baseline_aov": round(baseline_aov, 2),
        "hybrid_aov": round(hybrid_aov, 2),
        "absolute_change": round(absolute_change, 2),
        "percentage_uplift": round(percentage_uplift, 2),
        "total_simulated": len(baseline_totals),
        "benchmark_mode": mode,
        "panel_size": panel_size,
    }
    if extra:
        result.update(extra)
    return result


def _run_partial_cart_panel(inputs, seed=42, panel_size=DEFAULT_PANEL_SIZE):
    baseline_totals = []
    hybrid_totals = []
    baseline_accepts = 0
    hybrid_accepts = 0
    skipped_orders = 0

    menu_price_lookup = inputs["menu_price_lookup"]
    menu_category_lookup = inputs["menu_category_lookup"]
    default_baseline_item = "Pepsi"
    default_baseline_price = menu_price_lookup.get(default_baseline_item, 0.0)
    bandit_weights = dict(DEFAULT_BANDIT_WEIGHTS)

    for idx, (_order_id, original_items) in enumerate(inputs["grouped_orders"].items()):
        unique_items = _unique_preserve_order(original_items)
        if len(unique_items) < 2:
            skipped_orders += 1
            continue

        anchor_cart = _select_anchor_cart(unique_items, menu_category_lookup)
        if not anchor_cart:
            skipped_orders += 1
            continue

        held_out_items = [item for item in unique_items if item not in set(anchor_cart)]
        held_out_set = set(held_out_items)
        anchor_value = sum(menu_price_lookup.get(item, 0.0) for item in anchor_cart)

        baseline_val = anchor_value
        if default_baseline_item not in anchor_cart and default_baseline_item in held_out_set:
            baseline_val += default_baseline_price
            baseline_accepts += 1
        baseline_totals.append(baseline_val)

        timestamp_str, _is_lunch, _is_dinner = _timestamp_for_index(idx)
        recs = rerank_recommendations(
            cart_items=anchor_cart,
            active_promotions=inputs["promotions_list"],
            affinity_rules=inputs["affinity_rules"],
            menu_items=inputs["menu_records"],
            timestamp=timestamp_str,
            bandit_weights=bandit_weights,
            bandit_mode="expected"
        )

        hybrid_val = anchor_value
        accepted_items = set()
        for rec in recs[:panel_size]:
            rec_item = rec.get("name")
            if rec_item in held_out_set and rec_item not in accepted_items:
                hybrid_val += _recommended_price(rec, menu_price_lookup)
                accepted_items.add(rec_item)
                hybrid_accepts += 1
        hybrid_totals.append(hybrid_val)

    return _calculate_metrics(
        baseline_totals,
        hybrid_totals,
        DEFAULT_BENCHMARK_MODE,
        panel_size,
        extra={
            "total_orders_seen": len(inputs["grouped_orders"]),
            "skipped_orders": skipped_orders,
            "baseline_accepts": baseline_accepts,
            "hybrid_accepts": hybrid_accepts,
            "final_weights": bandit_weights,
            "seed": seed,
        }
    )


def _run_conservative_full_order(inputs, seed=42):
    # Seeded runs are useful for tests; seed=None gives the web demo a fresh
    # Monte Carlo replay instead of the same fixed result on every click.
    if seed is not None:
        random.seed(seed)
    rng = random.Random(seed)

    menu_price_lookup = inputs["menu_price_lookup"]
    menu_category_lookup = inputs["menu_category_lookup"]
    baseline_support = inputs["baseline_support"]
    promotions_list = inputs["promotions_list"]

    # Default item for baseline model
    default_baseline_item = "Pepsi"
    default_baseline_price = menu_price_lookup.get(default_baseline_item, 0.0)
    default_baseline_support = baseline_support.get(default_baseline_item, 0.0)
    sorted_by_popularity = inputs["sorted_by_popularity"]

    baseline_totals = []
    hybrid_totals = []

    bandit_weights = dict(DEFAULT_BANDIT_WEIGHTS)

    # Create temporary file for bandit weights during simulation run
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        temp_weights_path = tmp.name

    from bandit import save_bandit_weights, update_bandit_weights
    save_bandit_weights(bandit_weights, path=temp_weights_path)

    try:
        for idx, (_order_id, original_items) in enumerate(inputs["grouped_orders"].items()):
            original_value = sum(menu_price_lookup.get(item, 0.0) for item in original_items)
            timestamp_str, is_lunch, is_dinner = _timestamp_for_index(idx)
            active_promos = _active_promos_for_context(promotions_list, is_lunch, is_dinner)

            baseline_val = original_value
            if default_baseline_item not in original_items:
                # Customer accepts default item based on its baseline support.
                if rng.random() < default_baseline_support:
                    baseline_val += default_baseline_price
            baseline_totals.append(baseline_val)

            hybrid_val = original_value
            recs = rerank_recommendations(
                cart_items=original_items,
                active_promotions=promotions_list,
                affinity_rules=inputs["affinity_rules"],
                menu_items=inputs["menu_records"],
                timestamp=timestamp_str,
                bandit_weights=bandit_weights,
                bandit_mode="sample"
            )

            rec_item = None
            rec = None
            p_accept = 0.0
            if recs:
                # Top candidate from reranker is already sorted and excludes cart items.
                rec = recs[0]
                rec_item = rec["name"]
                p_accept = rec["score"]
            else:
                for item in sorted_by_popularity:
                    if item not in original_items:
                        rec_item = item
                        rec = {"name": item}
                        break
                if rec_item:
                    p_accept = baseline_support.get(rec_item, 0.0)

            accepted = False
            if rec_item:
                p_accept = min(1.0, max(0.0, p_accept))
                if rng.random() < p_accept:
                    hybrid_val += _recommended_price(rec, menu_price_lookup)
                    accepted = True

            if rec_item:
                item_category = menu_category_lookup.get(rec_item, "")
                item_category_lower = item_category.lower()
                promo_active = any(
                    is_item_in_promotion(rec_item, item_category, promo)
                    for promo in active_promos
                )

                time_active = False
                if is_lunch and item_category_lower in ["burgers", "combos"]:
                    time_active = True
                elif is_dinner and item_category_lower in ["combos", "sides"]:
                    time_active = True

                bandit_weights = update_bandit_weights(
                    accepted=accepted,
                    promo_active=promo_active,
                    time_active=time_active,
                    path=temp_weights_path
                )

            hybrid_totals.append(hybrid_val)
    finally:
        try:
            os.unlink(temp_weights_path)
        except Exception:
            pass

    return _calculate_metrics(
        baseline_totals,
        hybrid_totals,
        CONSERVATIVE_MODE,
        1,
        extra={
            "final_weights": bandit_weights,
            "seed": seed,
        }
    )


def run_backtest_simulation(seed=42, mode=DEFAULT_BENCHMARK_MODE, panel_size=DEFAULT_PANEL_SIZE, include_conservative=True):
    inputs = _load_backtest_inputs()

    if mode in ("conservative", CONSERVATIVE_MODE, "full_order"):
        return _run_conservative_full_order(inputs, seed=seed)

    if mode not in (DEFAULT_BENCHMARK_MODE, "panel", "default"):
        raise ValueError(f"Unknown backtest mode: {mode}")

    result = _run_partial_cart_panel(inputs, seed=seed, panel_size=panel_size)
    if include_conservative:
        result["conservative_result"] = _run_conservative_full_order(inputs, seed=seed)
    return result

if __name__ == "__main__":
    print("Starting AOV Uplift Backtest Simulation...")
    try:
        results = run_backtest_simulation(seed=42)
        print("\n================ BACKTEST SIMULATION RESULTS ================")
        print("Benchmark Mode:               Synthetic partial-cart top-3 panel")
        print(f"Eligible Transactions:        {results.get('total_simulated', 0)}")
        print(f"Skipped Single-Item Orders:   {results.get('skipped_orders', 0)}")
        print(f"Baseline AOV:                 {format_price_vnd(results['baseline_aov'])} VND")
        print(f"Hybrid Recommender AOV:       {format_price_vnd(results['hybrid_aov'])} VND")
        print(f"Absolute AOV Uplift:          +{format_price_vnd(results['absolute_change'])} VND")
        print(f"Percentage AOV Uplift:        +{results['percentage_uplift']:.2f}%")
        conservative = results.get("conservative_result")
        if conservative:
            print("\nSecondary Conservative Check:")
            print("Mode:                         Full-order top-1 Monte Carlo")
            print(f"Total Transactions Simulated: {conservative.get('total_simulated', 0)}")
            print(f"Percentage AOV Uplift:        +{conservative['percentage_uplift']:.2f}%")
        print("=============================================================")
    except Exception as e:
        print(f"Error running simulation: {e}")
        import traceback
        traceback.print_exc()
