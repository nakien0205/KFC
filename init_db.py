import os
import sys
import sqlite3
import pandas as pd

def init_db(data_dir=None):
    if data_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "_bmad-output", "data")
        
    menu_path = os.path.join(data_dir, "menu.csv")
    promo_path = os.path.join(data_dir, "promotions.csv")
    db_path = os.path.join(data_dir, "kiosk.db")
    
    # Check if files exist
    if not os.path.exists(menu_path):
        print(f"Error: menu.csv not found at {menu_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(promo_path):
        print(f"Error: promotions.csv not found at {promo_path}", file=sys.stderr)
        sys.exit(1)
        
    # Read menu CSV
    try:
        menu_df = pd.read_csv(menu_path)
    except Exception as e:
        print(f"Error: Failed to read menu.csv: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Validate menu columns
    required_menu_cols = {'name', 'category', 'price'}
    missing_menu_cols = required_menu_cols - set(menu_df.columns)
    if missing_menu_cols:
        print(f"Error: menu.csv is missing required columns: {missing_menu_cols}", file=sys.stderr)
        sys.exit(1)
        
    # Read promotions CSV
    try:
        promo_df = pd.read_csv(promo_path)
    except Exception as e:
        print(f"Error: Failed to read promotions.csv: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Validate promotions columns
    required_promo_cols = {'promo_id', 'name', 'discount_pct', 'start_date', 'end_date'}
    missing_promo_cols = required_promo_cols - set(promo_df.columns)
    if missing_promo_cols:
        print(f"Error: promotions.csv is missing required columns: {missing_promo_cols}", file=sys.stderr)
        sys.exit(1)
        
    # Validate menu data rows
    for idx, row in menu_df.iterrows():
        # Check required fields
        if pd.isna(row.get('name')) or str(row.get('name')).strip() == "":
            print(f"Error: Menu row {idx+2} contains a missing or empty name field.", file=sys.stderr)
            sys.exit(1)
        if pd.isna(row.get('category')) or str(row.get('category')).strip() == "":
            print(f"Error: Menu row {idx+2} (item: {row.get('name')}) contains a missing or empty category field.", file=sys.stderr)
            sys.exit(1)
        if pd.isna(row.get('price')):
            print(f"Error: Menu row {idx+2} (item: {row.get('name')}) contains a missing or empty price field.", file=sys.stderr)
            sys.exit(1)
            
        # Validate price is numeric and non-negative
        try:
            price_val = float(row.get('price'))
            if price_val < 0:
                raise ValueError("Price cannot be negative.")
        except (ValueError, TypeError) as e:
            print(f"Error: Menu row {idx+2} (item: {row.get('name')}) has an invalid price '{row.get('price')}'. Details: {e}", file=sys.stderr)
            sys.exit(1)
            
    # Validate promotion data rows
    for idx, row in promo_df.iterrows():
        # Check required fields
        for col in required_promo_cols:
            if pd.isna(row.get(col)) or str(row.get(col)).strip() == "":
                print(f"Error: Promotions row {idx+2} contains a missing or empty '{col}' field.", file=sys.stderr)
                sys.exit(1)
                
        # Validate discount_pct is numeric
        try:
            discount_val = float(row.get('discount_pct'))
            if discount_val < 0 or discount_val > 100:
                raise ValueError("Discount percent must be between 0 and 100.")
        except (ValueError, TypeError) as e:
            print(f"Error: Promotions row {idx+2} (promo: {row.get('name')}) has an invalid discount_pct '{row.get('discount_pct')}'. Details: {e}", file=sys.stderr)
            sys.exit(1)

    # Initialize connection to SQLite
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Drop existing tables to ensure determinism and no duplicate accumulation
        cursor.execute("DROP TABLE IF EXISTS menu;")
        cursor.execute("DROP TABLE IF EXISTS promotions;")
        
        # Create menu table
        # Note: image is optional (can be NULL)
        cursor.execute("""
            CREATE TABLE menu (
                item_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                image TEXT
            );
        """)
        
        # Create promotions table
        cursor.execute("""
            CREATE TABLE promotions (
                promo_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                discount_pct REAL NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL
            );
        """)
        
        # Insert menu items
        for _, row in menu_df.iterrows():
            item_id = row.get('item_id') if not pd.isna(row.get('item_id')) else None
            image = row.get('image') if not pd.isna(row.get('image')) else None
            cursor.execute(
                "INSERT INTO menu (item_id, name, category, price, image) VALUES (?, ?, ?, ?, ?);",
                (item_id, row['name'], row['category'], float(row['price']), image)
            )
            
        # Insert promotions
        for _, row in promo_df.iterrows():
            cursor.execute(
                "INSERT INTO promotions (promo_id, name, discount_pct, start_date, end_date) VALUES (?, ?, ?, ?, ?);",
                (row['promo_id'], row['name'], float(row['discount_pct']), row['start_date'], row['end_date'])
            )
            
        conn.commit()
        print(f"Successfully initialized SQLite database at {db_path}")
        print(f"Imported {len(menu_df)} menu items and {len(promo_df)} promotions.")
        
    except Exception as e:
        print(f"Error: Database operation failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    init_db()
