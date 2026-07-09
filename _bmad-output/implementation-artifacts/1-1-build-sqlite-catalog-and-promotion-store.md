# Story 1.1: Build SQLite Catalog And Promotion Store

Status: done

## Story

As a developer,
I want menu and promotion CSVs loaded into SQLite,
so that the demo has a relational source for structured catalog data.

## Acceptance Criteria

1. **Given** `_bmad-output/data/menu.csv` and `_bmad-output/data/promotions.csv` exist with their required fields
   **When** the SQLite initialization command is run
   **Then** a local SQLite database is created or rebuilt with menu and promotion tables
   **And** the imported records preserve item names, categories, prices, images when present, promotion names, discount values, and date ranges.
2. **Given** the SQLite initialization command has already been run once
   **When** the command is run again with the same source files
   **Then** the resulting catalog and promotion rows are deterministic
   **And** duplicate rows are not accumulated.
3. **Given** a required menu field such as `name`, `category`, or `price` is missing
   **When** SQLite initialization runs
   **Then** the command fails with a clear validation error
   **And** it does not silently create an incomplete runtime database.

## Tasks / Subtasks

- [x] Task 1: Create SQLite Schema and Database Model (AC: 1)
  - [x] Subtask 1.1: Design schema for menu and promotions tables
  - [x] Subtask 1.2: Implement python code to create the SQLite file and define tables
- [x] Task 2: Implement Import and Validation Script (AC: 1, 2, 3)
  - [x] Subtask 2.1: Read and parse menu.csv and promotions.csv with proper field validations
  - [x] Subtask 2.2: Ensure duplicate prevention and deterministic reloading
  - [x] Subtask 2.3: Raise error and halt on missing required fields (name, category, price)
- [x] Task 3: Add Command-Line Interface (AC: 1)
  - [x] Subtask 3.1: Expose a command to run this initialization (e.g. `python init_db.py` or similar)

## Dev Notes

- SQLite database file should be placed at a logical location, e.g., `_bmad-output/data/kiosk.db`.
- Database schemas must handle data types correctly (INTEGER/REAL for price, discount_pct; TEXT for name, category, image, start_date, end_date).
- Maintain robust validation: raise exception or exit with code non-zero if validation fails.
- Follow existing formatting patterns, e.g., `main.py` and `generate_data.py`.

### Project Structure Notes

- Keep implementation in the root directory (e.g., `database.py` or `init_db.py` or similar).

### References

- [epics-sqlite-layer-2026-07-08.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/epics-sqlite-layer-2026-07-08.md)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash

### Debug Log References

### Completion Notes List

### File List
