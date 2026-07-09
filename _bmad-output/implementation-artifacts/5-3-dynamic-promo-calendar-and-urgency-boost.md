---
baseline_commit: b42ddd744bbbb8ef83594ce6a726486a98ccfd0d
---

# Story 5.3: Dynamic Promo Calendar and Urgency Boost

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a growth-focused kiosk operator,
I want the demo to generate controlled daily sale promotions and boost items when those sales are close to ending,
so that recommendations can use realistic promotion psychology without making unsupported production-sales claims.

## Acceptance Criteria

1. **Controlled Daily Promo Generation**
   - `generate_data.py` must generate promotion rows through a deterministic promo engine instead of a fixed static list only.
   - Promo selection must use weighted probability by category and item popularity, not pure random selection.
   - Day strength must be higher near Monday and Sunday and lower mid-week using a Gaussian-style day weighting.
   - Not every day must receive sales.
2. **Discount Tiering and Framing**
   - Generated dynamic sale discounts must be one of `5`, `10`, `15`, or `20` percent.
   - `20%` is the maximum generated dynamic discount.
   - The promo engine must calculate amount-off and sale price from item price.
   - Display framing must support either percent-off or amount-off text, using amount-off when the rounded VND discount is more persuasive for higher-value items.
3. **Promotion Targeting Contract**
   - `promotions.csv` and the SQLite `promotions` table must keep the existing required fields: `promo_id`, `name`, `discount_pct`, `start_date`, `end_date`.
   - Optional dynamic-promo fields may be added for precise targeting, but existing broad legacy promotion rows must still work.
   - Runtime loading from SQLite and CSV fallback must preserve those optional fields.
4. **Urgency-Aware Reranking**
   - `recommender.py` must keep the existing no-cart-duplicates rule.
   - Active targeted promotions must boost only their target item.
   - Existing broad promotion matching by name/category must remain backward compatible.
   - A sale-ending urgency multiplier must apply only when a matching active promotion is close to ending.
   - Empty carts, missing timestamps, and invalid timestamps must still return HTTP 200 with an empty list from `/api/recommend`.
5. **Discount-Aware Copy and Backtest**
   - Local fallback copy must mention the active sale framing when a recommended item is under a dynamic promotion.
   - External LLM copy generation must still make at most one external call per `/api/recommend` event.
   - `backtest.py` must add discounted sale revenue for accepted promoted recommendations instead of original full item price.
   - The benchmark wording must still say the result is synthetic benchmark evidence, not real production sales proof.
6. **Testing and Documentation**
   - Add focused tests for promo generation math, discount tiering, amount-off framing, urgency calculation, reranking effect, and discounted backtest pricing.
   - Update docs to describe the dynamic promo calendar, optional promotion fields, urgency scoring, and discount-aware AOV math.
   - Run `python generate_data.py`, `python affinity_engine.py`, `python init_db.py`, `python backtest.py`, and the full unittest suite.

## Tasks / Subtasks

- [x] **Task 1: Add promo engine math module** (AC: 1, 2)
  - [x] Create `promo_engine.py` in the project root.
  - [x] Implement cyclic Gaussian day strength with Monday/Sunday peaks.
  - [x] Implement deterministic weighted item selection from menu records and order popularity.
  - [x] Implement generated discount tiers limited to `5/10/15/20`.
  - [x] Implement amount-off, sale-price, and display framing helpers.
- [x] **Task 2: Generate and persist dynamic promotions** (AC: 1, 2, 3)
  - [x] Update `generate_data.py` to generate promotion rows from the promo engine after orders are available.
  - [x] Preserve the existing required promotion columns.
  - [x] Add optional fields for targeted dynamic promos without breaking existing CSV consumers.
  - [x] Update `init_db.py` to persist optional promotion fields into SQLite.
  - [x] Update SQLite runtime and backtest loading to select all promotion columns.
- [x] **Task 3: Add urgency-aware recommendation scoring** (AC: 3, 4, 5)
  - [x] Update `is_item_in_promotion` to support targeted promo records and legacy promo names.
  - [x] Add sale-ending urgency scoring only for matching active promotions.
  - [x] Return sale context with ranked candidates while preserving existing API response shape.
  - [x] Update local and LLM copy generation to use promo framing when provided.
- [x] **Task 4: Make backtest discount-aware** (AC: 5)
  - [x] Add accepted dynamic promos at sale price, not original price.
  - [x] Keep the default partial-cart benchmark and conservative full-order check available.
  - [x] Refresh benchmark output and submission wording only after rerun output is known.
