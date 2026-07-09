# Story 1.2: Store Orders And Affinity Rules In SQLite

Status: done

## Story

As a developer,
I want historical orders and mined rules stored in SQLite,
So that recommendation inputs live in one relational dataset.

## Acceptance Criteria

1. **Given** `_bmad-output/data/orders.csv` and `_bmad-output/data/affinity_rules.json` exist
   **When** the SQLite loading path runs
   **Then** orders, order items, and affinity rules are imported into SQLite
   **And** each affinity rule preserves `antecedents`, `consequents`, `support`, `confidence`, and `lift`.

2. **Given** generated orders include the optional `scenario` column
   **When** orders are loaded into SQLite
   **Then** the scenario value is preserved where available
   **And** downstream consumers that only require `order_id` and `item_name` still work.

3. **Given** SQLite loading finishes successfully
   **When** validation checks run
   **Then** row counts and required fields are checked against the flat source artifacts
   **And** mismatches fail clearly instead of producing a stale or partial database.

## Tasks / Subtasks

- [x] Task 1: Create Orders and Affinity Rules Tables (AC: 1, 2)
  - [x] Subtask 1.1: Design schema for `orders` and `affinity_rules` tables in SQLite
  - [x] Subtask 1.2: Update database initialization code in `init_db.py` to create these tables
- [x] Task 2: Implement Data Loading and Validation (AC: 1, 2, 3)
  - [x] Subtask 2.1: Read and parse orders.csv (preserving scenario column) and load them into SQLite
  - [x] Subtask 2.2: Read and parse affinity_rules.json and load rules into SQLite (handling antecedents/consequents as JSON or comma-separated lists)
  - [x] Subtask 2.3: Implement validation checking row counts and essential fields from source CSV/JSON against SQLite table counts after loading
- [x] Task 3: Add Command-Line Interface and Unit Tests (AC: 1, 3)
  - [x] Subtask 3.1: Update `init_db.py` CLI so it loads all four entities (`menu.csv`, `promotions.csv`, `orders.csv`, `affinity_rules.json`)
  - [x] Subtask 3.2: Update `tests/test_sqlite.py` to verify orders and rules tables are correctly initialized, loaded, and validated

## Dev Notes

- SQLite database file is `_bmad-output/data/kiosk.db`.
- Schema design:
  - `orders` table: `order_id TEXT`, `item_name TEXT`, `scenario TEXT`, PRIMARY KEY (order_id, item_name). Wait! A transaction can have multiple items, so `order_id` is not unique. A composite primary key (order_id, item_name) is ideal.
  - `affinity_rules` table: `rule_id INTEGER PRIMARY KEY AUTOINCREMENT`, `antecedents TEXT NOT NULL` (JSON-serialized string or comma-separated), `consequents TEXT NOT NULL` (JSON-serialized string or comma-separated), `support REAL NOT NULL`, `confidence REAL NOT NULL`, `lift REAL NOT NULL`.
- Validation should compare:
  - Total rows in `orders` table equals number of rows in `orders.csv`.
  - Total rules in `affinity_rules` table equals number of rules in `affinity_rules.json`.
  - Any mismatch should raise ValueError or sys.exit(1).
- Preserving existing rules and constraints is critical (e.g., deterministic, no duplicates accumulated, drop tables before importing).

### References

- [epics-sqlite-layer-2026-07-08.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/epics-sqlite-layer-2026-07-08.md)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash

### Completion Notes

- Created `orders` and `affinity_rules` tables in local SQLite database.
- Parsed and validated incoming fields and columns for `orders.csv` and `affinity_rules.json`.
- Handled JSON serialization for `antecedents` and `consequents` lists.
- Implemented post-insert row count validation checks to prevent stale database state.
- Updated `tests/test_sqlite.py` with comprehensive tests verifying data loading, schema correctness, and validations.

### File List

- [init_db.py](file:///d:/Python/Projects/KFC/init_db.py)
- [tests/test_sqlite.py](file:///d:/Python/Projects/KFC/tests/test_sqlite.py)

### Change Log

- Update database initialization script (`init_db.py`) to create and populate orders and rules tables.
- Update SQLite unit tests (`tests/test_sqlite.py`) to cover new entities and error paths.

### Review Findings

- [x] [Review][Defer] SQLite PRAGMA foreign_keys is enabled but no foreign keys are defined in the schema [init_db.py:165] — deferred, cosmetic
- [x] [Review][Defer] Orders table composite primary key (order_id, item_name) constrains items to be unique per order [init_db.py:206] — deferred, design constraint compatible with synthetic dataset

