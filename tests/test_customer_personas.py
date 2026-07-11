import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from generate_customer_personas import generate_personas
from personalization_backtest import _accepted_value, _active_promotion_count, run_personalization_backtest


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
    "promotions_list": [
        {
            "promo_id": "DYN_20260706_BURGERS",
            "name": "Burger Daily Sale - Burger Zinger",
            "discount_pct": 10,
            "start_date": "2026-07-06",
            "end_date": "2026-07-06",
            "target_item": "Burger Zinger",
            "target_category": "Burgers",
            "sale_price": 76000,
        }
    ],
}


class TestCustomerPersonaEvidence(unittest.TestCase):
    def test_personas_are_deterministic_and_holdout_is_on_active_2026_calendar_date(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first_path = os.path.join(temp_dir, "first.json")
            second_path = os.path.join(temp_dir, "second.json")
            first = generate_personas(
                first_path,
                persona_count=5,
                seed=7,
                menu_records=MENU,
                promotion_calendar=INPUTS["promotions_list"],
            )
            generate_personas(
                second_path,
                persona_count=5,
                seed=7,
                menu_records=MENU,
                promotion_calendar=INPUTS["promotions_list"],
            )
            self.assertEqual(Path(first_path).read_text(encoding="utf-8"), Path(second_path).read_text(encoding="utf-8"))
            self.assertEqual(first["persona_count"], 5)
            for persona in first["personas"]:
                self.assertGreaterEqual(len(persona["history"]), 8)
                self.assertLessEqual(len(persona["history"]), 24)
                holdout_time = datetime.fromisoformat(persona["holdout"]["completed_at"])
                self.assertEqual(holdout_time.year, 2026)
                self.assertEqual(holdout_time.date().isoformat(), "2026-07-06")
                self.assertTrue(all(
                    datetime.fromisoformat(order["completed_at"]) < holdout_time
                    for order in persona["history"]
                ))
                for order in persona["history"] + [persona["holdout"]]:
                    self.assertEqual(len(order["items"]), len(set(order["items"])))
            with self.assertRaises(ValueError):
                generate_personas(
                    os.path.join(temp_dir, "invalid.json"),
                    persona_count=1,
                    seed=7,
                    menu_records=MENU,
                    promotion_calendar=[],
                )

    def test_replay_is_deterministic_and_reports_synthetic_metrics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            persona_path = os.path.join(temp_dir, "personas.json")
            generate_personas(
                persona_path,
                persona_count=12,
                seed=11,
                menu_records=MENU,
                promotion_calendar=INPUTS["promotions_list"],
            )
            first = run_personalization_backtest(persona_path=persona_path, inputs=INPUTS)
            second = run_personalization_backtest(persona_path=persona_path, inputs=INPUTS)
            self.assertEqual(first, second)
            self.assertFalse(first["holdout_used_as_history"])
            self.assertEqual(first["eligible_customer_count"], 12)
            self.assertEqual(first["active_promotion_persona_count"], 12)
            self.assertEqual(first["active_promotion_coverage"], 1.0)
            self.assertEqual(first["evidence_type"], "synthetic scenario evidence")
            self.assertIn("general_hybrid_aov", first)
            self.assertIn("personalized_aov", first)
            self.assertEqual(first["panel_size"], 3)
            self.assertIn("fixture_sha256", first)
            panel_one = run_personalization_backtest(persona_path=persona_path, inputs=INPUTS, panel_size=1)
            panel_five = run_personalization_backtest(persona_path=persona_path, inputs=INPUTS, panel_size=5)
            self.assertEqual(panel_one["panel_size"], 1)
            self.assertIn("top-1", panel_one["benchmark"])
            self.assertEqual(panel_five["panel_size"], 5)
            self.assertIn("top-5", panel_five["benchmark"])
            self.assertEqual(
                run_personalization_backtest(
                    persona_path=persona_path,
                    inputs={**INPUTS, "promotions_list": None},
                )["active_promotion_coverage"],
                0.0,
            )
            for invalid_panel_size in (0, True, "3", 6):
                with self.subTest(panel_size=invalid_panel_size), self.assertRaises(ValueError):
                    run_personalization_backtest(
                        persona_path=persona_path,
                        inputs=INPUTS,
                        panel_size=invalid_panel_size,
                    )
            self.assertEqual(
                _accepted_value(
                    [{"name": "Pepsi", "sale_price": 15000}], ["Pepsi"], {"Pepsi": 19000}
                ),
                15000.0,
            )
            self.assertEqual(_accepted_value([{"name": "Pepsi"}], ["Pepsi"], {"Pepsi": 19000}), 19000.0)

    def test_replay_skips_malformed_timestamp_and_respects_promotion_daypart(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            persona_path = os.path.join(temp_dir, "personas.json")
            generate_personas(
                persona_path,
                persona_count=1,
                seed=19,
                menu_records=MENU,
                promotion_calendar=INPUTS["promotions_list"],
            )
            artifact = json.loads(Path(persona_path).read_text(encoding="utf-8"))
            artifact["personas"][0]["holdout"]["completed_at"] = "not-a-timestamp"
            Path(persona_path).write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            replay = run_personalization_backtest(persona_path=persona_path, inputs=INPUTS)
            self.assertEqual(replay["eligible_customer_count"], 0)
            self.assertEqual(replay["skipped_customer_count"], 1)
            self.assertEqual(replay["active_promotion_coverage"], 0.0)

        lunch_promotion = {**INPUTS["promotions_list"][0], "name": "Lunch Daily Sale"}
        self.assertEqual(_active_promotion_count([lunch_promotion], "2026-07-06T10:00:00Z"), 0)
        self.assertEqual(_active_promotion_count([lunch_promotion], "2026-07-06T12:00:00Z"), 1)

    def test_replay_uses_holdout_timestamp_without_history_leakage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            persona_path = os.path.join(temp_dir, "personas.json")
            generate_personas(
                persona_path,
                persona_count=1,
                seed=17,
                menu_records=MENU,
                promotion_calendar=INPUTS["promotions_list"],
            )
            artifact = json.loads(Path(persona_path).read_text(encoding="utf-8"))
            persona = artifact["personas"][0]
            expected_timestamp = persona["holdout"]["completed_at"]
            expected_history_items = [order["items"] for order in persona["history"]]
            general_timestamps = []
            personalized_timestamps = []
            personalized_history = []

            def capture_general(**kwargs):
                general_timestamps.append(kwargs["timestamp"])
                return [{"name": "French Fries", "score": 1.0}]

            def capture_personalized(**kwargs):
                personalized_timestamps.append(kwargs["timestamp"])
                personalized_history.append(kwargs["customer_orders"])
                return [{"name": "French Fries", "score": 1.0}]

            with patch("personalization_backtest.rerank_recommendations", side_effect=capture_general), patch(
                "personalization_backtest.customer_recommendations", side_effect=capture_personalized
            ):
                run_personalization_backtest(persona_path=persona_path, inputs=INPUTS)

            self.assertEqual(general_timestamps, [expected_timestamp])
            self.assertEqual(personalized_timestamps, [expected_timestamp])
            self.assertEqual(
                [[item["name"] for item in order["items"]] for order in personalized_history[0]],
                expected_history_items,
            )


if __name__ == "__main__":
    unittest.main()
