import unittest
from unittest.mock import patch, MagicMock, mock_open
from fastapi.testclient import TestClient
import pandas as pd
import os
import json

from main import app

class TestMainAPI(unittest.TestCase):
    def setUp(self):
        # Patch weights path to a temporary file so tests don't overwrite production weights
        import tempfile
        import bandit
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_weights_path = os.path.join(self.temp_dir.name, "temp_bandit_weights.json")
        self.weights_patcher = patch('bandit.WEIGHTS_PATH', self.temp_weights_path)
        self.weights_patcher.start()

        # TestClient as context manager ensures lifespan startup and shutdown run
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.weights_patcher.stop()
        self.temp_dir.cleanup()

    @patch('main.generate_recommendation_copy')
    def test_recommend_endpoint_success(self, mock_generate_copy):
        mock_generate_copy.return_value = {
            "copy": "Gợi ý kiểm thử",
            "rationale": "Không gọi mạng trong test."
        }
        payload = {
            "cart_items": ["Burger Zinger"],
            "timestamp": "2026-07-06T12:00:00+07:00"
        }
        response = self.client.post("/api/recommend", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        if len(data) > 0:
            item = data[0]
            self.assertIn("name", item)
            self.assertIn("price", item)
            self.assertIn("score", item)
            self.assertIn("copy", item)
            self.assertIn("rationale", item)
            self.assertNotIn(item["name"], payload["cart_items"])
            self.assertIsInstance(item["price"], float)

    @patch('main.rerank_recommendations')
    @patch('main.generate_recommendation_copy')
    def test_recommend_endpoint_uses_sale_price_and_promo_context(self, mock_generate_copy, mock_rerank):
        mock_rerank.return_value = [
            {
                "name": "Burger Zinger",
                "score": 0.8,
                "sale_price": 46000.0,
                "discount_label": "Giảm 10.000đ",
                "urgency": 0.8,
            }
        ]
        mock_generate_copy.return_value = {
            "copy": "Ưu đãi kiểm thử",
            "rationale": "Khuyến mãi phù hợp."
        }

        response = self.client.post(
            "/api/recommend",
            json={
                "cart_items": ["Pepsi"],
                "timestamp": "2026-07-06T21:00:00+07:00"
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data[0]["price"], 46000.0)
        self.assertEqual(data[0]["copy"], "Ưu đãi kiểm thử")
        call_kwargs = mock_generate_copy.call_args.kwargs
        self.assertEqual(call_kwargs["item_price"], 46000.0)
        self.assertEqual(call_kwargs["promotion_context"]["discount_label"], "Giảm 10.000đ")

    def test_recommend_endpoint_empty_cart(self):
        payload = {
            "cart_items": [],
            "timestamp": "2026-07-06T12:00:00+07:00"
        }
        response = self.client.post("/api/recommend", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])

    def test_recommend_endpoint_invalid_timestamp(self):
        payload = {
            "cart_items": ["Burger Zinger"],
            "timestamp": "invalid-time"
        }
        response = self.client.post("/api/recommend", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])

    @patch('recommender.requests.post')
    def test_recommend_endpoint_with_gemini_mock(self, mock_post):
        # Mock Gemini success path
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"copy": "Ngon tuyệt! Ăn kèm Khoai tây chiên nhé!", "rationale": "Thường được mua kèm Burger Zinger"}'
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        # We set fake GEMINI_API_KEY environment variable if it's not set
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-api-key"}):
            payload = {
                "cart_items": ["Burger Zinger"],
                "timestamp": "2026-07-06T12:00:00+07:00"
            }
            response = self.client.post("/api/recommend", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(len(data) > 0)
            self.assertEqual(data[0]["copy"], "Ngon tuyệt! Ăn kèm Khoai tây chiên nhé!")
            self.assertEqual(data[0]["rationale"], "Thường được mua kèm Burger Zinger")

    def test_serve_index_html(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("KFC", response.text)

    def test_serve_static_style(self):
        response = self.client.get("/static/style.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response.headers.get("content-type", ""))

    def test_menu_endpoint_returns_200(self):
        response = self.client.get("/api/menu")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_menu_endpoint_structure(self):
        response = self.client.get("/api/menu")
        data = response.json()
        if len(data) > 0:
            item = data[0]
            self.assertIn("name", item)
            self.assertIn("category", item)
            self.assertIn("price", item)
            self.assertIsInstance(item["price"], float)

    def test_backtest_endpoint_success(self):
        response = self.client.post("/api/backtest")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("baseline_aov", data)
        self.assertIn("hybrid_aov", data)
        self.assertIn("absolute_change", data)
        self.assertIn("percentage_uplift", data)
        self.assertGreater(data["baseline_aov"], 0)
        self.assertGreater(data["hybrid_aov"], 0)
        self.assertGreater(data["percentage_uplift"], 0)

    @patch('backtest.run_backtest_simulation')
    def test_backtest_endpoint_uses_fixed_demo_seed(self, mock_run):
        mock_run.return_value = {
            "baseline_aov": 100.0,
            "hybrid_aov": 104.0,
            "absolute_change": 4.0,
            "percentage_uplift": 4.0,
            "final_weights": {}
        }

        response = self.client.post("/api/backtest")

        self.assertEqual(response.status_code, 200)
        mock_run.assert_called_once_with(seed=42)
    def test_feedback_endpoint_success(self):
        payload = {
            "recommended_item": "French Fries",
            "accepted": True,
            "context": {
                "promo_active": True,
                "time_active": False
            }
        }
        response = self.client.post("/api/recommend/feedback", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("updated_weights", data)
        self.assertIn("alpha_promo", data["updated_weights"])

class TestMainSQLiteLoading(unittest.TestCase):
    @patch('sqlite3.connect')
    @patch('os.path.exists')
    def test_lifespan_sqlite_loading_success(self, mock_exists, mock_connect):
        def side_effect(path):
            if "kiosk.db" in path:
                return True
            return False
        mock_exists.side_effect = side_effect

        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        menu_df = pd.DataFrame([
            {"name": "SQLite Burger", "category": "Burgers", "price": 50000.0, "image": "img.png"}
        ])
        promo_df = pd.DataFrame([
            {"promo_id": "P1", "name": "SQLite Promo", "discount_pct": 10.0, "start_date": "2026-07-01", "end_date": "2026-07-31"}
        ])

        def read_sql_side_effect(query, conn):
            if "menu" in query:
                return menu_df
            elif "promotions" in query:
                return promo_df
            return pd.DataFrame()

        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (json.dumps(["SQLite Burger"]), json.dumps(["Pepsi"]), 0.1, 0.8, 2.0)
        ]

        with patch('pandas.read_sql_query', side_effect=read_sql_side_effect):
            with TestClient(app):
                import main
                self.assertEqual(len(main.MENU_ITEMS_DF), 1)
                self.assertEqual(main.MENU_ITEMS_DF.iloc[0]["name"], "SQLite Burger")
                self.assertEqual(main.MENU_PRICE_LOOKUP["SQLite Burger"], 50000.0)
                self.assertEqual(len(main.PROMOTIONS_LIST), 1)
                self.assertEqual(main.PROMOTIONS_LIST[0]["promo_id"], "P1")
                self.assertEqual(len(main.AFFINITY_RULES), 1)
                self.assertEqual(main.AFFINITY_RULES[0]["antecedents"], ["SQLite Burger"])
                self.assertEqual(main.AFFINITY_RULES[0]["consequents"], ["Pepsi"])

    @patch('sqlite3.connect')
    @patch('os.path.exists')
    def test_lifespan_sqlite_loading_fallback(self, mock_exists, mock_connect):
        def side_effect(path):
            if "kiosk.db" in path:
                return True
            if "menu.csv" in path or "promotions.csv" in path or "affinity_rules.json" in path:
                return True
            return False
        mock_exists.side_effect = side_effect

        mock_connect.side_effect = Exception("Connection failed")

        fallback_menu = pd.DataFrame([
            {"name": "CSV Burger", "category": "Burgers", "price": 45000.0}
        ])
        fallback_promo = pd.DataFrame([
            {"promo_id": "P_CSV", "name": "CSV Promo", "discount_pct": 5.0, "start_date": "2026-07-01", "end_date": "2026-07-31"}
        ])
        fallback_rules = [
            {"antecedents": ["CSV Burger"], "consequents": ["Pepsi"], "support": 0.05, "confidence": 0.6, "lift": 1.2}
        ]

        def read_csv_side_effect(path):
            if "menu.csv" in path:
                return fallback_menu
            elif "promotions.csv" in path:
                return fallback_promo
            return pd.DataFrame()

        with patch('pandas.read_csv', side_effect=read_csv_side_effect), \
             patch('builtins.open', mock_open(read_data=json.dumps(fallback_rules))):
            with TestClient(app):
                import main
                self.assertEqual(len(main.MENU_ITEMS_DF), 1)
                self.assertEqual(main.MENU_ITEMS_DF.iloc[0]["name"], "CSV Burger")
                self.assertEqual(main.MENU_PRICE_LOOKUP["CSV Burger"], 45000.0)
                self.assertEqual(len(main.PROMOTIONS_LIST), 1)
                self.assertEqual(main.PROMOTIONS_LIST[0]["promo_id"], "P_CSV")
                self.assertEqual(len(main.AFFINITY_RULES), 1)
                self.assertEqual(main.AFFINITY_RULES[0]["antecedents"], ["CSV Burger"])

if __name__ == "__main__":
    unittest.main()
