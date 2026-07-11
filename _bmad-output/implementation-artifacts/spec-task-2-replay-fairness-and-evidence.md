---
title: 'Task 2 Replay Fairness and Evidence'
type: 'bugfix'
created: '2026-07-11'
status: 'done'
review_loop_iteration: 0
baseline_commit: '29e7a0c3204f25efb9fb752eced9b4f62cb10f31'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/guide.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-customer-personalization.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-task-1-customer-offer-ui-correctness.md'
  - '{project-root}/_bmad-output/planning-artifacts/epics-customer-personalization-2026-07-11.md'
---

<frozen-after-approval reason="human-owned Task 2 intent — do not modify unless the user renegotiates scope">

## Intent

**Problem:** The current deterministic persona fixture puts every hold-out in 2025, while the generated global promotion calendar is for July 2026. The personalization replay therefore labels its general-hybrid comparison as promotion-aware without ever exercising an active promotion. It also accepts panel sizes that the general reranker cannot produce.

**Approach:** Generate deterministic hold-outs on controlled dates with at least one active 2026 calendar promotion, keep all 8–24 completed history orders strictly before each hold-out, and make the replay prove its timestamp, no-leakage, panel-size, promotion-coverage, and effective-price contracts. Refresh only the generated persona fixture and replay report after tests pass.

## Boundaries & Constraints

**Always:** Keep kiosk routes, `/api/recommend`, the global generator/miner/database/backtest algorithms, and customer offer rules unchanged. Use the hold-out's `completed_at` timestamp for both general and personalized ranking. Do not add the hold-out to customer history. Keep both strategy panels in the inclusive range 1–5 and calculate accepted values through the existing `_recommended_price` sale-price contract. Keep tests offline and deterministic. Preserve the user-owned `.gitignore`, `README.md`, and customer-personalization review ledger.

**Ask First:** Change any kiosk API or promotion contract, change the generated global-data schema, alter the global kiosk benchmark rules, change tracked-fixture policy, or touch user-owned files.

**Never:** Present the replay as real customer-sales proof; modify `backtest.py` benchmark semantics; put the generated persona history into `orders.csv`, `kiosk.db`, or `customer.db`; accept a panel size above five; or regenerate the fixture/report before the focused generator and replay tests pass.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected behavior | Error handling |
|---|---|---|---|
| Deterministic fixture | Same seed, menu, and promotion dates | Byte-identical JSON; each persona has 8–24 histories and one hold-out | Invalid/empty promotion-date source fails clearly rather than silently falling back to 2025 |
| Promotion-calendar hold-out | A generated 2026 calendar date with one or more promotions | Every hold-out is timestamped on one of those dates; histories are strictly earlier | Dates outside the calendar are rejected/not selected |
| Replay history boundary | Distinct history and hold-out baskets | Only converted history reaches `customer_recommendations`; hold-out is acceptance evidence only | Malformed persona rows are skipped and counted as before |
| Timestamp and coverage | Valid hold-out timestamp plus promotion calendar | Both strategies receive that timestamp; report records a nonzero active-calendar coverage count/rate | Invalid/missing timestamp skips the persona without inventing coverage |
| Panel size | Integer from 1 through 5 | General and personalized paths receive/evaluate the same panel limit | 0, booleans, non-integers, and values above 5 raise `ValueError` |
| Effective accepted price | Recommended held-out item has `sale_price` | Accepted AOV uses the sale price deterministically | Missing/invalid sale price falls back to menu price through existing helper |

</frozen-after-approval>

## Code Map

- `generate_customer_personas.py` -- deterministic persona fixture source; currently creates 2025 dates and must select controlled 2026 promotion-calendar dates.
- `personalization_backtest.py` -- held-out replay; owns input validation, history adaptation, strategy calls, accepted-value math, report metadata, and report serialization.
- `promo_engine.py` and generated `_bmad-output/data/promotions.csv` -- existing deterministic calendar and its `start_date`/`end_date` records. Reuse; do not invent a separate promotion engine.
- `backtest.py` -- shared SQLite input loader, anchor-cart selector, and `_recommended_price` effective-sale-price helper. Reuse its existing contracts; do not alter kiosk benchmark behavior.
- `personalization.py` -- mature-customer replay accepts a timestamp and uses only supplied completed order history. Do not change ranking/offer logic for this task.
- `tests/test_customer_personas.py` -- focused offline fixture/replay contract coverage.

## Tasks / Subtasks

- [x] Task 1: Add focused failing replay-fairness tests (AC: 1, 2, 3, 4)
  - [x] Extend `tests/test_customer_personas.py` with a byte-determinism assertion using an explicit controlled 2026 active-promotion date source.
  - [x] Prove every generated history timestamp is strictly earlier than its hold-out, every history count is 8–24, and every hold-out date is an active date in the supplied 2026 calendar.
  - [x] Prove the replay passes each hold-out timestamp to both ranking strategies and never passes the hold-out order/items into the personalized history argument.
  - [x] Prove report promotion-calendar coverage is nonzero for a fixture made from active dates, panel sizes 1 and 5 work, and 0, booleans, non-integers, and values above 5 are rejected.
  - [x] Preserve/add deterministic effective-sale-price assertions for accepted held-out recommendations with and without a valid `sale_price`.

