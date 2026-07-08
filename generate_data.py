import os
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def infer_category(name):
    name_lower = str(name or "").lower()
    if "combo" in name_lower or "bucket" in name_lower:
        return "Combos"
    if "burger" in name_lower:
        return "Burgers"
    if any(d in name_lower for d in ["pepsi", "7up", "lipton"]):
        return "Drinks"
    if "eggtart" in name_lower or "tart" in name_lower:
        return "Desserts"
    return "Sides"

def infer_order_role(name, category):
    name_lower = str(name or "").lower()
    category_lower = str(category or "").lower()
    if category_lower == "drinks" or any(d in name_lower for d in ["pepsi", "7up", "lipton"]):
        return "drink"
    if category_lower == "desserts" or any(d in name_lower for d in ["eggtart", "tart"]):
        return "dessert"
    if category_lower in ["combos", "burgers"] or any(word in name_lower for word in ["combo", "bucket", "burger"]):
        return "main"
    if any(word in name_lower for word in ["chicken", "tender", "rice", "pasta", "fish", "fillet"]):
        return "main"
    return "side"

def unique_names(names):
    return list(dict.fromkeys(names))

def matching_names(df_menu, predicate):
    return unique_names([
        row["name"]
        for _, row in df_menu.iterrows()
        if predicate(str(row["name"]), str(row["category"]))
    ])

def choose(items):
    return random.choice(items) if items else None

def add_if_present(order_items, item):
    if item:
        order_items.add(item)

def add_optional(order_items, items, probability):
    if random.random() < probability:
        add_if_present(order_items, choose(items))

def build_strata(total_orders):
    scenario_weights = [
        ("burger_meal", 0.14),
        ("fried_chicken_meal", 0.14),
        ("rice_meal", 0.14),
        ("pasta_meal", 0.12),
        ("popcorn_snack_meal", 0.12),
        ("bucket_group_meal", 0.14),
        ("dessert_led_basket", 0.10),
        ("drink_led_snack_basket", 0.08),
        ("exploratory_basket", 0.02),
    ]
    counts = []
    assigned = 0
    for idx, (name, weight) in enumerate(scenario_weights):
        if idx == len(scenario_weights) - 1:
            count = total_orders - assigned
        else:
            count = int(total_orders * weight)
            assigned += count
        counts.append((name, count))
    return counts

def load_or_create_menu():
    kfc_menu_path = "kfc_menu.csv"
    output_dir = "_bmad-output/data"
    os.makedirs(output_dir, exist_ok=True)
    
    if os.path.exists(kfc_menu_path):
        df_raw = pd.read_csv(kfc_menu_path)
        menu_items = []
        for idx, row in df_raw.iterrows():
            name = str(row['name']).strip()
            # Determine price: use dis_price if numeric, else org_price
            price = row['org_price']
            if pd.notna(row['dis_price']) and str(row['dis_price']).strip() != "":
                try:
                    price = float(row['dis_price'])
                except ValueError:
                    pass
            
            category = infer_category(name)
                
            # Get image column if exists
            image_val = str(row['image']).strip() if 'image' in df_raw.columns and pd.notna(row['image']) else ""
                
            menu_items.append({
                "item_id": f"ITEM_{idx+1:03d}",
                "name": name,
                "category": category,
                "price": float(price) if pd.notna(price) else 0.0,
                "image": image_val
            })
        df_menu = pd.DataFrame(menu_items)
    else:
        # Fallback default menu items if kfc_menu.csv doesn't exist
        default_items = [
            {"item_id": "ITEM_001", "name": "Burger Zinger", "category": "Burgers", "price": 56000.0, "image": ""},
            {"item_id": "ITEM_002", "name": "Burger Shrimp", "category": "Burgers", "price": 45000.0, "image": ""},
            {"item_id": "ITEM_003", "name": "Roasted Fillet Chicken Burger", "category": "Burgers", "price": 56000.0, "image": ""},
            {"item_id": "ITEM_004", "name": "Burger Yo (Chicken)", "category": "Burgers", "price": 30000.0, "image": ""},
            {"item_id": "ITEM_005", "name": "French Fries", "category": "Sides", "price": 20000.0, "image": ""},
            {"item_id": "ITEM_007", "name": "1 Fried Chicken", "category": "Sides", "price": 37000.0, "image": ""},
            {"item_id": "ITEM_008", "name": "2 Fried Chicken", "category": "Sides", "price": 74000.0, "image": ""},
            {"item_id": "ITEM_009", "name": "3 Tenders Chicken", "category": "Sides", "price": 42000.0, "image": ""},
            {"item_id": "ITEM_010", "name": "Coleslaw", "category": "Sides", "price": 13000.0, "image": ""},
            {"item_id": "ITEM_011", "name": "Pepsi", "category": "Drinks", "price": 13000.0, "image": ""},
            {"item_id": "ITEM_012", "name": "7Up", "category": "Drinks", "price": 13000.0, "image": ""},
            {"item_id": "ITEM_015", "name": "1 Eggtart", "category": "Desserts", "price": 20000.0, "image": ""},
        ]
        df_menu = pd.DataFrame(default_items)
        
    df_menu.to_csv(os.path.join(output_dir, "menu.csv"), index=False)
    print(f"Created menu.csv with {len(df_menu)} items.")
    return df_menu

