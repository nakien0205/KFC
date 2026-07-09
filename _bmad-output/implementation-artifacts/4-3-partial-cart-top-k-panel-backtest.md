---
baseline_commit: b42ddd744bbbb8ef83594ce6a726486a98ccfd0d
---

# Story 4.3: Partial-Cart Top-K Panel Backtest

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a business analyst,
I want the backtest harness to simulate recommendations while the kiosk cart is still being built,
so that the hackathon benchmark measures the recommendation panel flow shown in the UI instead of only a final-basket upsell.

## Acceptance Criteria

1. **Partial-Cart Replay**: Given `orders.csv`, `menu.csv`, `promotions.csv`, and `affinity_rules.json`, the default `run_backtest_simulation(seed=42)` path must split each eligible order into one anchor cart item plus held-out add-ons. Orders with fewer than 2 unique items must be skipped for this benchmark.
2. **Static Baseline**: The baseline remains a static one-item Pepsi upsell strategy. Pepsi may only be counted as accepted when it is present in the held-out items and absent from the anchor cart.
3. **Top-K Hybrid Panel**: The hybrid model must evaluate the top 3 context-reranked recommendations from `rerank_recommendations`, matching the UI's multi-card recommendation panel behavior.
4. **Held-Out Acceptance Rule**: A hybrid recommendation may only add AOV when the recommended item appears in the held-out items from the original synthetic order. Do not count arbitrary sampled recommendations as accepted.
5. **Target Band Evidence**: With the current generated data and fixed seed `42`, the default benchmark must return `percentage_uplift` between 10.0 and 15.0.
6. **Conservative Secondary Evidence**: The old full-order, top-1 Monte Carlo benchmark must remain available as a callable mode or nested secondary result so pitch wording can still disclose the conservative result.
7. **No Production Claim**: Updated pitch/submission wording must say the 10-15% result is a synthetic partial-cart panel benchmark, not real production sales proof.

## Tasks / Subtasks

- [x] **Task 1: Add partial-cart benchmark mode in `backtest.py`** (AC: 1, 2, 3, 4, 5, 6)
  - [x] Preserve the existing full-order top-1 benchmark behavior as a conservative mode.
  - [x] Make the default fixed-seed path use the partial-cart top-3 panel benchmark.
  - [x] Keep bandit simulation isolated in a temporary weights file; do not write production `bandit_weights.json`.
- [x] **Task 2: Update tests for both benchmark modes** (AC: 1, 5, 6)
  - [x] Add tests proving the default result lands in the 10% to 15% band.
  - [x] Add tests proving the conservative mode remains callable and positive.
  - [x] Keep tests deterministic and free of real network calls.
- [x] **Task 3: Update benchmark wording artifacts** (AC: 7)
  - [x] Update `hackathon_submission.md`.
  - [x] Update `simple_pitch.md`.
  - [x] Update `technical_pitch.md`.
  - [x] Update `technical_judge_qna.md`.
- [x] **Task 4: Run full verification** (AC: 1-7)
  - [x] Run `python backtest.py`.
  - [x] Run `python -m unittest discover -s tests -p "test_*.py"`.

### Review Findings

- [x] [Review][Patch] In-app backtest wording still used generic full-order labels [static/app.js:461] — updated the modal and metric labels to say synthetic partial-cart panel benchmark and eligible cart.

## Dev Notes

- This story is a benchmark correction, not a data-generation rewrite. Do not change `generate_data.py`, `affinity_engine.py`, or the generated CSV/JSON data unless tests prove the benchmark cannot work with the current artifacts.
- The current full-order benchmark calls `rerank_recommendations(cart_items=original_items, ...)`, which means the recommender sees the complete synthetic basket and must recommend something outside it. That is valid as a conservative stress test, but it does not match the kiosk flow where recommendations update while the cart is being built.
- Use a simple deterministic anchor rule for partial-cart replay: de-duplicate each original order preserving order, choose the first main-like item when possible, otherwise choose the first item. Held-out items are all remaining unique items.
- Keep the current static baseline narrow and explicit: one Pepsi suggestion. Do not compare the hybrid top-3 panel against a top-k popularity baseline for the main claim because that is a different benchmark. If mentioned in prose, describe it as a stronger future baseline, not the current target metric.
- The quick evidence gathered before story creation showed the current data can support the target band under partial-cart top-k replay:
  - top-3 hybrid panel vs static Pepsi baseline: about `+11.23%`
  - top-4 hybrid panel vs static Pepsi baseline: about `+14.57%`
  Use top-3 to stay inside the requested 10% to 15% band without making the panel unrealistically broad.
- Keep the old conservative result visible as secondary evidence: current fixed-seed full-order top-1 output was `+3.00%` over `5,000` transactions.
- `main.py` currently calls `run_backtest_simulation(seed=DEMO_BACKTEST_SEED)` and exposes only the existing top-level AOV fields plus optional `final_weights`. Avoid breaking this API shape unless you also update `tests/test_main.py` and the static frontend.
- Customer-facing copy and benchmark prose must stay conservative: say "synthetic scenario benchmark" and "not real production sales proof."

### Project Structure Notes

- Backend benchmark logic lives in root `backtest.py`.
- API driver logic lives in root `main.py`; do not move replay loops into `main.py`.
- Tests live under `tests/` and use `unittest`.
- Runtime data remains under `_bmad-output/data/`.
- Static frontend has no build step.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.3]
- [Source: _bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md#Capabilities]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md#AD-5]
- [Source: _bmad-output/implementation-artifacts/4-1-backtest-replay-logic-and-math-module.md]
- [Source: _bmad-output/implementation-artifacts/4-2-fastapi-integration-for-api-backtest.md]
- [Source: AGENTS.md#Implementation-Rules]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `python -m unittest tests.test_backtest` red phase failed before implementation with missing `mode` and `benchmark_mode`.
- `python -m unittest tests.test_backtest` passed after implementation.
- `python backtest.py` passed and reported partial-cart panel uplift `+11.23%` plus conservative full-order uplift `+3.00%`.
- `python -m unittest discover -s tests -p "test_*.py"` passed after implementation: `Ran 47 tests in 114.286s OK`.
- `python backtest.py` passed after review patch and still reported partial-cart panel uplift `+11.23%` plus conservative full-order uplift `+3.00%`.
- `python -m unittest discover -s tests -p "test_*.py"` passed after review patch: `Ran 52 tests in 110.511s OK`.

### Completion Notes List

- Added default partial-cart top-3 panel benchmark mode in `backtest.py`.
- Preserved the old full-order top-1 Monte Carlo benchmark as `mode="conservative"`.
- Added deterministic tests for the 10% to 15% headline band and the conservative secondary result.
- Updated pitch and judge-facing wording to describe the new result as a synthetic partial-cart panel benchmark, not production sales proof.
- Addressed code-review wording finding by updating the in-app backtest modal labels for the new benchmark semantics.

### File List

- `backtest.py`
- `tests/test_backtest.py`
- `hackathon_submission.md`
- `simple_pitch.md`
- `technical_pitch.md`
- `technical_judge_qna.md`
- `static/index.html`
- `static/app.js`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/4-3-partial-cart-top-k-panel-backtest.md`

## Change Log

- 2026-07-08: Added Story 4.3, implemented partial-cart top-3 panel benchmark, preserved conservative benchmark mode, updated tests and pitch wording.
- 2026-07-08: Addressed code-review wording finding and marked story done.