- [x] Task 2: Generate promotion-calendar-aligned personas (AC: 1)
  - [x] Reuse the existing 2026 promotion calendar source (through the established backtest/generated-data inputs or an explicit injectable date collection); do not hard-code a disconnected calendar.
  - [x] Select only normalized dates that have at least one active promotion and are in 2026. Keep the selection and time-of-day deterministic for the same seed.
  - [x] Build each 8–24-order history strictly before the selected hold-out timestamp. Preserve deterministic IDs, unique basket items, output path behavior, stable sorted/indented JSON, and the default 500-persona fixture.
  - [x] Raise a clear `ValueError` when no usable controlled 2026 promotion date exists instead of producing untested/non-promoted evidence.

- [x] Task 3: Make the replay comparison fair and auditable (AC: 2, 3, 4)
  - [x] Validate `panel_size` as an integer in the inclusive range 1–5 before loading/replaying data; keep both strategy panels at exactly the requested limit.
  - [x] Continue deriving the replay timestamp only from `holdout.completed_at`; pass that exact value to `rerank_recommendations` and `customer_recommendations`.
  - [x] Keep `_history_for_personalization(history)` as the sole customer-history input and retain `holdout_used_as_history: false`; do not mutate fixture data or append the hold-out.
  - [x] Calculate/report the number and rate of eligible replays whose hold-out timestamp has at least one active global calendar promotion. A valid regenerated fixture must produce nonzero coverage.
  - [x] Keep `_accepted_value` delegated to `backtest._recommended_price`, so both global promotion sale prices and personal-offer sale prices use the same stable effective-price calculation.
  - [x] Label the output explicitly as **synthetic scenario evidence**, and retain the clear limitation that it is not real customer-sales proof.

- [x] Task 4: Validate, regenerate, and record reproducible evidence (AC: 1, 2, 3, 4, 5)
  - [x] Run focused customer-persona/replay tests before writing generated evidence.
  - [x] Run the required data chain in this exact order: `python generate_data.py`, `python affinity_engine.py`, `python init_db.py`, `python backtest.py`, `python generate_customer_personas.py`, `python personalization_backtest.py`.
  - [x] Run `python -m unittest discover -s tests -p "test_*.py"` after regeneration. Confirm no kiosk benchmark regression and no production customer database writes.
- [x] Update only the generated `_bmad-output/data/customer_personas.json` and `_bmad-output/data/personalization_backtest.json` evidence artifacts produced by the approved commands. Record their fixture hash, synthetic-evidence wording, hold-out timestamp policy, valid panel size, and nonzero promotion-calendar coverage.

### Review Findings

- [x] [Review][Patch] Skip nonempty malformed hold-out timestamps [personalization_backtest.py:171] — an unparsable timestamp currently reaches both ranking paths, adds anchor-only totals, and dilutes AOV/coverage instead of being skipped.
- [x] [Review][Patch] Treat a null promotion list as empty [personalization_backtest.py:150] — injected or malformed replay inputs with `promotions_list: null` currently raise during coverage counting.
- [x] [Review][Patch] Describe the actual evaluated panel size [personalization_backtest.py:206] — saved panel-1 or panel-5 reports still claim “top-three,” which misstates synthetic evidence outside the default run.
- [x] [Review][Patch] Count only daypart-active calendar promotions [personalization_backtest.py:68] — promotions labelled Lunch or Dinner must follow the same timestamp-hour eligibility used by the general reranker before coverage is reported.

## Acceptance Criteria

1. Given the same seed, menu records, and controlled active 2026 promotion dates, when persona generation runs twice, then the two fixture files are byte-identical; each persona has 8–24 history orders strictly before its hold-out and every hold-out falls on an active 2026 promotion-calendar date.
2. Given a valid fixture, when the replay runs, then it uses each hold-out `completed_at` value as the timestamp for both general and personalized strategies, never puts the hold-out into customer history, and reports nonzero active-promotion calendar coverage for the regenerated fixture.
3. Given a requested panel size, when the replay starts, then only integer panel sizes 1 through 5 are accepted and both strategies evaluate the same limit; all other values, including values above five, fail with `ValueError`.
4. Given a held-out item accepted from either strategy, when it has a valid `sale_price`, then replay AOV uses that effective sale price deterministically; otherwise it uses the menu price through the existing shared helper.
5. Given focused tests pass, when the required data chain and full suite run, then the regenerated persona fixture and replay report are reproducible and explicitly described as synthetic scenario evidence rather than real customer-sales proof, while kiosk benchmark behavior remains unchanged.

## Dev Notes

### Implementation Guardrails

