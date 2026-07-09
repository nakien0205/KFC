# Story 1.4: Run Backtest From The Same SQLite Dataset

Status: done

## Story

As a judge or developer,
I want the backtest to use the same SQLite-backed data source,
So that demo metrics match runtime data.

## Acceptance Criteria

1. **Given** the SQLite database has been built from the generated artifacts
   **When** `python backtest.py` runs
   **Then** it reads the same structured menu, promotion, order, and affinity-rule data used by runtime loading
   **And** it still reports baseline AOV, hybrid AOV, absolute change, percentage uplift, and total simulated transactions.

2. **Given** the backtest runs with a fixed seed
   **When** the simulation completes
   **Then** the result is deterministic for unchanged input data
   **And** the backtest uses temporary bandit weights instead of writing production bandit state.

3. **Given** the SQLite database is missing or stale
   **When** the backtest starts
   **Then** the failure mode is explicit
   **And** the user can rebuild the database from the documented local command.

## Tasks / Subtasks

- [x] Task 1: Load Backtest Inputs from SQLite (AC: 1)
  - [x] Update `_load_backtest_inputs` in `backtest.py` to read from the SQLite database `kiosk.db` if it is present and valid.
  - [x] Query and map the `menu`, `promotions`, `orders`, and `affinity_rules` tables to match the expected pandas dataframes and list structures.
  - [x] Parse `antecedents` and `consequents` JSON arrays when deserializing `affinity_rules`.
- [x] Task 2: Implement Explicit Error Handling for Missing/Stale Database (AC: 3)
  - [x] If `kiosk.db` is missing, raise a `FileNotFoundError` with a clear explanation and the command to rebuild it (`python init_db.py`).
  - [x] Catch `sqlite3.Error` or table structure errors, and raise a `ValueError` indicating the database is stale/invalid, with instructions to run `python init_db.py`.
- [x] Task 3: Verify Determinism and Weight Persistence Isolation (AC: 2)
  - [x] Ensure that seed runs remain fully deterministic.
  - [x] Verify that simulation weight updates are isolated to temporary files and do not touch `bandit_weights.json`.
- [x] Task 4: Add Verification Tests (AC: 1, 2, 3)
  - [x] Add unit tests in `tests/test_backtest.py` (or update existing test files) verifying that the backtest successfully loads inputs from SQLite when available, runs the simulation, produces identical/deterministic results, and raises an explicit error when the database is missing or invalid.

## Dev Notes

- The SQLite database file path is `_bmad-output/data/kiosk.db`.
- Schema information for each table is defined in `init_db.py`:
  - `menu` (item_id, name, category, price, image)
  - `promotions` (promo_id, name, discount_pct, start_date, end_date)
  - `orders` (order_id, item_name, scenario)
  - `affinity_rules` (rule_id, antecedents, consequents, support, confidence, lift)
- The existing CSV-based loading logic should only be used as a fallback if the database path isn't active or if we explicitly want fallback, but per spec, the SQLite database is the primary store, and missing/stale db must fail explicitly.
- Run tests via `python -m unittest discover -s tests -p "test_*.py"`.

### References

- [epics-sqlite-layer-2026-07-08.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/epics-sqlite-layer-2026-07-08.md)
- [backtest.py](file:///d:/Python/Projects/KFC/backtest.py)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Completion Notes

- Modified `backtest.py` to load backtest inputs from `_bmad-output/data/kiosk.db` using sqlite3 connection.
- Handled parsing and mapping of all tables (`menu`, `promotions`, `orders`, `affinity_rules`) to expected objects, ensuring JSON deserialization of antecedents/consequents in affinity rules.
- Added explicit error handling in `backtest.py`: throws `FileNotFoundError` if database file doesn't exist, and `ValueError` if the database schema is invalid or connection fails, instructing the user to rebuild the database via `python init_db.py`.
- Added mock-based unit tests `test_backtest_missing_db_raises_error` and `test_backtest_stale_db_raises_error` in `tests/test_backtest.py` to test error reporting.
- Executed the entire test suite and verified that all 54 tests pass and simulation results remain deterministic and correct.

### File List

- [backtest.py](file:///d:/Python/Projects/KFC/backtest.py)
- [tests/test_backtest.py](file:///d:/Python/Projects/KFC/tests/test_backtest.py)
