import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
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

    def test_recommend_endpoint_success(self):
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
            # Ensure price is a float and correct
            self.assertEqual(item["name"], "French Fries")
            self.assertEqual(item["price"], 20000.0)

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

if __name__ == "__main__":
    unittest.main()