- The existing generated calendar starts at `2026-07-01` for 14 days and may contain promotions only on some dates. Choose from the actual dates represented by calendar rows, not the whole date range.
- Prefer an optional injectable promotion-date/calendar argument in `generate_personas` for small offline tests, while the default path loads the established generated promotion records. Preserve the public default CLI path.
- Parse calendar date fields defensively: a date is eligible when at least one valid promotion has a range containing it; the current generated rows are daily promotions, but the implementation should not rely on `start_date == end_date`.
- Preserve chronological order in each generated `history` list. Generate backwards from the controlled hold-out then reverse, or use another deterministic method that proves every history precedes it.
- The general reranker itself filters the supplied promotion list by its timestamp. Coverage reporting must independently test the same date-range condition so the report describes evidence, not the number of raw rows loaded.
- Mature `customer_recommendations` intentionally replaces global daily promotions with a personal offer. Fairness here means the same hold-out timestamp/context reaches both strategies, not that both use the same promotion type.
- Do not change `DEFAULT_PROMO_DATE`, global `backtest.py` panel behavior, `generate_data.py` generation logic, or customer API/UI code in this task.
- Existing `sale_price` is the effective-price contract. Do not add a second price field or duplicate price calculation.

### Test Design

- Use temporary persona/report paths and injected menu/input records. Do not require the tracked two-million-byte fixture for unit tests.
- Use a small deterministic 2026 promotion collection that includes a known active date to prove the generator/replay behavior. Include an empty/invalid-date source test for the generator's clear failure path.
- Mock or wrap the two ranking calls only where necessary to capture arguments; assert exact timestamp equality and that `customer_orders` derives from history only.
- Keep tests offline: no FastAPI server, external LLM, database mutation, or production bandit/customer-store writes.
- Run the focused test module first, then the repository's full unittest command. The generation/replay commands are integration evidence and must run only after focused tests are green.

### References

- [Source: guide.md#Task 2 — Repair Replay Fairness and Evidence]
- [Source: _bmad-output/implementation-artifacts/spec-customer-personalization.md#Review Findings]
- [Source: _bmad-output/planning-artifacts/epics-customer-personalization-2026-07-11.md#Epic 3: Personalization Evidence]
- [Source: generate_customer_personas.py#generate_personas]
- [Source: personalization_backtest.py#run_personalization_backtest]
- [Source: promo_engine.py#generate_promo_calendar]
- [Source: backtest.py#_recommended_price]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add red tests for calendar-aligned fixture generation, timestamp/no-leakage replay inputs, 1–5 panel validation, coverage metadata, and sale-price stability.
- Implement the minimum generator and replay changes to satisfy those contracts.
- Run focused tests, then regenerate the full data/replay chain and run full regression before marking this story ready for review.

### Debug Log References

- Story created from `guide.md` Task 2 after confirming Task 1 is complete in commit `29e7a0c`.
- `sprint-status.yaml` has no customer-personalization task entry; this task follows the existing standalone `spec-task-1-*` artifact convention and must not alter the stale sprint ledger.

### Completion Notes List

- Implemented calendar-aligned persona generation using only active 2026 promotion dates from the established generated promotion calendar. Empty/invalid calendars now fail clearly.
- The replay now accepts only panels 1–5, records active-promotion coverage, retains hold-out-only acceptance evidence, and labels its result as synthetic scenario evidence rather than real customer-sales proof.
- Added focused offline tests for fixture byte determinism, strict chronology, active-calendar hold-outs, no history leakage, exact strategy timestamps, panel rejection above five, coverage metadata, and effective sale-price fallback.
- Code review resolved four findings: malformed timestamp skipping, null-calendar safety, panel-accurate evidence labels, and Lunch/Dinner coverage parity with the general reranker. The added review regressions pass.
- Final validation passed: `python -m unittest tests.test_customer_personas` (4 tests); required generator/miner/database/backtest/persona/replay chain; `python -m unittest discover -s tests -p "test_*.py"` (85 tests).
- Repeated generator/replay verification produced identical SHA-256 values: fixture `68f6612f94f4aecbfec35f55f3e5bf3c9e8d898ec73c79260a7f86afdabe7802`; report `d4bfec4fb9f4ba5db9f72344400a888825805e8c07da71a81a5336a17c52ffa3`. The refreshed report covers 500/500 eligible personas (1.0) on active promotion-calendar dates.

### File List

- `generate_customer_personas.py`
- `personalization_backtest.py`
- `tests/test_customer_personas.py`
- `_bmad-output/data/customer_personas.json`
- `_bmad-output/data/personalization_backtest.json`
- `_bmad-output/implementation-artifacts/spec-task-2-replay-fairness-and-evidence.md`

### Change Log

- 2026-07-11: Created Task 2 implementation context from the guide, review ledger, prior Task 1 record, customer-personalization epic, current generator/replay code, and generated promotion calendar.
- 2026-07-11: Implemented and validated Task 2 replay-fairness repair; status set to review for the required adversarial code-review workflow.
- 2026-07-11: Addressed four adversarial review findings, reran the full required validation chain, and marked Task 2 done. Sprint status was intentionally not synced because this standalone task has no sprint key.
