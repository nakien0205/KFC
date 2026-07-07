import os
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

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
            
            # Categorize items
            name_lower = name.lower()
            meals_str = str(row['meals']).lower() if pd.notna(row['meals']) else ""
            
            if "combo" in name_lower or "bucket" in name_lower:
                category = "Combos"
            elif "burger" in name_lower:
                category = "Burgers"
            elif any(d in name_lower for d in ["pepsi", "7up", "lipton"]):
                category = "Drinks"
            elif "eggtart" in name_lower:
                category = "Desserts"
            else:
                category = "Sides"
                
            menu_items.append({
                "item_id": f"ITEM_{idx+1:03d}",
                "name": name,
                "category": category,
                "price": float(price) if pd.notna(price) else 0.0
            })
        df_menu = pd.DataFrame(menu_items)
    else:
        # Fallback default menu items if kfc_menu.csv doesn't exist
        default_items = [
            {"item_id": "ITEM_001", "name": "Burger Zinger", "category": "Burgers", "price": 56000.0},
            {"item_id": "ITEM_002", "name": "Burger Shrimp", "category": "Burgers", "price": 45000.0},
            {"item_id": "ITEM_003", "name": "Roasted Fillet Chicken Burger", "category": "Burgers", "price": 56000.0},
            {"item_id": "ITEM_004", "name": "Burger Yo (Chicken)", "category": "Burgers", "price": 30000.0},
            {"item_id": "ITEM_005", "name": "French Fries", "category": "Sides", "price": 20000.0},
            {"item_id": "ITEM_007", "name": "1 Fried Chicken", "category": "Sides", "price": 37000.0},
            {"item_id": "ITEM_008", "name": "2 Fried Chicken", "category": "Sides", "price": 74000.0},
            {"item_id": "ITEM_009", "name": "3 Tenders Chicken", "category": "Sides", "price": 42000.0},
            {"item_id": "ITEM_010", "name": "Coleslaw", "category": "Sides", "price": 13000.0},
            {"item_id": "ITEM_011", "name": "Pepsi", "category": "Drinks", "price": 13000.0},
            {"item_id": "ITEM_012", "name": "7Up", "category": "Drinks", "price": 13000.0},
            {"item_id": "ITEM_015", "name": "1 Eggtart", "category": "Desserts", "price": 20000.0},
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
    
    # Retrieve items for each category
    burgers = df_menu[df_menu['category'] == 'Burgers']['name'].tolist()
    sides = df_menu[df_menu['category'] == 'Sides']['name'].tolist()
    drinks = df_menu[df_menu['category'] == 'Drinks']['name'].tolist()
    desserts = df_menu[df_menu['category'] == 'Desserts']['name'].tolist()
    
    orders = []
    random.seed(42)
    
    # We generate 1200 transactions
    for txn_idx in range(1, 1201):
        order_id = f"TXN_{txn_idx:04d}"
        order_items = set()
        
        r = random.random()
        if r < 0.40:
            # 40% Burger orders
            burger = random.choice(burgers) if burgers else "Burger Zinger"
            order_items.add(burger)
            
            # 70% chance to add French Fries (avoiding size dilution)
            if random.random() < 0.70:
                order_items.add("French Fries")
                
            # 65% chance to add Pepsi (avoiding size/sugar dilution)
            if random.random() < 0.65:
                order_items.add("Pepsi")
                
        elif r < 0.60:
            # 20% Fried Chicken orders
            # Focus on 1 Fried Chicken or 2 Fried Chicken to avoid name dilution
            chicken = random.choice(["1 Fried Chicken", "2 Fried Chicken"])
            order_items.add(chicken)
            
            # 80% chance to add Pepsi
            if random.random() < 0.80:
                order_items.add("Pepsi")
                
        elif r < 0.75:
            # 15% Desserts alone
            dessert = random.choice(desserts) if desserts else "1 Eggtart"
            order_items.add(dessert)
            if random.random() < 0.20 and desserts:
                order_items.add(random.choice(desserts))
                
        else:
            # 25% Random mixtures
            num_items = random.randint(1, 4)
            all_items = df_menu['name'].tolist()
            sampled = random.sample(all_items, min(num_items, len(all_items)))
            for item in sampled:
                order_items.add(item)
                
        # Append rows to orders list
        for item in order_items:
            orders.append({
                "order_id": order_id,
                "item_name": item
            })
            
    df_orders = pd.DataFrame(orders)
    df_orders.to_csv(os.path.join(output_dir, "orders.csv"), index=False)
    print(f"Created orders.csv with {len(df_orders)} items in {df_orders['order_id'].nunique()} transactions.")

if __name__ == "__main__":
    df_menu = load_or_create_menu()
    generate_promotions()
    generate_orders(df_menu)
