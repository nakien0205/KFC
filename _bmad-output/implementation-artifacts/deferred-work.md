# Deferred Work

This file tracks technical debt and deferred items from development and reviews.

## Deferred from: code review of 2-2-genai-copy-generation-and-fallback-engine.md (2026-07-06)

- Brittle promotion matching via hardcoded substring checks (pepsi, 7up, lipton, fries, eggtart) instead of metadata flags in recommender.py.
- Generic promotions without matched keywords ignored completely.
- Time boosts limited to lunch/dinner; no breakfast or late-night support.
- Confidence fallback to support metric mathematically incorrect and skews scores.
- menu lookup builder crashes if menu DataFrame lacks 'name' or 'category' columns.
- function crashes with AttributeError if menu_items is neither list nor DataFrame.
- candidate deduplication ignores cumulative rule affinity by only keeping highest score.
- return value lacks item metadata (price, category) requiring extra lookups.
- active_promotions list contains non-dict elements (e.g., None, string).
- timestamp is passed as datetime object instead of string.
- menu item has category set to None in source data.
- item_name, item_category, or promo_name is a non-string object in is_item_in_promotion.
- Test suite lacks edge case coverage (negative values, malformed dates, missing columns).

## Deferred from: code review of 2-3-fastapi-server-and-api-recommend-endpoint.md (2026-07-06)

- Loop uses pandas iterrows (main.py:36)
- No API request size limit (main.py:57)

## Deferred from: code review of story-3.1 (2026-07-06)

- Frontend HTML contains no interactive JS file (static/index.html:185)
- Unit test check live API if GEMINI_API_KEY set (test_main.py:862)
- Weak assertions in TestMainAPI (test_main.py:845)
- Lifespan ignores critical data load failures (main.py:35)
- Sync requests block FastAPI thread (main.py:123)
- Optional request fields hide bugs (main.py:108)
- Dangerous price fallback to 0.0 (main.py:137)
- Global cache read/write thread safety issues (main.py:20)
- Flawed chicken matching substring checks (recommender.py:7)

## Deferred from: code review of story-3.2 (2026-07-06)

- Pydantic field name "copy" shadows BaseModel attribute (main.py:118)
- Sync requests block FastAPI thread in recommender (main.py:123)
- Menu card fixed height may clip long item names (static/style.css:196)

## Deferred from: code review of 5-2-dynamic-contextual-reranking-via-multi-armed-bandits.md (2026-07-07)

- Sync HTTP request blocks FastAPI event loop (recommender.py:180-210)
- OLLAMA_HOST environment variable blank or invalid (recommender.py:150-160)

## Deferred from: code review of 1-2-store-orders-and-affinity-rules-in-sqlite.md (2026-07-08)

- SQLite PRAGMA foreign_keys is enabled but no foreign keys are defined in the schema (init_db.py:165)
- Orders table composite primary key (order_id, item_name) constrains items to be unique per order (init_db.py:206)