- [x] **Task 5: Tests and documentation** (AC: 6)
  - [x] Add/update unit tests for promo engine, recommender, SQLite, backtest, and API behavior.
  - [x] Update `AGENTS.md`, `docs/index.md`, and `hackathon_submission.md`.
  - [x] Run the required data regeneration commands and full unittest suite.

## Dev Notes

- Keep the feature inside the existing pipes-and-filters architecture. `promo_engine.py` should be a pure helper/filter module; `main.py` should remain a delivery layer.
- Do not add customer identity or loyalty-history claims. The hackathon spec does not provide customer identity data, so this story implements store/menu-level adaptive promotion context only.
- Do not change `/api/recommend` response shape unless tests, frontend, and `AGENTS.md` are updated. Prefer embedding sale framing in copy and using sale price in the existing `price` field for promoted recommendations.
- Preserve one-external-call behavior: only the top recommendation can call the LLM; all other cards use local fallback copy.
- Preserve Vietnamese customer-facing copy and dot-separated VND formatting through `format_price_vnd`.
- Backtest claims must stay aligned with rerun output and must remain framed as synthetic benchmark evidence.

### Current Files To Extend

- `promo_engine.py` - new promo generation, discount, and urgency helpers.
- `generate_data.py` - write dynamic promo calendar rows.
- `init_db.py` - store optional promotion fields in SQLite.
- `main.py` - load optional promotion fields and pass sale context into copy generation.
- `recommender.py` - targeted promotion matching, urgency boost, sale context, and fallback copy.
- `backtest.py` - discounted revenue for accepted promoted recommendations.
- `tests/` - promo, recommender, backtest, API, and SQLite coverage.
- `AGENTS.md`, `docs/index.md`, `hackathon_submission.md` - docs and pitch updates.

### References

- [Source: _bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md#Capabilities]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-5-Local-LLM-Integration-and-Dynamic-Contextual-Boosts]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md#AD-1--Pipes--Filters-Architecture]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md#AD-3--GenAI-Response-Latency--Offline-Resilience]
- [Source: _bmad-output/implementation-artifacts/5-2-dynamic-contextual-reranking-via-multi-armed-bandits.md]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Started dev-story implementation from baseline `b42ddd744bbbb8ef83594ce6a726486a98ccfd0d`.

### Completion Notes List

- Implemented a deterministic dynamic promo calendar with Gaussian-style day strength, weighted product selection, 5/10/15/20 percent discount tiers, amount-off framing, sale price calculation, and end-of-day urgency scoring.
- Preserved legacy broad promotion matching while adding targeted promotion support through optional `target_item`, `target_category`, `discount_type`, `amount_off_vnd`, `sale_price`, `display_text`, and `is_dynamic` fields.
- Updated recommendation scoring, copy generation, API response pricing, and backtest revenue math so active targeted promotions use sale context without adding a new API response shape.
- Regenerated demo data and reran the benchmark. Current synthetic benchmark result: Hybrid Recommender AOV `87.822 VND`, baseline AOV `78.294 VND`, uplift `+9.527 VND` / `+12.17%`; conservative full-order top-1 uplift `+1.82%`.
- Review fix: blank/NaN `target_item` values no longer block category-targeted promotion matching.
- Review fix: direct OpenRouter no-key fallback now preserves promotion context so sale copy is still shown.
- Verification completed: `python generate_data.py`, `python affinity_engine.py`, `python init_db.py`, `python backtest.py`, and `python -m unittest discover -s tests -p "test_*.py"` all passed. The final full unit run passed `65` tests.

### File List

- `promo_engine.py`
- `generate_data.py`
- `init_db.py`
- `main.py`
- `recommender.py`
- `backtest.py`
- `_bmad-output/data/menu.csv`
- `_bmad-output/data/orders.csv`
- `_bmad-output/data/promotions.csv`
- `_bmad-output/data/affinity_rules.json`
- `_bmad-output/data/rule_coverage_report.md`
- `_bmad-output/data/kiosk.db`
- `tests/test_promo_engine.py`
- `tests/test_recommender.py`
- `tests/test_backtest.py`
- `tests/test_sqlite.py`
- `tests/test_main.py`
- `AGENTS.md`
- `docs/index.md`
- `hackathon_submission.md`
- `simple_pitch.md`
- `technical_pitch.md`
- `technical_judge_qna.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/5-3-dynamic-promo-calendar-and-urgency-boost.md`

## Change Log

- 2026-07-08: Created story for dynamic promotion generation, urgency scoring, discounted AOV math, and documentation updates.
- 2026-07-08: Started implementation.
- 2026-07-08: Completed implementation, docs, data regeneration, benchmark rerun, and unit verification; moved story to review.
- 2026-07-08: Completed code review, fixed two review findings, and reran focused plus full tests.
