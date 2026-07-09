import unittest
import os
from unittest.mock import patch, MagicMock
from backtest import _recommended_price, run_backtest_simulation

class TestBacktestSimulation(unittest.TestCase):
    def test_run_backtest_simulation(self):
        # Run simulation with standard seed
        results = run_backtest_simulation(seed=42)

        # Verify result contains the expected keys
        self.assertIn("baseline_aov", results)
        self.assertIn("hybrid_aov", results)
        self.assertIn("absolute_change", results)
        self.assertIn("percentage_uplift", results)

        # Verify values are reasonable
        self.assertGreater(results["baseline_aov"], 0)
        self.assertGreater(results["hybrid_aov"], 0)
        self.assertGreater(results["percentage_uplift"], 0)
        self.assertAlmostEqual(
            results["hybrid_aov"] - results["baseline_aov"],
            results["absolute_change"],
            places=1
        )
        self.assertEqual(results["benchmark_mode"], "partial_cart_panel")
        self.assertEqual(results["panel_size"], 3)
        self.assertGreaterEqual(results["percentage_uplift"], 10.0)
        self.assertLessEqual(results["percentage_uplift"], 15.0)
        self.assertIn("conservative_result", results)
        self.assertAlmostEqual(
            results["conservative_result"]["percentage_uplift"],
            1.82,
            places=1
        )

    def test_conservative_backtest_mode_remains_available(self):
        results = run_backtest_simulation(seed=42, mode="conservative")

        self.assertEqual(results["benchmark_mode"], "conservative_full_order")
        self.assertEqual(results["panel_size"], 1)
        self.assertEqual(results["total_simulated"], 5000)
        self.assertGreater(results["percentage_uplift"], 0)
        self.assertAlmostEqual(results["percentage_uplift"], 1.82, places=1)

    def test_recommended_price_uses_sale_price_when_present(self):
        price_lookup = {"Happy Bucket": 249000.0}

        self.assertEqual(
            _recommended_price({"name": "Happy Bucket", "sale_price": 199000.0}, price_lookup),
            199000.0,
        )
        self.assertEqual(
            _recommended_price({"name": "Happy Bucket"}, price_lookup),
            249000.0,
        )

    @patch('backtest.os.path.exists')
    def test_backtest_missing_db_raises_error(self, mock_exists):
        # Simulate kiosk.db missing
        mock_exists.side_effect = lambda path: False if "kiosk.db" in path else True

        from backtest import _load_backtest_inputs
        with self.assertRaises(FileNotFoundError) as context:
            _load_backtest_inputs()
        self.assertIn("SQLite database is missing", str(context.exception))

    @patch('sqlite3.connect')
    @patch('backtest.os.path.exists')
    def test_backtest_stale_db_raises_error(self, mock_exists, mock_connect):
        # Simulate kiosk.db exists
        mock_exists.side_effect = lambda path: True if "kiosk.db" in path else True

        # Simulate sqlite query error
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.side_effect = Exception("OperationalError: no such table: menu")

        from backtest import _load_backtest_inputs
        with self.assertRaises(ValueError) as context:
            _load_backtest_inputs()
        self.assertIn("SQLite database is stale or invalid", str(context.exception))

if __name__ == "__main__":
    unittest.main()
