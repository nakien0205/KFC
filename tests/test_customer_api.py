import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


class TestCustomerAPI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_patcher = patch.dict(
            os.environ,
            {"CUSTOMER_DB_PATH": os.path.join(self.temp_dir.name, "customer.db")},
        )
        self.env_patcher.start()
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.env_patcher.stop()
        self.temp_dir.cleanup()

    def _register(self, email="first@example.test"):
        response = self.client.post(
            "/api/customer/register", json={"email": email, "password": "long-secret"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("password", response.text.lower())
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=lax", cookie)
        return response

    def _checkout(self):
        response = self.client.post(
            "/api/customer/checkout",
            json={"cart_items": [{"name": "Burger Zinger", "quantity": 1, "price": 1}]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.json()["order"]["total_vnd"], 1)
        return response

    def test_pages_registration_auth_and_customer_isolation(self):
        self.assertEqual(self.client.get("/customer").status_code, 200)
        self.assertEqual(self.client.get("/customer/login").status_code, 200)
        self.assertEqual(self.client.get("/customer/app", follow_redirects=False).status_code, 303)
        self._register()
        self.assertEqual(self.client.get("/customer/app").status_code, 200)
        self._checkout()
        self.assertEqual(len(self.client.get("/api/customer/orders").json()["orders"]), 1)

        self.client.post("/api/customer/logout")
        self.assertEqual(self.client.get("/api/customer/orders").status_code, 401)
        self._register("second@example.test")
        self.assertEqual(self.client.get("/api/customer/orders").json()["orders"], [])

    def test_checkout_and_recommendation_edge_contracts(self):
        self._register()
        invalid_checkout = self.client.post(
            "/api/customer/checkout", json={"cart_items": [{"name": "Burger Zinger", "quantity": 0}]}
        )
        self.assertEqual(invalid_checkout.status_code, 422)
        excessive_checkout = self.client.post(
            "/api/customer/checkout", json={"cart_items": [{"name": "Burger Zinger", "quantity": 100}]}
        )
        self.assertEqual(excessive_checkout.status_code, 422)
        self.assertEqual(
            self.client.post("/api/customer/recommend", json={"cart_items": [], "timestamp": "2026-07-06T12:00:00Z"}).json(),
            [],
        )
        self.assertEqual(
            self.client.post("/api/customer/recommend", json={"cart_items": ["Burger Zinger"], "timestamp": "bad-time"}).json(),
            [],
        )

        for _ in range(3):
            self._checkout()
        with patch("main.generate_recommendation_copy", return_value={"copy": "Local test", "rationale": "History test"}) as mock_copy:
            response = self.client.post(
                "/api/customer/recommend",
                json={"cart_items": ["Burger Zinger"], "timestamp": "2026-07-06T12:00:00Z"},
            )
        self.assertEqual(response.status_code, 200)
        recommendations = response.json()
        self.assertTrue(recommendations)
        self.assertEqual(mock_copy.call_count, 1)
        self.assertTrue(all(row["name"] != "Burger Zinger" for row in recommendations))
        offer_row = next(row for row in recommendations if row.get("promotion"))
        offer = offer_row["promotion"]
        self.assertIn(offer["discount_pct"], [5, 10, 15, 20])
        redemption = self.client.post(
            "/api/customer/checkout",
            json={
                "cart_items": [{"name": offer["target_item"], "quantity": 1}],
                "offer_id": offer["offer_id"],
            },
        )
        self.assertEqual(redemption.status_code, 200)
        saved_order = redemption.json()["order"]
        self.assertEqual(saved_order["applied_offer_id"], offer["offer_id"])
        self.assertEqual(saved_order["total_vnd"], offer["sale_price"])
        self.assertEqual(
            self.client.post(
                "/api/customer/checkout",
                json={
                    "cart_items": [{"name": offer["target_item"], "quantity": 1}],
                    "offer_id": offer["offer_id"],
                },
            ).status_code,
            400,
        )


if __name__ == "__main__":
    unittest.main()
