import unittest
import os
import tempfile
import sqlite3
import shutil
import json
import pandas as pd
from init_db import init_db

class TestSQLiteInitialization(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for database and CSV/JSON files
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "kiosk.db")

        # Create valid menu and promotions dataframes
        self.menu_data = pd.DataFrame([
            {"item_id": "ITEM_001", "name": "Burger Zinger", "category": "Burgers", "price": 85000.0, "image": "burger.jpg"},
            {"item_id": "ITEM_002", "name": "Pepsi", "category": "Drinks", "price": 19000.0, "image": "pepsi.jpg"},
            {"item_id": "ITEM_003", "name": "Burger Combo", "category": "Burgers", "price": 85000.0, "image": "burger2.jpg"}
        ])

        self.promo_data = pd.DataFrame([
            {
                "promo_id": "PROMO_001",
                "name": "Promo 1",
                "discount_pct": 15.0,
                "start_date": "2026-06-01",
                "end_date": "2026-08-31",
                "target_item": "Burger Zinger",
                "target_category": "Burgers",
                "discount_type": "amount",
                "amount_off_vnd": 13000,
                "sale_price": 72000,
                "display_text": "Giảm 13.000đ",
                "is_dynamic": 1,
            }
        ])

        # Create valid orders dataframe
        self.orders_data = pd.DataFrame([
            {"order_id": "TXN_00001", "item_name": "Burger Zinger", "scenario": "burger_meal"},
            {"order_id": "TXN_00001", "item_name": "Pepsi", "scenario": "burger_meal"},
            {"order_id": "TXN_00002", "item_name": "Burger Combo", "scenario": "burger_meal"}
        ])

        # Create valid affinity rules list
        self.rules_data = [
            {
                "antecedents": ["Burger Zinger"],
                "consequents": ["Pepsi"],
                "support": 0.1,
                "confidence": 0.7,
                "lift": 1.5
            }
        ]

        # Write valid files
        self.menu_data.to_csv(os.path.join(self.test_dir, "menu.csv"), index=False)
        self.promo_data.to_csv(os.path.join(self.test_dir, "promotions.csv"), index=False)
        self.orders_data.to_csv(os.path.join(self.test_dir, "orders.csv"), index=False)
        with open(os.path.join(self.test_dir, "affinity_rules.json"), "w", encoding="utf-8") as f:
            json.dump(self.rules_data, f)

    def tearDown(self):
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def test_successful_initialization(self):
        # Run init_db on the temporary directory
        try:
            init_db(self.test_dir)
        except SystemExit as e:
            self.assertEqual(e.code, 0)

        # Verify DB exists
        self.assertTrue(os.path.exists(self.db_path))

        # Connect and check tables content
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM menu;")
        menu_count = cursor.fetchone()[0]
        self.assertEqual(menu_count, 3)

        cursor.execute("SELECT name, category, price FROM menu WHERE item_id='ITEM_001';")
        row = cursor.fetchone()
        self.assertEqual(row, ("Burger Zinger", "Burgers", 85000.0))

        cursor.execute("SELECT COUNT(*) FROM promotions;")
        promo_count = cursor.fetchone()[0]
        self.assertEqual(promo_count, 1)

        cursor.execute("SELECT target_item, discount_type, amount_off_vnd, sale_price, display_text, is_dynamic FROM promotions WHERE promo_id='PROMO_001';")
        promo_row = cursor.fetchone()
        self.assertEqual(promo_row, ("Burger Zinger", "amount", 13000.0, 72000.0, "Giảm 13.000đ", 1))

        cursor.execute("SELECT COUNT(*) FROM orders;")
        orders_count = cursor.fetchone()[0]
        self.assertEqual(orders_count, 3)

        cursor.execute("SELECT scenario FROM orders WHERE order_id='TXN_00001' AND item_name='Pepsi';")
        scenario_row = cursor.fetchone()
        self.assertEqual(scenario_row[0], "burger_meal")

        cursor.execute("SELECT COUNT(*) FROM affinity_rules;")
        rules_count = cursor.fetchone()[0]
        self.assertEqual(rules_count, 1)

        cursor.execute("SELECT antecedents, consequents, confidence FROM affinity_rules;")
        rule_row = cursor.fetchone()
        self.assertEqual(json.loads(rule_row[0]), ["Burger Zinger"])
        self.assertEqual(json.loads(rule_row[1]), ["Pepsi"])
        self.assertEqual(rule_row[2], 0.7)

        conn.close()

    def test_determinism_and_no_duplicates(self):
        # Run initialization twice
        init_db(self.test_dir)
        init_db(self.test_dir)

        # Verify counts are still the same
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM menu;")
        self.assertEqual(cursor.fetchone()[0], 3)
        cursor.execute("SELECT COUNT(*) FROM promotions;")
        self.assertEqual(cursor.fetchone()[0], 1)
        cursor.execute("SELECT COUNT(*) FROM orders;")
        self.assertEqual(cursor.fetchone()[0], 3)
        cursor.execute("SELECT COUNT(*) FROM affinity_rules;")
        self.assertEqual(cursor.fetchone()[0], 1)
        conn.close()

    def test_dynamic_flag_accepts_float_like_csv_value(self):
        promo_data = self.promo_data.copy()
        promo_data["is_dynamic"] = ["1.0"]
        promo_data.to_csv(os.path.join(self.test_dir, "promotions.csv"), index=False)

        init_db(self.test_dir)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT is_dynamic FROM promotions WHERE promo_id='PROMO_001';")
        self.assertEqual(cursor.fetchone()[0], 1)
        conn.close()

    def test_missing_menu_field_validation(self):
        # Create menu CSV with a missing category field in one row
        invalid_menu = pd.DataFrame([
            {"item_id": "ITEM_001", "name": "Burger Combo", "category": "", "price": 85000.0}, # empty category
        ])
        invalid_menu.to_csv(os.path.join(self.test_dir, "menu.csv"), index=False)

        # Expect system exit with code 1
        with self.assertRaises(SystemExit) as cm:
            init_db(self.test_dir)
        self.assertEqual(cm.exception.code, 1)

    def test_missing_menu_column_validation(self):
        # Create menu CSV with missing price column
        invalid_menu = pd.DataFrame([
            {"item_id": "ITEM_001", "name": "Burger Combo", "category": "Burgers"},
        ])
        invalid_menu.to_csv(os.path.join(self.test_dir, "menu.csv"), index=False)

        # Expect system exit with code 1
        with self.assertRaises(SystemExit) as cm:
            init_db(self.test_dir)
        self.assertEqual(cm.exception.code, 1)

    def test_invalid_price_validation(self):
        # Create menu CSV with negative price
        invalid_menu = pd.DataFrame([
            {"item_id": "ITEM_001", "name": "Burger Combo", "category": "Burgers", "price": -500.0},
        ])
        invalid_menu.to_csv(os.path.join(self.test_dir, "menu.csv"), index=False)

        # Expect system exit with code 1
        with self.assertRaises(SystemExit) as cm:
            init_db(self.test_dir)
        self.assertEqual(cm.exception.code, 1)

    def test_missing_orders_column_validation(self):
        # Create orders CSV with missing item_name column
        invalid_orders = pd.DataFrame([
            {"order_id": "TXN_00001"},
        ])
        invalid_orders.to_csv(os.path.join(self.test_dir, "orders.csv"), index=False)

        with self.assertRaises(SystemExit) as cm:
            init_db(self.test_dir)
        self.assertEqual(cm.exception.code, 1)

    def test_missing_orders_field_validation(self):
        # Create orders CSV with missing order_id in one row
        invalid_orders = pd.DataFrame([
            {"order_id": "", "item_name": "Pepsi"},
        ])
        invalid_orders.to_csv(os.path.join(self.test_dir, "orders.csv"), index=False)

        with self.assertRaises(SystemExit) as cm:
            init_db(self.test_dir)
        self.assertEqual(cm.exception.code, 1)

    def test_missing_rules_field_validation(self):
        # Create affinity rules with missing confidence
        invalid_rules = [
            {
                "antecedents": ["Burger Zinger"],
                "consequents": ["Pepsi"],
                "support": 0.1,
                "lift": 1.5
            }
        ]
        with open(os.path.join(self.test_dir, "affinity_rules.json"), "w", encoding="utf-8") as f:
            json.dump(invalid_rules, f)

        with self.assertRaises(SystemExit) as cm:
            init_db(self.test_dir)
        self.assertEqual(cm.exception.code, 1)

if __name__ == "__main__":
    unittest.main()
