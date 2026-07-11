"""Generate deterministic repeat-customer histories for personalization evaluation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
import random
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_PERSONA_COUNT = 500
DEFAULT_SEED = 20260711


def default_persona_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "_bmad-output",
        "data",
        "customer_personas.json",
    )


def _load_menu_records() -> List[Dict[str, Any]]:
    from backtest import _load_backtest_inputs

    return _load_backtest_inputs()["menu_records"]


def _by_role(menu_records: Iterable[Dict[str, Any]]) -> Dict[str, List[str]]:
    roles = {"main": [], "drink": [], "side": [], "dessert": [], "any": []}
    for row in menu_records:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        roles["any"].append(name)
        category = str(row.get("category") or "").lower()
        lowered_name = name.lower()
        if category == "drinks" or any(token in lowered_name for token in ("pepsi", "7up", "lipton")):
            roles["drink"].append(name)
        elif category == "desserts" or "tart" in lowered_name:
            roles["dessert"].append(name)
        elif category in ("burgers", "combos") or any(
            token in lowered_name for token in ("burger", "combo", "bucket", "rice", "pasta", "chicken", "tender")
        ):
            roles["main"].append(name)
        else:
            roles["side"].append(name)
    if len(set(roles["any"])) < 2:
        raise ValueError("Customer persona generation requires at least two distinct menu items.")
    for role in ("main", "drink", "side", "dessert"):
        if not roles[role]:
            roles[role] = list(roles["any"])
    return roles


def _order_items(rng: random.Random, favourites: Dict[str, str], roles: Dict[str, List[str]]) -> List[str]:
    """Create a small, repeatable basket with realistic favourite-item bias."""
    items = [favourites["main"]]
    if rng.random() < 0.76:
        items.append(favourites["drink"] if rng.random() < 0.82 else rng.choice(roles["drink"]))
    if rng.random() < 0.62:
        items.append(favourites["side"] if rng.random() < 0.74 else rng.choice(roles["side"]))
    if rng.random() < 0.18:
        items.append(favourites["dessert"] if rng.random() < 0.70 else rng.choice(roles["dessert"]))
    # At least two distinct ordered items make a partial-cart replay meaningful.
    if len(set(items)) < 2:
        alternatives = [item for item in roles["any"] if item not in items]
        if alternatives:
            items.append(rng.choice(alternatives))
    return list(dict.fromkeys(items))


def generate_personas(
    output_path: Optional[str] = None,
    persona_count: int = DEFAULT_PERSONA_COUNT,
    seed: int = DEFAULT_SEED,
    menu_records: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Write 500 (by default) strict-history/hold-out persona sequences."""
    if persona_count <= 0:
        raise ValueError("persona_count must be positive.")
    roles = _by_role(list(menu_records) if menu_records is not None else _load_menu_records())
    rng = random.Random(seed)
    base_date = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    personas = []
    for index in range(persona_count):
        favourites = {
            "main": rng.choice(roles["main"]),
            "drink": rng.choice(roles["drink"]),
            "side": rng.choice(roles["side"]),
            "dessert": rng.choice(roles["dessert"]),
        }
        history_count = rng.randint(8, 24)
        cursor = base_date + timedelta(days=rng.randint(0, 90), minutes=rng.randint(0, 600))
        history = []
        for order_index in range(history_count):
            cursor += timedelta(days=rng.randint(2, 15), minutes=rng.randint(1, 120))
            history.append(
                {
                    "order_id": f"P{index + 1:03d}-H{order_index + 1:02d}",
                    "completed_at": cursor.isoformat(),
                    "items": _order_items(rng, favourites, roles),
                }
            )
        cursor += timedelta(days=rng.randint(2, 15), minutes=rng.randint(1, 120))
        holdout = {
            "order_id": f"P{index + 1:03d}-HOLDOUT",
            "completed_at": cursor.isoformat(),
            "items": _order_items(rng, favourites, roles),
        }
        personas.append(
            {
                "persona_id": f"persona-{index + 1:03d}",
                "history": history,
                "holdout": holdout,
            }
        )

    artifact = {
        "seed": seed,
        "persona_count": persona_count,
        "generated_at": "deterministic",
        "personas": personas,
    }
    destination = os.path.abspath(output_path or default_persona_path())
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "w", encoding="utf-8") as handle:
        json.dump(artifact, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return artifact


if __name__ == "__main__":
    artifact = generate_personas()
    print(
        f"Generated {artifact['persona_count']} deterministic customer personas at {default_persona_path()}"
    )
