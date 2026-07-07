import unittest
import os
import tempfile
import json
from bandit import (
    load_bandit_weights,
    save_bandit_weights,
    update_bandit_weights,
    get_bandit_boosts,
    DEFAULT_WEIGHTS
)

class TestBandit(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for testing serialization
        self.test_dir = tempfile.TemporaryDirectory()
        self.weights_path = os.path.join(self.test_dir.name, "test_bandit_weights.json")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_default_priors(self):
        # Load weights from non-existent path
        weights = load_bandit_weights(self.weights_path)
        self.assertEqual(weights["alpha_promo"], DEFAULT_WEIGHTS["alpha_promo"])
        self.assertEqual(weights["beta_promo"], DEFAULT_WEIGHTS["beta_promo"])
        self.assertEqual(weights["alpha_time"], DEFAULT_WEIGHTS["alpha_time"])
        self.assertEqual(weights["beta_time"], DEFAULT_WEIGHTS["beta_time"])

        # Check expected boosts at default priors
        promo_boost, time_boost = get_bandit_boosts(weights, mode="expected")
        self.assertAlmostEqual(promo_boost, 0.20)
        self.assertAlmostEqual(time_boost, 0.15)

    def test_save_and_load(self):
        custom_weights = {
            "alpha_promo": 5.0,
            "beta_promo": 10.0,
            "alpha_time": 4.0,
            "beta_time": 6.0
        }
        save_bandit_weights(custom_weights, self.weights_path)
        
        # Verify file exists and has correct content
        self.assertTrue(os.path.exists(self.weights_path))
        loaded = load_bandit_weights(self.weights_path)
        self.assertEqual(loaded["alpha_promo"], 5.0)
        self.assertEqual(loaded["alpha_time"], 4.0)

    def test_update_shifts_priors_correctly(self):
        # Initial: alpha=2, beta=8 (mean = 0.2)
        weights = load_bandit_weights(self.weights_path)
        
        # Success (accepted=True) when promo is active
        updated = update_bandit_weights(
            accepted=True,
            promo_active=True,
            time_active=False,
            path=self.weights_path
        )
        # Expect alpha_promo to increase by 1
        self.assertEqual(updated["alpha_promo"], DEFAULT_WEIGHTS["alpha_promo"] + 1)
        self.assertEqual(updated["beta_promo"], DEFAULT_WEIGHTS["beta_promo"])
        
        # Expect mean boost to increase (shift right)
        promo_boost, _ = get_bandit_boosts(updated, mode="expected")
        self.assertGreater(promo_boost, 0.20)

        # Failure (accepted=False) when promo is active
        updated2 = update_bandit_weights(
            accepted=False,
            promo_active=True,
            time_active=False,
            path=self.weights_path
        )
        # Expect beta_promo to increase by 1
        self.assertEqual(updated2["alpha_promo"], DEFAULT_WEIGHTS["alpha_promo"] + 1)
        self.assertEqual(updated2["beta_promo"], DEFAULT_WEIGHTS["beta_promo"] + 1)
        
        # Failure (accepted=False) when time is active
        updated3 = update_bandit_weights(
            accepted=False,
            promo_active=False,
            time_active=True,
            path=self.weights_path
        )
        self.assertEqual(updated3["beta_time"], DEFAULT_WEIGHTS["beta_time"] + 1)
        
        # Expect mean boost for time to decrease (shift left)
        _, time_boost = get_bandit_boosts(updated3, mode="expected")
        self.assertLess(time_boost, 0.15)

    def test_sampling_mode(self):
        weights = load_bandit_weights(self.weights_path)
        promo_boost, time_boost = get_bandit_boosts(weights, mode="sample")
        
        # Since it's a sample from beta, it should be a float in [0, 1]
        self.assertTrue(0.0 <= promo_boost <= 1.0)
        self.assertTrue(0.0 <= time_boost <= 1.0)

if __name__ == "__main__":
    unittest.main()
