import json
import os
import tempfile
import unittest
from pathlib import Path

from generate_customer_personas import generate_personas
from personalization_backtest import _accepted_value, run_personalization_backtest


MENU = [
    {"name": "Burger Zinger", "category": "Burgers", "price": 85000},
    {"name": "French Fries", "category": "Sides", "price": 30000},
    {"name": "Pepsi", "category": "Drinks", "price": 19000},
    {"name": "1 Eggtart", "category": "Desserts", "price": 20000},
]
INPUTS = {
    "menu_records": MENU,
    "menu_price_lookup": {row["name"]: row["price"] for row in MENU},
    "menu_category_lookup": {row["name"]: row["category"] for row in MENU},
    "affinity_rules": [
        {"antecedents": ["Burger Zinger"], "consequents": ["French Fries"], "support": 0.2, "confidence": 0.8, "lift": 1.5}
    ],
    "promotions_list": [],
}


class TestCustomerPersonaEvidence(unittest.TestCase):
    def test_personas_are_deterministic_and_holdout_is_later(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first_path = os.path.join(temp_dir, "first.json")
            second_path = os.path.join(temp_dir, "second.json")
            first = generate_personas(first_path, persona_count=5, seed=7, menu_records=MENU)
            generate_personas(second_path, persona_count=5, seed=7, menu_records=MENU)
            self.assertEqual(Path(first_path).read_text(encoding="utf-8"), Path(second_path).read_text(encoding="utf-8"))
            self.assertEqual(first["persona_count"], 5)
            for persona in first["personas"]:
                self.assertGreaterEqual(len(persona["history"]), 8)
                self.assertLessEqual(len(persona["history"]), 24)
                self.assertGreater(persona["holdout"]["completed_at"], persona["history"][-1]["completed_at"])
                for order in persona["history"] + [persona["holdout"]]:
                    self.assertEqual(len(order["items"]), len(set(order["items"])))

    def test_replay_is_deterministic_and_reports_synthetic_metrics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            persona_path = os.path.join(temp_dir, "personas.json")
            generate_personas(persona_path, persona_count=12, seed=11, menu_records=MENU)
            first = run_personalization_backtest(persona_path=persona_path, inputs=INPUTS)
            second = run_personalization_backtest(persona_path=persona_path, inputs=INPUTS)
            self.assertEqual(first, second)
            self.assertFalse(first["holdout_used_as_history"])
            self.assertEqual(first["eligible_customer_count"], 12)
            self.assertIn("general_hybrid_aov", first)
            self.assertIn("personalized_aov", first)
            self.assertEqual(first["panel_size"], 3)
            self.assertIn("fixture_sha256", first)
            self.assertEqual(
                run_personalization_backtest(persona_path=persona_path, inputs=INPUTS, panel_size=2)["panel_size"],
                2,
            )
            with self.assertRaises(ValueError):
                run_personalization_backtest(persona_path=persona_path, inputs=INPUTS, panel_size=0)
            self.assertEqual(
                _accepted_value(
                    [{"name": "Pepsi", "sale_price": 15000}], ["Pepsi"], {"Pepsi": 19000}
                ),
                15000.0,
            )


if __name__ == "__main__":
    unittest.main()