def generate_promotions():
    output_dir = "_bmad-output/data"
    promotions = [
        {"promo_id": "PROMO_001", "name": "Lunch Special Burger Combo", "discount_pct": 15, "start_date": "2026-06-01", "end_date": "2026-08-31"},
        {"promo_id": "PROMO_002", "name": "Happy Bucket Discount", "discount_pct": 10, "start_date": "2026-07-01", "end_date": "2026-07-31"},
        {"promo_id": "PROMO_003", "name": "Free Drink with Fried Chicken", "discount_pct": 100, "start_date": "2026-07-04", "end_date": "2026-07-06"},
        {"promo_id": "PROMO_004", "name": "Dessert Delight", "discount_pct": 20, "start_date": "2026-05-01", "end_date": "2026-12-31"},
    ]
    df_promo = pd.DataFrame(promotions)
    df_promo.to_csv(os.path.join(output_dir, "promotions.csv"), index=False)
    print(f"Created promotions.csv with {len(df_promo)} promos.")

def generate_orders(df_menu):
    output_dir = "_bmad-output/data"
    total_orders = 5000

    burgers = matching_names(df_menu, lambda name, cat: cat == "Burgers")
    combos = matching_names(df_menu, lambda name, cat: cat == "Combos")
    drinks = matching_names(df_menu, lambda name, cat: cat == "Drinks")
    desserts = matching_names(df_menu, lambda name, cat: cat == "Desserts")
    fried_chicken = matching_names(
        df_menu,
        lambda name, cat: (
            infer_order_role(name, cat) == "main"
            and "chicken" in name.lower()
            and "burger" not in name.lower()
            and "combo" not in name.lower()
            and "bucket" not in name.lower()
            and "rice" not in name.lower()
            and "pasta" not in name.lower()
        )
    )
    rice_pasta = matching_names(
        df_menu,
        lambda name, cat: infer_order_role(name, cat) == "main" and any(word in name.lower() for word in ["rice", "pasta"])
    )
    rice_meals = matching_names(
        df_menu,
        lambda name, cat: infer_order_role(name, cat) == "main" and "rice" in name.lower()
    )
    pasta_meals = matching_names(
        df_menu,
        lambda name, cat: infer_order_role(name, cat) == "main" and "pasta" in name.lower()
    )
    snack_sides = matching_names(
        df_menu,
        lambda name, cat: infer_order_role(name, cat) == "side" and any(
            word in name.lower()
            for word in ["fries", "popcorn", "coleslaw", "mashed", "soup", "salad"]
        )
    )
    popcorn_snacks = matching_names(
        df_menu,
        lambda name, cat: "popcorn" in name.lower() or "chewy cheese" in name.lower()
    )
    bucket_group_meals = matching_names(
        df_menu,
        lambda name, cat: cat == "Combos" and any(
            word in name.lower()
            for word in ["bucket", "group", "party", "together", "cheers", "big combo"]
        )
    )

    fries = matching_names(df_menu, lambda name, cat: "fries" in name.lower())
    cola_sides = matching_names(df_menu, lambda name, cat: any(word in name.lower() for word in ["coleslaw", "mashed"]))
    pepsi_drinks = matching_names(df_menu, lambda name, cat: "pepsi" in name.lower()) or drinks
    eggtarts = matching_names(df_menu, lambda name, cat: "eggtart" in name.lower()) or desserts
    soups_salads = matching_names(df_menu, lambda name, cat: any(word in name.lower() for word in ["soup", "salad"]))
    mains = unique_names(burgers + fried_chicken + rice_pasta + combos)

    orders = []
    random.seed(42)
    scenario_counts = build_strata(total_orders)
    txn_idx = 1

    for scenario_name, scenario_count in scenario_counts:
        for _ in range(scenario_count):
            order_id = f"TXN_{txn_idx:05d}"
            order_items = set()

            if scenario_name == "burger_meal":
                add_if_present(order_items, choose(burgers))
                add_optional(order_items, fries, 0.74)
                add_optional(order_items, pepsi_drinks, 0.70)
                add_optional(order_items, eggtarts, 0.20)
            elif scenario_name == "fried_chicken_meal":
                add_if_present(order_items, choose(fried_chicken))
                add_optional(order_items, pepsi_drinks, 0.74)
                add_optional(order_items, cola_sides or fries, 0.54)
                add_optional(order_items, eggtarts, 0.16)
            elif scenario_name == "rice_meal":
                add_if_present(order_items, choose(rice_meals or rice_pasta))
                add_optional(order_items, pepsi_drinks, 0.60)
                add_optional(order_items, soups_salads or snack_sides, 0.42)
                add_optional(order_items, eggtarts, 0.14)
            elif scenario_name == "pasta_meal":
                add_if_present(order_items, choose(pasta_meals or rice_pasta))
                add_optional(order_items, pepsi_drinks, 0.58)
                add_optional(order_items, popcorn_snacks or snack_sides, 0.44)
                add_optional(order_items, eggtarts, 0.12)
            elif scenario_name == "popcorn_snack_meal":
                add_if_present(order_items, choose(popcorn_snacks or snack_sides))
                add_optional(order_items, pepsi_drinks, 0.62)
                add_optional(order_items, fries, 0.34)
                add_optional(order_items, mains, 0.26)
            elif scenario_name == "bucket_group_meal":
                add_if_present(order_items, choose(bucket_group_meals or combos))
                add_optional(order_items, pepsi_drinks, 0.52)
                add_optional(order_items, fries, 0.30)
                add_optional(order_items, eggtarts, 0.30)
                add_optional(order_items, cola_sides, 0.26)
            elif scenario_name == "dessert_led_basket":
                add_if_present(order_items, choose(eggtarts))
                add_optional(order_items, pepsi_drinks, 0.58)
                add_optional(order_items, popcorn_snacks or fries, 0.34)
                add_optional(order_items, mains, 0.20)
            elif scenario_name == "drink_led_snack_basket":
                add_if_present(order_items, choose(drinks))
                add_optional(order_items, popcorn_snacks or snack_sides, 0.56)
                add_optional(order_items, fries, 0.40)
                add_optional(order_items, eggtarts, 0.24)
            else:
                num_items = random.randint(1, 4)
                all_items = df_menu['name'].tolist()
                sampled = random.sample(all_items, min(num_items, len(all_items)))
                for item in sampled:
                    order_items.add(item)

            if not order_items:
                add_if_present(order_items, choose(mains or df_menu['name'].tolist()))

            for item in order_items:
                orders.append({
                    "order_id": order_id,
                    "item_name": item,
                    "scenario": scenario_name
                })
            txn_idx += 1

    df_orders = pd.DataFrame(orders)
    df_orders.to_csv(os.path.join(output_dir, "orders.csv"), index=False)
    print(f"Created orders.csv with {len(df_orders)} items in {df_orders['order_id'].nunique()} stratified transactions.")
    for scenario_name, scenario_count in scenario_counts:
        print(f"  {scenario_name}: {scenario_count} orders")

if __name__ == "__main__":
    df_menu = load_or_create_menu()
    generate_promotions()
    generate_orders(df_menu)
