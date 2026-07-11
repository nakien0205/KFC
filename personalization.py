"""Pure customer-history ranking and deterministic customer-only offers."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import hashlib
import json
from typing import Any, Dict, Iterable, List, Optional

from promo_engine import DISCOUNT_TIERS, build_discount_view
from recommender import rerank_recommendations


MIN_COMPLETED_ORDERS = 3
DEFAULT_CUSTOMER_BANDIT_WEIGHTS = {
    "alpha_promo": 2.0,
    "beta_promo": 8.0,
    "alpha_time": 1.5,
    "beta_time": 8.5,
}


def _parse_timestamp_date(timestamp: Any) -> Optional[str]:
    if not isinstance(timestamp, str) or not timestamp.strip():
        return None
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date().isoformat()
    except (TypeError, ValueError):
        return None


def _parse_offer_date(offer_date: Any) -> Optional[str]:
    if not isinstance(offer_date, str) or not offer_date.strip():
        return None
    try:
        return datetime.fromisoformat(f"{offer_date.strip()}T00:00:00+00:00").date().isoformat()
    except (TypeError, ValueError):
        return None


def _menu_records(menu_items: Any) -> List[Dict[str, Any]]:
    if isinstance(menu_items, list):
        source = menu_items
    else:
        try:
            source = menu_items.to_dict(orient="records")
        except AttributeError:
            return []
    records: List[Dict[str, Any]] = []
    seen = set()
    for item in source:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        try:
            price = float(item.get("price", 0.0))
        except (TypeError, ValueError):
            price = 0.0
        records.append({"name": name, "category": str(item.get("category") or ""), "price": price})
    return records


def _item_role(item_name: str, category: str) -> str:
    name = str(item_name or "").lower()
    lowered_category = str(category or "").lower()
    if lowered_category == "drinks" or any(word in name for word in ("pepsi", "7up", "lipton")):
        return "drink"
    if lowered_category == "desserts" or any(word in name for word in ("eggtart", "tart", "dessert")):
        return "dessert"
    if lowered_category in ("burgers", "combos") or any(
        word in name for word in ("burger", "combo", "bucket", "rice", "pasta", "chicken", "tender", "fish")
    ):
        return "main"
    return "side"


def _order_item_names(order: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for item in order.get("items", []) if isinstance(order, dict) else []:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            quantity = item.get("quantity", 1)
        else:
            name = str(item or "").strip()
            quantity = 1
        if not name:
            continue
        try:
            count = max(1, int(quantity))
        except (TypeError, ValueError):
            count = 1
        names.extend([name] * count)
    return names


def completed_order_count(customer_orders: Iterable[Dict[str, Any]]) -> int:
    return sum(1 for order in customer_orders if isinstance(order, dict))


def _history_profile(customer_orders: Iterable[Dict[str, Any]], cart_items: Iterable[str]) -> Dict[str, Dict[str, float]]:
    orders = [order for order in customer_orders if isinstance(order, dict)]
    orders.sort(key=lambda order: (str(order.get("completed_at") or ""), int(order.get("id", 0) or 0)))
    item_score: Dict[str, float] = defaultdict(float)
    copurchase_score: Dict[str, float] = defaultdict(float)
    cart_set = {str(item) for item in cart_items if str(item).strip()}
    total_orders = max(1, len(orders))
    for position, order in enumerate(orders):
        recency_weight = 0.5 + ((position + 1) / total_orders)
        item_names = _order_item_names(order)
        unique_names = set(item_names)
        for item_name in item_names:
            item_score[item_name] += recency_weight
        if unique_names & cart_set:
            for item_name in unique_names - cart_set:
                copurchase_score[item_name] += recency_weight

    max_item_score = max(item_score.values(), default=1.0)
    max_copurchase_score = max(copurchase_score.values(), default=1.0)
    return {
        "item": {name: value / max_item_score for name, value in item_score.items()},
        "copurchase": {name: value / max_copurchase_score for name, value in copurchase_score.items()},
    }


def _complement_score(candidate_name: str, candidate_category: str, cart_items: Iterable[str], categories: Dict[str, str]) -> float:
    cart_roles = {_item_role(item, categories.get(item, "")) for item in cart_items}
    candidate_role = _item_role(candidate_name, candidate_category)
    if "main" in cart_roles and candidate_role in {"drink", "side", "dessert"}:
        return 0.16
    if "main" not in cart_roles and candidate_role == "main":
        return 0.12
    if candidate_role not in cart_roles:
        return 0.06
    return 0.0


def _reason_for_candidate(name: str, profile: Dict[str, Dict[str, float]], cold_start: bool) -> str:
    if cold_start:
        return "Cold start: based on general cart pairings until you complete three orders."
    if profile["copurchase"].get(name, 0.0) > 0:
        return "Suggested because you have ordered it with similar items before."
    if profile["item"].get(name, 0.0) > 0:
        return "Suggested from your completed order history."
    return "Suggested as a complement to your current cart and completed order history."


def _canonical_history(customer_orders: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    canonical = []
    for order in customer_orders:
        if not isinstance(order, dict):
            continue
        canonical.append(
            {
                "completed_at": str(order.get("completed_at") or ""),
                "items": sorted(_order_item_names(order)),
            }
        )
    return sorted(canonical, key=lambda order: (order["completed_at"], order["items"]))


def build_personal_offer(
    user_identifier: Any,
    customer_orders: Iterable[Dict[str, Any]],
    cart_items: Iterable[str],
    candidate: Dict[str, Any],
    request_date: str,
) -> Optional[Dict[str, Any]]:
    """Return the stable offer for one customer/candidate/date, or no offer."""
    if not isinstance(candidate, dict) or not candidate.get("name"):
        return None
    if completed_order_count(customer_orders) < MIN_COMPLETED_ORDERS:
        return None
    candidate_name = str(candidate["name"])
    if candidate_name in {str(item) for item in cart_items}:
        return None
    try:
        price = float(candidate.get("price", 0.0))
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None

    payload = {
        "user": str(user_identifier),
        "history": _canonical_history(customer_orders),
        "cart": sorted(str(item) for item in cart_items),
        "candidate": candidate_name,
        "date": request_date,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    tier = DISCOUNT_TIERS[int(digest[:8], 16) % len(DISCOUNT_TIERS)]
    discount = build_discount_view(price, tier)
    return {
        "type": "personal",
        "offer_id": f"personal-{digest[:32]}",
        "target_item": candidate_name,
        "request_date": request_date,
        **discount,
    }


def customer_recommendations(
    user_identifier: Any,
    cart_items: Any,
    timestamp: Any,
    menu_items: Any,
    affinity_rules: Iterable[Dict[str, Any]],
    customer_orders: Iterable[Dict[str, Any]],
    active_promotions: Optional[Iterable[Dict[str, Any]]] = None,
    offer_date: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Rank a cart using general affinity plus completed personal history only.

    Cold-start customers retain the shared global promotion-aware hybrid result.
    Mature customers instead receive one deterministic personal offer.
    """
    if not isinstance(cart_items, list) or not cart_items:
        return []
    normalised_cart = [str(item).strip() for item in cart_items if isinstance(item, str) and item.strip()]
    if not normalised_cart or _parse_timestamp_date(timestamp) is None:
        return []
    cart_set = set(normalised_cart)
    menu_records = _menu_records(menu_items)
    categories = {item["name"]: item["category"] for item in menu_records}
    prices = {item["name"]: item["price"] for item in menu_records}
    order_history = [order for order in customer_orders if isinstance(order, dict)]
    cold_start = completed_order_count(order_history) < MIN_COMPLETED_ORDERS
    global_promotions = list(active_promotions or []) if cold_start else []

    general_candidates = rerank_recommendations(
        cart_items=normalised_cart,
        active_promotions=global_promotions,
        affinity_rules=list(affinity_rules or []),
        menu_items=menu_records,
        timestamp=timestamp,
        bandit_weights=dict(DEFAULT_CUSTOMER_BANDIT_WEIGHTS),
        bandit_mode="expected",
    )
    candidates: Dict[str, Dict[str, Any]] = {}
    for recommendation in general_candidates:
        if not isinstance(recommendation, dict):
            continue
        name = str(recommendation.get("name") or "").strip()
        if not name or name in cart_set or name not in prices:
            continue
        global_promotion = None
        promotion_keys = (
            "promo_id",
            "promotion_name",
            "discount_pct",
            "discount_label",
            "amount_off_vnd",
            "sale_price",
            "urgency",
        )
        if cold_start and any(recommendation.get(key) is not None for key in promotion_keys):
            global_promotion = {
                "type": "global",
                **{key: recommendation[key] for key in promotion_keys if recommendation.get(key) is not None},
            }
            global_promotion["display_text"] = (
                str(global_promotion.get("discount_label") or global_promotion.get("promotion_name") or "Active promotion")
            )
        effective_price = recommendation.get("sale_price", prices[name])
        try:
            effective_price = float(effective_price)
        except (TypeError, ValueError):
            effective_price = float(prices[name])
        candidates[name] = {
            "name": name,
            "price": effective_price,
            "global_score": float(recommendation.get("score", 0.0) or 0.0),
            "promotion": global_promotion,
        }

    # Once history is sufficient, let personal signals surface catalog items the
    # global rules did not happen to emit for this exact cart.
    if not cold_start:
        for item in menu_records:
            if item["name"] not in cart_set:
                candidates.setdefault(
                    item["name"],
                    {"name": item["name"], "price": item["price"], "global_score": 0.0},
                )

    profile = _history_profile(order_history, normalised_cart)
    results: List[Dict[str, Any]] = []
    for candidate in candidates.values():
        name = candidate["name"]
        category = categories.get(name, "")
        personal_score = 0.0
        if not cold_start:
            personal_score = (
                (0.55 * profile["item"].get(name, 0.0))
                + (0.75 * profile["copurchase"].get(name, 0.0))
                + _complement_score(name, category, normalised_cart, categories)
            )
        score = candidate["global_score"] + personal_score
        result = {
            "name": name,
            "price": float(candidate["price"]),
            "score": round(score, 6),
            "personalization_reason": _reason_for_candidate(name, profile, cold_start),
            "cold_start": cold_start,
        }
        if candidate.get("promotion"):
            result["promotion"] = candidate["promotion"]
        results.append(result)

    results.sort(key=lambda item: (-item["score"], item["name"]))
    results = results[: max(0, int(limit))]
    if not results:
        return []

    offer_index = next(
        (
            index
            for index, candidate in enumerate(results)
            if _complement_score(
                candidate["name"], categories.get(candidate["name"], ""), normalised_cart, categories
            ) > 0
        ),
        None,
    )
    offer = None
    if not cold_start and offer_index is not None:
        offer = build_personal_offer(
            user_identifier=user_identifier,
            customer_orders=order_history,
            cart_items=normalised_cart,
            candidate=results[offer_index],
            request_date=_parse_offer_date(offer_date) or _parse_timestamp_date(timestamp) or "",
        )
    if offer and offer_index is not None:
        results[offer_index]["price"] = float(offer["sale_price"])
        # Keep the established recommender/backtest effective-price contract.
        results[offer_index]["sale_price"] = float(offer["sale_price"])
        results[offer_index]["promotion"] = offer
        results[offer_index]["personalization_reason"] = (
            "Personal offer: " + results[offer_index]["personalization_reason"]
        )
    return results
