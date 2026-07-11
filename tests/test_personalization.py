import unittest

from personalization import DISCOUNT_TIERS, build_personal_offer, customer_recommendations


MENU = [
    {"name": "Burger Zinger", "category": "Burgers", "price": 85000},
    {"name": "French Fries", "category": "Sides", "price": 30000},
    {"name": "Pepsi", "category": "Drinks", "price": 19000},
    {"name": "1 Eggtart", "category": "Desserts", "price": 20000},
]
RULES = [
    {"antecedents": ["Burger Zinger"], "consequents": ["French Fries"], "support": 0.2, "confidence": 0.8, "lift": 1.5},
    {"antecedents": ["Burger Zinger"], "consequents": ["Pepsi"], "support": 0.2, "confidence": 0.7, "lift": 1.3},
]
GLOBAL_PROMOTIONS = [
    {
        "promo_id": "COLD_FRIES",
        "name": "French Fries offer",
        "discount_pct": 10,
        "start_date": "2026-07-01",
        "end_date": "2026-07-31",
        "target_item": "French Fries",
        "display_text": "Save 10% on French Fries",
        "is_dynamic": 1,
    }
]
HISTORY = [
    {"id": 1, "completed_at": "2026-01-01T12:00:00+00:00", "items": [{"name": "Burger Zinger"}, {"name": "French Fries"}]},
    {"id": 2, "completed_at": "2026-01-08T12:00:00+00:00", "items": [{"name": "Burger Zinger"}, {"name": "Pepsi"}]},
    {"id": 3, "completed_at": "2026-01-15T12:00:00+00:00", "items": [{"name": "Burger Zinger"}, {"name": "French Fries"}]},
]


class TestCustomerPersonalization(unittest.TestCase):
    def test_cold_start_and_invalid_input_remain_safe(self):
        cold = customer_recommendations(
            "customer-1", ["Burger Zinger"], "2026-07-06T12:00:00Z", MENU, RULES, HISTORY[:2]
        )
        self.assertTrue(cold)
        self.assertTrue(all(row["cold_start"] for row in cold))
        self.assertTrue(all("promotion" not in row for row in cold))
        self.assertTrue(all(row["name"] != "Burger Zinger" for row in cold))
        self.assertEqual(customer_recommendations("customer-1", ["Burger Zinger"], "bad-time", MENU, RULES, HISTORY), [])

    def test_history_offer_is_tiered_cart_safe_and_deterministic(self):
        results = customer_recommendations(
            "customer-1", ["Burger Zinger"], "2026-07-06T12:00:00Z", MENU, RULES, HISTORY
        )
        self.assertTrue(results)
        offer_row = next(row for row in results if row.get("promotion"))
        offer = offer_row["promotion"]
        self.assertNotEqual(offer["target_item"], "Burger Zinger")
        self.assertIn(offer["discount_pct"], DISCOUNT_TIERS)
        self.assertLessEqual(offer["discount_pct"], 20)
        self.assertTrue(offer["offer_id"].startswith("personal-"))
        self.assertEqual(offer_row["price"], offer["sale_price"])
        self.assertEqual(
            build_personal_offer("customer-1", HISTORY, ["Burger Zinger"], offer_row, "2026-07-06"),
            build_personal_offer("customer-1", HISTORY, ["Burger Zinger"], offer_row, "2026-07-06"),
        )

    def test_cold_start_uses_global_promotion_metadata_without_personal_offer(self):
        results = customer_recommendations(
            "customer-1",
            ["Burger Zinger"],
            "2026-07-06T12:00:00Z",
            MENU,
            RULES,
            HISTORY[:2],
            active_promotions=GLOBAL_PROMOTIONS,
        )

        promoted = next(row for row in results if row.get("promotion"))
        self.assertTrue(promoted["cold_start"])
        self.assertEqual(promoted["promotion"]["type"], "global")
        self.assertNotIn("offer_id", promoted["promotion"])
        self.assertEqual(promoted["price"], promoted["promotion"]["sale_price"])


if __name__ == "__main__":
    unittest.main()
