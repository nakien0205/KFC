import os
import json
import random
import threading

# Default path for weights
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_PATH = os.path.join(BASE_DIR, "_bmad-output", "data", "bandit_weights.json")

# Default priors: yields mean boosts of 0.20 for promo and 0.15 for time
DEFAULT_WEIGHTS = {
    "alpha_promo": 2.0,
    "beta_promo": 8.0,
    "alpha_time": 1.5,
    "beta_time": 8.5
}

# Reentrant lock to prevent concurrent read-modify-write race conditions safely
_lock = threading.RLock()

def load_bandit_weights(path=None):
    """Load bandit weights from a JSON file, or initialize with defaults if not found."""
    if path is None:
        path = WEIGHTS_PATH
        
    with _lock:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    weights = json.load(f)
                    if not isinstance(weights, dict):
                        weights = {}
                    # Verify all keys exist, fallback if missing
                    for k, v in DEFAULT_WEIGHTS.items():
                        if k not in weights:
                            weights[k] = v
                    return weights
            except Exception:
                pass
        return dict(DEFAULT_WEIGHTS)

def save_bandit_weights(weights, path=None):
    """Save bandit weights to a JSON file atomically."""
    if path is None:
        path = WEIGHTS_PATH
        
    with _lock:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        temp_path = path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(weights, f, indent=2)
            os.replace(temp_path, path)
        except Exception:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
            raise

def update_bandit_weights(accepted: bool, promo_active: bool, time_active: bool, path=None):
    """Update bandit weights based on acceptance outcome and active context."""
    if path is None:
        path = WEIGHTS_PATH
        
    with _lock:
        weights = load_bandit_weights(path)
        reward = 1.0 if accepted else 0.0
        
        if promo_active:
            if reward > 0.5:
                weights["alpha_promo"] += 1.0
            else:
                weights["beta_promo"] += 1.0
                
        if time_active:
            if reward > 0.5:
                weights["alpha_time"] += 1.0
            else:
                weights["beta_time"] += 1.0
                
        save_bandit_weights(weights, path)
        return weights

def get_bandit_boosts(weights, mode="expected"):
    """
    Get dynamic boost values based on current bandit parameters.
    mode: "expected" (mean of beta distribution) or "sample" (Thompson Sampling draw)
    """
    if not isinstance(weights, dict):
        weights = DEFAULT_WEIGHTS
        
    # Enforce positive inputs (> 0) to betavariate to prevent ValueErrors
    alpha_promo = max(1e-5, weights.get("alpha_promo", DEFAULT_WEIGHTS["alpha_promo"]))
    beta_promo = max(1e-5, weights.get("beta_promo", DEFAULT_WEIGHTS["beta_promo"]))
    alpha_time = max(1e-5, weights.get("alpha_time", DEFAULT_WEIGHTS["alpha_time"]))
    beta_time = max(1e-5, weights.get("beta_time", DEFAULT_WEIGHTS["beta_time"]))
    
    if mode == "sample":
        promo_boost = random.betavariate(alpha_promo, beta_promo)
        time_boost = random.betavariate(alpha_time, beta_time)
    else:  # expected
        promo_boost = alpha_promo / (alpha_promo + beta_promo)
        time_boost = alpha_time / (alpha_time + beta_time)
        
    return promo_boost, time_boost
