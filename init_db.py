import os
import sys
import sqlite3
import json
import pandas as pd


def _optional_cell(row, column):
    value = row.get(column)
    if pd.isna(value) or str(value).strip() == "":
        return None
    return value


def _optional_float(row, column):
    value = _optional_cell(row, column)
    return float(value) if value is not None else None


def _optional_int(row, column, default=0):
    value = _optional_cell(row, column)
    return int(float(value)) if value is not None else default


def init_db(data_dir=None):
    if data_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "_bmad-output", "data")

    menu_path = os.path.join(data_dir, "menu.csv")
    promo_path = os.path.join(data_dir, "promotions.csv")
    orders_path = os.path.join(data_dir, "orders.csv")
    rules_path = os.path.join(data_dir, "affinity_rules.json")
    db_path = os.path.join(data_dir, "kiosk.db")

    # Check if files exist
    if not os.path.exists(menu_path):
        print(f"Error: menu.csv not found at {menu_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(promo_path):
        print(f"Error: promotions.csv not found at {promo_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(orders_path):
        print(f"Error: orders.csv not found at {orders_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(rules_path):
        print(f"Error: affinity_rules.json not found at {rules_path}", file=sys.stderr)
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

    # Read orders CSV
    try:
        orders_df = pd.read_csv(orders_path)
    except Exception as e:
        print(f"Error: Failed to read orders.csv: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate orders columns
    required_orders_cols = {'order_id', 'item_name'}
    missing_orders_cols = required_orders_cols - set(orders_df.columns)
    if missing_orders_cols:
        print(f"Error: orders.csv is missing required columns: {missing_orders_cols}", file=sys.stderr)
        sys.exit(1)

    # Read affinity rules JSON
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            rules_data = json.load(f)
    except Exception as e:
        print(f"Error: Failed to read affinity_rules.json: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(rules_data, list):
        print("Error: affinity_rules.json must contain a JSON list.", file=sys.stderr)
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

        for optional_numeric_col in ["amount_off_vnd", "sale_price"]:
            if optional_numeric_col in promo_df.columns and not pd.isna(row.get(optional_numeric_col)) and str(row.get(optional_numeric_col)).strip() != "":
                try:
                    numeric_val = float(row.get(optional_numeric_col))
                    if numeric_val < 0:
                        raise ValueError(f"{optional_numeric_col} cannot be negative.")
                except (ValueError, TypeError) as e:
                    print(f"Error: Promotions row {idx+2} (promo: {row.get('name')}) has an invalid {optional_numeric_col} '{row.get(optional_numeric_col)}'. Details: {e}", file=sys.stderr)
                    sys.exit(1)

    # Validate orders data rows
    for idx, row in orders_df.iterrows():
        if pd.isna(row.get('order_id')) or str(row.get('order_id')).strip() == "":
            print(f"Error: Orders row {idx+2} contains a missing or empty order_id field.", file=sys.stderr)
            sys.exit(1)
        if pd.isna(row.get('item_name')) or str(row.get('item_name')).strip() == "":
            print(f"Error: Orders row {idx+2} (order: {row.get('order_id')}) contains a missing or empty item_name field.", file=sys.stderr)
            sys.exit(1)

    # Validate affinity rules data
    required_rule_keys = {'antecedents', 'consequents', 'support', 'confidence', 'lift'}
    for idx, rule in enumerate(rules_data):
        if not isinstance(rule, dict):
            print(f"Error: Rule at index {idx} is not a JSON object.", file=sys.stderr)
            sys.exit(1)
        missing_keys = required_rule_keys - set(rule.keys())
        if missing_keys:
            print(f"Error: Rule at index {idx} is missing required fields: {missing_keys}", file=sys.stderr)
            sys.exit(1)
        if not isinstance(rule['antecedents'], list) or not isinstance(rule['consequents'], list):
            print(f"Error: Rule at index {idx} has invalid antecedents or consequents (must be lists).", file=sys.stderr)
            sys.exit(1)
        for key in ['support', 'confidence', 'lift']:
            try:
                float(rule[key])
            except (ValueError, TypeError):
                print(f"Error: Rule at index {idx} has invalid non-numeric value for '{key}'.", file=sys.stderr)
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
        cursor.execute("DROP TABLE IF EXISTS orders;")
        cursor.execute("DROP TABLE IF EXISTS affinity_rules;")

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
                end_date TEXT NOT NULL,
                target_item TEXT,
                target_category TEXT,
                discount_type TEXT,
                amount_off_vnd REAL,
                sale_price REAL,
                display_text TEXT,
                is_dynamic INTEGER DEFAULT 0
            );
        """)

        # Create orders table
        cursor.execute("""
            CREATE TABLE orders (
                order_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                scenario TEXT,
                PRIMARY KEY (order_id, item_name)
            );
        """)

        # Create affinity_rules table
        cursor.execute("""
            CREATE TABLE affinity_rules (
                rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                antecedents TEXT NOT NULL,
                consequents TEXT NOT NULL,
                support REAL NOT NULL,
                confidence REAL NOT NULL,
                lift REAL NOT NULL
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
            target_item = _optional_cell(row, 'target_item') if 'target_item' in promo_df.columns else None
            target_category = _optional_cell(row, 'target_category') if 'target_category' in promo_df.columns else None
            discount_type = _optional_cell(row, 'discount_type') if 'discount_type' in promo_df.columns else None
            amount_off_vnd = _optional_float(row, 'amount_off_vnd') if 'amount_off_vnd' in promo_df.columns else None
            sale_price = _optional_float(row, 'sale_price') if 'sale_price' in promo_df.columns else None
            display_text = _optional_cell(row, 'display_text') if 'display_text' in promo_df.columns else None
            is_dynamic = _optional_int(row, 'is_dynamic') if 'is_dynamic' in promo_df.columns else 0
            cursor.execute(
                """
                INSERT INTO promotions (
                    promo_id, name, discount_pct, start_date, end_date,
                    target_item, target_category, discount_type, amount_off_vnd,
                    sale_price, display_text, is_dynamic
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    row['promo_id'],
                    row['name'],
                    float(row['discount_pct']),
                    row['start_date'],
                    row['end_date'],
                    target_item,
                    target_category,
                    discount_type,
                    amount_off_vnd,
                    sale_price,
                    display_text,
                    is_dynamic
                )
            )

        # Insert orders
        for _, row in orders_df.iterrows():
            scenario = row.get('scenario') if 'scenario' in orders_df.columns and not pd.isna(row.get('scenario')) else None
            cursor.execute(
                "INSERT INTO orders (order_id, item_name, scenario) VALUES (?, ?, ?);",
                (row['order_id'], row['item_name'], scenario)
            )

        # Insert affinity rules
        for rule in rules_data:
            cursor.execute(
                "INSERT INTO affinity_rules (antecedents, consequents, support, confidence, lift) VALUES (?, ?, ?, ?, ?);",
                (
                    json.dumps(rule['antecedents'], ensure_ascii=False),
                    json.dumps(rule['consequents'], ensure_ascii=False),
                    float(rule['support']),
                    float(rule['confidence']),
                    float(rule['lift'])
                )
            )

        # Validate row counts from SQLite against source dataframe/list
        cursor.execute("SELECT COUNT(*) FROM menu;")
        db_menu_count = cursor.fetchone()[0]
        if db_menu_count != len(menu_df):
            raise ValueError(f"Validation mismatch: menu count in CSV ({len(menu_df)}) does not match DB ({db_menu_count})")

        cursor.execute("SELECT COUNT(*) FROM promotions;")
        db_promo_count = cursor.fetchone()[0]
        if db_promo_count != len(promo_df):
            raise ValueError(f"Validation mismatch: promotions count in CSV ({len(promo_df)}) does not match DB ({db_promo_count})")

        cursor.execute("SELECT COUNT(*) FROM orders;")
        db_orders_count = cursor.fetchone()[0]
        if db_orders_count != len(orders_df):
            raise ValueError(f"Validation mismatch: orders count in CSV ({len(orders_df)}) does not match DB ({db_orders_count})")

        cursor.execute("SELECT COUNT(*) FROM affinity_rules;")
        db_rules_count = cursor.fetchone()[0]
        if db_rules_count != len(rules_data):
            raise ValueError(f"Validation mismatch: rules count in JSON ({len(rules_data)}) does not match DB ({db_rules_count})")

        conn.commit()
        print(f"Successfully initialized SQLite database at {db_path}")
        print(f"Imported {len(menu_df)} menu items, {len(promo_df)} promotions, {len(orders_df)} order items, and {len(rules_data)} affinity rules.")

    except Exception as e:
        print(f"Error: Database operation failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    init_db()
