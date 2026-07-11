"""Generate deterministic repeat-customer histories for personalization evaluation."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import json
import os
import random
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_PERSONA_COUNT = 500
DEFAULT_SEED = 20260711
PROMOTION_CALENDAR_YEAR = 2026


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


def _load_promotion_calendar() -> List[Dict[str, Any]]:
    from backtest import _load_backtest_inputs

    return _load_backtest_inputs()["promotions_list"]


def _parse_calendar_date(value: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        return None


def _controlled_promotion_dates(promotion_calendar: Iterable[Dict[str, Any]]) -> List[date]:
    """Return sorted 2026 dates covered by at least one valid promotion row."""
    start_of_year = date(PROMOTION_CALENDAR_YEAR, 1, 1)
    end_of_year = date(PROMOTION_CALENDAR_YEAR, 12, 31)
    active_dates = set()
    for promotion in promotion_calendar:
        if not isinstance(promotion, dict):
            continue
        start_date = _parse_calendar_date(promotion.get("start_date"))
        end_date = _parse_calendar_date(promotion.get("end_date"))
        if start_date is None or end_date is None or end_date < start_date:
            continue
        cursor = max(start_date, start_of_year)
        last_date = min(end_date, end_of_year)
        while cursor <= last_date:
            active_dates.add(cursor)
            cursor += timedelta(days=1)
    return sorted(active_dates)


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
    promotion_calendar: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Write strict-history personas with hold-outs on active 2026 promotion dates."""
    if persona_count <= 0:
        raise ValueError("persona_count must be positive.")
    resolved_menu_records = list(menu_records) if menu_records is not None else _load_menu_records()
    resolved_calendar = list(promotion_calendar) if promotion_calendar is not None else _load_promotion_calendar()
    controlled_dates = _controlled_promotion_dates(resolved_calendar)
    if not controlled_dates:
        raise ValueError("Customer persona generation requires at least one active 2026 promotion-calendar date.")

    roles = _by_role(resolved_menu_records)
    rng = random.Random(seed)
    personas = []
    for index in range(persona_count):
        favourites = {
            "main": rng.choice(roles["main"]),
            "drink": rng.choice(roles["drink"]),
            "side": rng.choice(roles["side"]),
            "dessert": rng.choice(roles["dessert"]),
        }
        history_count = rng.randint(8, 24)
        holdout_date = rng.choice(controlled_dates)
        holdout_at = datetime.combine(
            holdout_date,
            time(hour=rng.choice((10, 12, 13, 15, 18, 20)), minute=rng.randint(0, 59)),
            tzinfo=timezone.utc,
        )
        gaps = [
            timedelta(days=rng.randint(2, 15), minutes=rng.randint(1, 120))
            for _ in range(history_count + 1)
        ]
        cursor = holdout_at - sum(gaps, timedelta())
        history = []
        for order_index, gap in enumerate(gaps[:-1]):
            cursor += gap
            history.append(
                {
                    "order_id": f"P{index + 1:03d}-H{order_index + 1:02d}",
                    "completed_at": cursor.isoformat(),
                    "items": _order_items(rng, favourites, roles),
                }
            )
        holdout = {
            "order_id": f"P{index + 1:03d}-HOLDOUT",
            "completed_at": holdout_at.isoformat(),
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
