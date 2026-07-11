import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
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

    def test_future_client_timestamp_uses_trusted_server_offer_date(self):
        self._register()
        for _ in range(3):
            self._checkout()

        with patch("main._customer_offer_date", return_value="2026-07-11"), patch(
            "main.generate_recommendation_copy", return_value={"copy": "Test", "rationale": "Test"}
        ):
            response = self.client.post(
                "/api/customer/recommend",
                json={"cart_items": ["Burger Zinger"], "timestamp": "2036-12-31T12:00:00Z"},
            )

        self.assertEqual(response.status_code, 200)
        offer = next(row["promotion"] for row in response.json() if row.get("promotion"))
        self.assertEqual(offer["type"], "personal")
        self.assertEqual(offer["request_date"], "2026-07-11")

    def test_cold_start_preserves_global_promotion_without_personal_offer(self):
        self._register()
        promotion = {
            "promo_id": "COLD_FRIES",
            "name": "French Fries offer",
            "discount_pct": 10,
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
            "target_item": "French Fries",
            "display_text": "Save 10% on French Fries",
            "is_dynamic": 1,
        }
        with patch.object(main, "PROMOTIONS_LIST", [promotion]), patch(
            "main.generate_recommendation_copy", return_value={"copy": "Test", "rationale": "Test"}
        ):
            response = self.client.post(
                "/api/customer/recommend",
                json={"cart_items": ["Burger Zinger"], "timestamp": "2026-07-06T12:00:00Z"},
            )

        self.assertEqual(response.status_code, 200)
        global_row = next(row for row in response.json() if row.get("promotion"))
        self.assertTrue(global_row["cold_start"])
        self.assertEqual(global_row["promotion"]["type"], "global")
        self.assertNotIn("offer_id", global_row["promotion"])
        base_price = float(
            main.MENU_ITEMS_DF.loc[main.MENU_ITEMS_DF["name"] == "French Fries", "price"].iloc[0]
        )
        self.assertLess(global_row["price"], base_price)
        self.assertEqual(
            self.client.get("/api/customer/orders").json()["orders"], [],
        )

    def test_concurrent_offer_change_returns_retryable_response(self):
        self._register()
        for _ in range(3):
            self._checkout()
        with patch.object(
            main._active_customer_store(),
            "issue_personal_offer",
            side_effect=main.CustomerStoreError("Personal offer is no longer available."),
        ), patch("main.generate_recommendation_copy", return_value={"copy": "Test", "rationale": "Test"}):
            response = self.client.post(
                "/api/customer/recommend",
                json={"cart_items": ["Burger Zinger"], "timestamp": "2026-07-06T12:00:00Z"},
            )

        self.assertEqual(response.status_code, 409)
        self.assertIn("refresh recommendations", response.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
