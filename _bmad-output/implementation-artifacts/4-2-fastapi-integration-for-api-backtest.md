---
baseline_commit: 0c73971bbed139e82ed7b68124b6ec545a88f65a
---

# Story 4.2: FastAPI Integration for `/api/backtest`

Status: done

## Story

As a kiosk developer,
I want to expose the backtest simulation via a web API,
so that the kiosk UI (or pitch dashboard) can trigger the simulation dynamically and retrieve results.

## Acceptance Criteria

1. **Backtest Endpoint**: Expose `POST /api/backtest` in the FastAPI backend (`main.py`) (FR8).
2. **Execution**: The endpoint must execute the backtest replay simulation module and calculate metrics.
3. **Response Payload**: The response must contain a structured JSON object:
   ```json
   {
     "baseline_aov": 123456.78,
     "hybrid_aov": 134567.89,
     "absolute_change": 11111.11,
     "percentage_uplift": 9.0
   }
   ```
4. **Offline Mode Performance**: The response must return in under 2 seconds without blocking or memory leaks.

## Tasks / Subtasks

- [x] **Task 1: Add `/api/backtest` POST route in `main.py`** (AC: 1, 3)
- [x] **Task 2: Integrate `backtest.py` simulation logic into the route** (AC: 2)
- [x] **Task 3: Implement unit test for the backtest API endpoint** (AC: 1, 3)
- [x] **Task 4: Add UI components or trigger mechanism in index.html/app.js (optional/pitch)** (AC: 2)

## Dev Notes

- Since `main.py` is a thin controller (Pipes & Filters architecture), do not write the replay loop inside `main.py`. Import and call a function from `backtest.py`.
- Ensure tests verify both baseline and hybrid model AOV values are non-zero.

### Project Structure Notes

- Keep `main.py` clean. Import `run_backtest_simulation` from `backtest.py`.
- All prices in Vietnamese Dong (VND).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.2]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md#AD-5]

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

### Completion Notes List

- Implemented `POST /api/backtest` endpoint in `main.py`.
- Tested the endpoint with unit test suite in `test_main.py`.
- Added premium Backtest Simulation UI section, button and modal in `static/index.html`, `static/style.css`, and `static/app.js`.

### File List

- `main.py`
- `test_main.py`
- `static/index.html`
- `static/style.css`
- `static/app.js`

