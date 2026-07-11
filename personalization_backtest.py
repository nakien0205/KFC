"""Replay held-out synthetic customer orders against general and personal ranking."""

from __future__ import annotations

import json
import hashlib
import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from backtest import DEFAULT_BANDIT_WEIGHTS, _recommended_price, _select_anchor_cart
from personalization import customer_recommendations
from recommender import rerank_recommendations


DEFAULT_PANEL_SIZE = 3
MAX_PANEL_SIZE = 5


def default_report_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "_bmad-output",
        "data",
        "personalization_backtest.json",
    )


def _load_personas(persona_path: str) -> Dict[str, Any]:
    with open(persona_path, "r", encoding="utf-8") as handle:
        artifact = json.load(handle)
    if not isinstance(artifact, dict) or not isinstance(artifact.get("personas"), list):
        raise ValueError("Persona artifact must contain a personas list.")
    return artifact


def _load_inputs() -> Dict[str, Any]:
    from backtest import _load_backtest_inputs

    return _load_backtest_inputs()


def _history_for_personalization(history: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Adapt history only. The hold-out order is deliberately not accepted here."""
    converted = []
    for index, order in enumerate(history):
        if not isinstance(order, dict):
            continue
        converted.append(
            {
                "id": index + 1,
                "completed_at": order.get("completed_at", ""),
                "items": [{"name": name, "quantity": 1} for name in order.get("items", [])],
            }
        )
    return converted


def _accepted_value(recommendations: Iterable[Dict[str, Any]], held_out_items: Iterable[str], prices: Dict[str, float]) -> float:
    held_out = set(held_out_items)
    accepted = set()
    value = 0.0
    for recommendation in recommendations:
        name = recommendation.get("name") if isinstance(recommendation, dict) else None
        if name in held_out and name not in accepted:
            value += _recommended_price(recommendation, prices)
            accepted.add(name)
    return value


def _parse_replay_timestamp(timestamp: Any) -> Optional[datetime]:
    if not isinstance(timestamp, str) or not timestamp.strip():
        return None
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _active_promotion_count(promotions: Optional[Iterable[Dict[str, Any]]], timestamp: Any) -> int:
    """Count valid calendar promotions active on a replay timestamp's UTC date."""
    timestamp_dt = _parse_replay_timestamp(timestamp)
    if timestamp_dt is None:
        return 0
    timestamp_date = timestamp_dt.date()
    time_minutes = timestamp_dt.hour * 60 + timestamp_dt.minute
    is_lunch = 11 * 60 <= time_minutes <= 14 * 60
    is_dinner = 17 * 60 <= time_minutes <= 21 * 60

    active_count = 0
    for promotion in promotions or []:
        if not isinstance(promotion, dict):
            continue
        try:
            start_date = datetime.strptime(str(promotion.get("start_date", "")), "%Y-%m-%d").date()
            end_date = datetime.strptime(str(promotion.get("end_date", "")), "%Y-%m-%d").date()
        except (TypeError, ValueError):
            continue
        if start_date <= timestamp_date <= end_date:
            promotion_name = str(promotion.get("name") or "").lower()
            if "lunch" in promotion_name and not is_lunch:
                continue
            if "dinner" in promotion_name and not is_dinner:
                continue
            active_count += 1
    return active_count


def _metrics(
    general_totals: List[float],
    personalized_totals: List[float],
    eligible_count: int,
    skipped_count: int,
    panel_size: int,
) -> Dict[str, Any]:
    if not general_totals:
        return {
            "general_hybrid_aov": 0.0,
            "personalized_aov": 0.0,
            "absolute_change": 0.0,
            "percentage_uplift": 0.0,
            "eligible_customer_count": 0,
            "skipped_customer_count": skipped_count,
            "panel_size": panel_size,
        }
    general_aov = sum(general_totals) / len(general_totals)
    personalized_aov = sum(personalized_totals) / len(personalized_totals)
    absolute_change = personalized_aov - general_aov
    uplift = (absolute_change / general_aov * 100) if general_aov else 0.0
    return {
        "general_hybrid_aov": round(general_aov, 2),
        "personalized_aov": round(personalized_aov, 2),
        "absolute_change": round(absolute_change, 2),
        "percentage_uplift": round(uplift, 2),
        "eligible_customer_count": eligible_count,
        "skipped_customer_count": skipped_count,
        "panel_size": panel_size,
    }


def run_personalization_backtest(
    persona_path: Optional[str] = None,
    output_path: Optional[str] = None,
    inputs: Optional[Dict[str, Any]] = None,
    panel_size: int = DEFAULT_PANEL_SIZE,
) -> Dict[str, Any]:
    """Compare current general hybrid results with customer-history results.

    This is a synthetic replay only. The hold-out basket provides the acceptance
    targets but is never sent to the personalized history profile.
    """
    if not isinstance(panel_size, int) or isinstance(panel_size, bool) or not 1 <= panel_size <= MAX_PANEL_SIZE:
        raise ValueError(f"panel_size must be an integer from 1 through {MAX_PANEL_SIZE}.")
    artifact_path = os.path.abspath(persona_path or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "_bmad-output", "data", "customer_personas.json"
    ))
    artifact = _load_personas(artifact_path)
    with open(artifact_path, "rb") as handle:
        fixture_sha256 = hashlib.sha256(handle.read()).hexdigest()
    runtime_inputs = inputs or _load_inputs()
    menu_records = runtime_inputs["menu_records"]
    prices = runtime_inputs["menu_price_lookup"]
    categories = runtime_inputs["menu_category_lookup"]
    affinity_rules = runtime_inputs["affinity_rules"]
    promotions = runtime_inputs.get("promotions_list") or []
    general_totals: List[float] = []
    personalized_totals: List[float] = []
    skipped = 0
    active_promotion_persona_count = 0

    for index, persona in enumerate(artifact["personas"]):
        if not isinstance(persona, dict):
            skipped += 1
            continue
        holdout = persona.get("holdout")
        history = persona.get("history")
        if not isinstance(holdout, dict) or not isinstance(history, list):
            skipped += 1
            continue
        holdout_items = list(dict.fromkeys(holdout.get("items", [])))
        cart = _select_anchor_cart(holdout_items, categories)
        held_out_items = [item for item in holdout_items if item not in set(cart)]
        if not cart or not held_out_items:
            skipped += 1
            continue
        timestamp = str(holdout.get("completed_at") or "")
        if _parse_replay_timestamp(timestamp) is None:
            skipped += 1
            continue
        has_active_promotion = _active_promotion_count(promotions, timestamp) > 0
        anchor_value = sum(float(prices.get(item, 0.0)) for item in cart)
        general = rerank_recommendations(
            cart_items=cart,
            active_promotions=promotions,
            affinity_rules=affinity_rules,
            menu_items=menu_records,
            timestamp=timestamp,
            bandit_weights=dict(DEFAULT_BANDIT_WEIGHTS),
            bandit_mode="expected",
        )[:panel_size]
        personalized = customer_recommendations(
            user_identifier=persona.get("persona_id", index),
            cart_items=cart,
            timestamp=timestamp,
            menu_items=menu_records,
            affinity_rules=affinity_rules,
            customer_orders=_history_for_personalization(history),
            limit=panel_size,
        )
        general_totals.append(anchor_value + _accepted_value(general, held_out_items, prices))
        personalized_totals.append(anchor_value + _accepted_value(personalized, held_out_items, prices))
        if has_active_promotion:
            active_promotion_persona_count += 1

    result = _metrics(general_totals, personalized_totals, len(general_totals), skipped, panel_size)
    active_promotion_coverage = (
        round(active_promotion_persona_count / len(general_totals), 4) if general_totals else 0.0
    )
    result.update(
        {
            "benchmark": f"synthetic scenario evidence: held-out repeat-customer top-{panel_size} replay",
            "evidence_type": "synthetic scenario evidence",
            "real_customer_sales_proof": False,
            "persona_seed": artifact.get("seed"),
            "fixture_sha256": fixture_sha256,
            "holdout_used_as_history": False,
            "timestamp_policy": "Each held-out order's completed_at timestamp",
            "general_promotion_treatment": "Current global promotion calendar",
            "active_promotion_persona_count": active_promotion_persona_count,
            "active_promotion_coverage": active_promotion_coverage,
            "personalized_promotion_treatment": "One server-validated personal offer replaces global daily promotions",
            "bandit_weights": dict(DEFAULT_BANDIT_WEIGHTS),
        }
    )
    if output_path is not None:
        destination = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
    return result


if __name__ == "__main__":
    report = run_personalization_backtest(output_path=default_report_path())
    print("Synthetic customer personalization replay")
    print(f"Eligible customers: {report['eligible_customer_count']}")
    print(f"General hybrid AOV: {report['general_hybrid_aov']:.2f} VND")
    print(f"Personalized AOV: {report['personalized_aov']:.2f} VND")
    print(f"Absolute change: {report['absolute_change']:.2f} VND")
    print(f"Percentage uplift: {report['percentage_uplift']:.2f}%")
