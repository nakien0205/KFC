import hashlib
import math
import random
from datetime import date, datetime, time, timedelta


DISCOUNT_TIERS = (5, 10, 15, 20)
PROMO_GROUPS = ("burgers", "chickens", "combos")
DEFAULT_MIN_SALE_PROBABILITY = 0.15
DEFAULT_MAX_SALE_PROBABILITY = 0.70
URGENCY_WINDOW_HOURS = 8
URGENCY_BOOST_CAP = 0.10


def _safe_lower(value):
    return str(value or "").strip().lower()


def _optional_text(value):
    if value is None:
        return ""
    try:
        if value != value:
            return ""
    except Exception:
        pass
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _normalize_records(rows):
    if rows is None:
        return []
    if isinstance(rows, list):
        source = rows
    else:
        try:
            source = rows.to_dict(orient="records")
        except AttributeError:
            return []

    records = []
    for row in source:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "") or "").strip()
        if not name:
            continue
        try:
            price = float(row.get("price", 0.0) or 0.0)
        except (TypeError, ValueError):
            price = 0.0
        records.append({
            "name": name,
            "category": str(row.get("category", "") or ""),
            "price": price,
        })
    return records


def _build_popularity_lookup(orders):
    if orders is None:
        return {}

    try:
        records = orders.to_dict(orient="records")
    except AttributeError:
        records = orders if isinstance(orders, list) else []

    order_items = {}
    raw_counts = {}
    for row in records:
        if not isinstance(row, dict):
            continue
        item_name = str(row.get("item_name", "") or "").strip()
        if not item_name:
            continue
        order_id = str(row.get("order_id", "") or "").strip()
        raw_counts[item_name] = raw_counts.get(item_name, 0) + 1
        if order_id:
            order_items.setdefault(order_id, set()).add(item_name)

    if order_items:
        counts = {}
        for items in order_items.values():
            for item in items:
                counts[item] = counts.get(item, 0) + 1
        denominator = max(1, len(order_items))
        return {item: count / denominator for item, count in counts.items()}

    total = sum(raw_counts.values())
    if total <= 0:
        return {}
    return {item: count / total for item, count in raw_counts.items()}


def cyclic_day_distance(day_index, center_index):
    distance = abs(int(day_index) - int(center_index))
    return min(distance, 7 - distance)


def day_sale_strength(target_date, sigma=1.0):
    parsed = _as_date(target_date)
    if parsed is None:
        return 0.0

    day_index = parsed.weekday()
    monday_peak = math.exp(-(cyclic_day_distance(day_index, 0) ** 2) / (2 * sigma ** 2))
    sunday_peak = math.exp(-(cyclic_day_distance(day_index, 6) ** 2) / (2 * sigma ** 2))
    return max(0.0, min(1.0, 0.5 * monday_peak + 0.5 * sunday_peak))


def sale_probability_for_date(target_date, min_probability=DEFAULT_MIN_SALE_PROBABILITY, max_probability=DEFAULT_MAX_SALE_PROBABILITY):
    strength = day_sale_strength(target_date)
    return min_probability + (max_probability - min_probability) * strength


def discount_tier_for_date(target_date, rng=None):
    if rng is None:
        rng = random.Random()
    strength = day_sale_strength(target_date)
    raw_discount = 5 + (15 * strength) + rng.gauss(0, 1.5)
    tier = int(round(raw_discount / 5.0) * 5)
    return max(min(tier, max(DISCOUNT_TIERS)), min(DISCOUNT_TIERS))


def format_price_vnd_text(price):
    try:
        value = int(round(float(price)))
    except (TypeError, ValueError):
        return str(price)
    return f"{value:,}".replace(",", ".") + "đ"


def build_discount_view(price, discount_pct):
    try:
        normalized_pct = int(round(float(discount_pct) / 5.0) * 5)
    except (TypeError, ValueError):
        normalized_pct = 5
    normalized_pct = max(min(normalized_pct, max(DISCOUNT_TIERS)), min(DISCOUNT_TIERS))

    try:
        numeric_price = float(price)
    except (TypeError, ValueError):
        numeric_price = 0.0

    raw_amount = numeric_price * normalized_pct / 100.0
    amount_off = int(round(raw_amount / 1000.0) * 1000)
    if normalized_pct > 0 and numeric_price > 0 and amount_off <= 0:
        amount_off = 1000
    sale_price = max(0, int(round(numeric_price - amount_off)))

    if amount_off >= 20000:
        discount_type = "amount"
        display_text = f"Giảm {format_price_vnd_text(amount_off)}"
    else:
        discount_type = "percent"
        display_text = f"Giảm {normalized_pct}%"

    return {
        "discount_pct": normalized_pct,
        "amount_off_vnd": amount_off,
        "sale_price": sale_price,
        "discount_type": discount_type,
        "display_text": display_text,
    }


