import unittest
import os
from backtest import run_backtest_simulation

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

if __name__ == "__main__":
    unittest.main()
