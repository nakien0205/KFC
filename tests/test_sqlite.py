import unittest
import os
import tempfile
import sqlite3
import shutil
import pandas as pd
from init_db import init_db

class TestSQLiteInitialization(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for database and CSV files
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "kiosk.db")
        
        # Create valid menu and promotions dataframes
        self.menu_data = pd.DataFrame([
            {"item_id": "ITEM_001", "name": "Burger Combo", "category": "Burgers", "price": 85000.0, "image": "burger.jpg"},
            {"item_id": "ITEM_002", "name": "Pepsi", "category": "Drinks", "price": 19000.0, "image": "pepsi.jpg"},
            {"item_id": "ITEM_003", "name": "Burger Combo", "category": "Burgers", "price": 85000.0, "image": "burger2.jpg"} # Duplicate name is allowed
        ])
        
        self.promo_data = pd.DataFrame([
            {"promo_id": "PROMO_001", "name": "Promo 1", "discount_pct": 15.0, "start_date": "2026-06-01", "end_date": "2026-08-31"}
        ])
        
        # Write valid files
        self.menu_data.to_csv(os.path.join(self.test_dir, "menu.csv"), index=False)
        self.promo_data.to_csv(os.path.join(self.test_dir, "promotions.csv"), index=False)

    def tearDown(self):
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def test_successful_initialization(self):
        # Run init_db on the temporary directory
        # Since it exits on failure, we expect it to complete normally
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
        self.assertEqual(row, ("Burger Combo", "Burgers", 85000.0))
        
        cursor.execute("SELECT COUNT(*) FROM promotions;")
        promo_count = cursor.fetchone()[0]
        self.assertEqual(promo_count, 1)
        
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

if __name__ == "__main__":
    unittest.main()