def _promo_group_for_item(item_name, item_category):
    name = _safe_lower(item_name)
    category = _safe_lower(item_category)

    if category == "burgers" or "burger" in name:
        return "burgers"
    if category == "combos" or "combo" in name or "bucket" in name:
        return "combos"
    if "chicken" in name or "tender" in name:
        return "chickens"
    return ""


def _seed_for_day(seed, target_date):
    digest = hashlib.sha256(f"{seed}:{target_date.isoformat()}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _weighted_choice(candidates, popularity, rng):
    if not candidates:
        return None

    weights = []
    for row in candidates:
        base_popularity = popularity.get(row["name"], 0.01)
        exploration = rng.uniform(0.8, 1.2)
        weights.append(max(0.001, base_popularity * exploration))

    total = sum(weights)
    pick = rng.random() * total
    cumulative = 0.0
    for row, weight in zip(candidates, weights):
        cumulative += weight
        if pick <= cumulative:
            return row
    return candidates[-1]


def generate_daily_promotions(menu_items, orders=None, target_date=None, seed=42, groups=PROMO_GROUPS):
    parsed_date = _as_date(target_date) or date.today()
    rng = random.Random(_seed_for_day(seed, parsed_date))
    records = _normalize_records(menu_items)
    popularity = _build_popularity_lookup(orders)
    sale_probability = sale_probability_for_date(parsed_date)
    promos = []

    for group in groups:
        if rng.random() > sale_probability:
            continue

        candidates = [
            row for row in records
            if _promo_group_for_item(row["name"], row["category"]) == group
        ]
        selected = _weighted_choice(candidates, popularity, rng)
        if not selected:
            continue

        discount_pct = discount_tier_for_date(parsed_date, rng)
        discount_view = build_discount_view(selected["price"], discount_pct)
        group_label = {
            "burgers": "Burger",
            "chickens": "Chicken",
            "combos": "Combo",
        }.get(group, "Menu")
        promo_id = f"DYN_{parsed_date.strftime('%Y%m%d')}_{group.upper()}"
        promos.append({
            "promo_id": promo_id,
            "name": f"{group_label} Daily Sale - {selected['name']}",
            "discount_pct": discount_view["discount_pct"],
            "start_date": parsed_date.isoformat(),
            "end_date": parsed_date.isoformat(),
            "target_item": selected["name"],
            "target_category": selected["category"],
            "discount_type": discount_view["discount_type"],
            "amount_off_vnd": discount_view["amount_off_vnd"],
            "sale_price": discount_view["sale_price"],
            "display_text": discount_view["display_text"],
            "is_dynamic": 1,
        })

    return promos


def generate_promo_calendar(menu_items, orders=None, start_date=None, days=14, seed=42):
    parsed_start = _as_date(start_date) or date.today()
    promos = []
    for offset in range(days):
        promos.extend(
            generate_daily_promotions(
                menu_items=menu_items,
                orders=orders,
                target_date=parsed_start + timedelta(days=offset),
                seed=seed,
            )
        )
    return promos


def calculate_promotion_urgency(promo, timestamp_dt, window_hours=URGENCY_WINDOW_HOURS):
    if not isinstance(promo, dict) or not isinstance(timestamp_dt, datetime):
        return 0.0

    end_date = _as_date(promo.get("end_date"))
    if end_date is None:
        return 0.0

    end_dt = datetime.combine(end_date, time(23, 59, 59))
    if timestamp_dt.tzinfo is not None:
        end_dt = end_dt.replace(tzinfo=timestamp_dt.tzinfo)

    seconds_left = (end_dt - timestamp_dt).total_seconds()
    if seconds_left <= 0:
        return 1.0

    window_seconds = max(1.0, float(window_hours) * 3600)
    return max(0.0, min(1.0, 1.0 - (seconds_left / window_seconds)))


def promotion_targets_item(promo, item_name, item_category):
    if not isinstance(promo, dict):
        return False

    target_item = _optional_text(promo.get("target_item"))
    if target_item:
        return target_item == str(item_name or "").strip()

    target_category = _safe_lower(promo.get("target_category"))
    if target_category:
        return target_category == _safe_lower(item_category)

    return False
