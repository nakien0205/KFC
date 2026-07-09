import unittest
from datetime import datetime, date

import pandas as pd

from promo_engine import (
    DISCOUNT_TIERS,
    build_discount_view,
    calculate_promotion_urgency,
    day_sale_strength,
    generate_daily_promotions,
    promotion_targets_item,
    sale_probability_for_date,
)


class TestPromoEngine(unittest.TestCase):
    def test_day_strength_peaks_on_monday_and_sunday(self):
        monday = day_sale_strength(date(2026, 7, 6))
        sunday = day_sale_strength(date(2026, 7, 12))
        wednesday = day_sale_strength(date(2026, 7, 8))

        self.assertGreater(monday, wednesday)
        self.assertGreater(sunday, wednesday)
        self.assertGreater(sale_probability_for_date(date(2026, 7, 6)), sale_probability_for_date(date(2026, 7, 8)))

    def test_discount_view_rounds_amount_off_for_large_items(self):
        view = build_discount_view(249000, 20)

        self.assertEqual(view["discount_pct"], 20)
        self.assertEqual(view["amount_off_vnd"], 50000)
        self.assertEqual(view["sale_price"], 199000)
        self.assertEqual(view["discount_type"], "amount")
        self.assertEqual(view["display_text"], "Save 50.000 VND")

    def test_generated_discounts_use_allowed_tiers_and_max_20(self):
        menu = pd.DataFrame([
            {"name": "Burger Zinger", "category": "Burgers", "price": 56000},
            {"name": "Combo Group 2", "category": "Combos", "price": 169000},
            {"name": "2 Fried Chicken", "category": "Sides", "price": 74000},
        ])
        orders = pd.DataFrame([
            {"order_id": "T1", "item_name": "Burger Zinger"},
            {"order_id": "T2", "item_name": "Burger Zinger"},
            {"order_id": "T3", "item_name": "Combo Group 2"},
            {"order_id": "T4", "item_name": "2 Fried Chicken"},
        ])

        promos = generate_daily_promotions(menu, orders, date(2026, 7, 6), seed=42)

        self.assertGreater(len(promos), 0)
        for promo in promos:
            self.assertIn(int(promo["discount_pct"]), DISCOUNT_TIERS)
            self.assertLessEqual(int(promo["discount_pct"]), 20)
            self.assertIn("target_item", promo)
            self.assertIn("sale_price", promo)
            self.assertIn("display_text", promo)

    def test_promotion_urgency_increases_near_end_of_day(self):
        promo = {
            "start_date": "2026-07-06",
            "end_date": "2026-07-06",
        }

        midday = calculate_promotion_urgency(promo, datetime.fromisoformat("2026-07-06T12:00:00+07:00"))
        evening = calculate_promotion_urgency(promo, datetime.fromisoformat("2026-07-06T21:00:00+07:00"))

        self.assertLess(midday, evening)
        self.assertGreater(evening, 0)

    def test_category_target_ignores_blank_target_item(self):
        promo = {
            "target_item": float("nan"),
            "target_category": "Burgers",
        }

        self.assertTrue(promotion_targets_item(promo, "Burger Zinger", "Burgers"))
        self.assertFalse(promotion_targets_item(promo, "Pepsi", "Drinks"))


if __name__ == "__main__":
    unittest.main()
