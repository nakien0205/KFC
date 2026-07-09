# Story 1.3: Load Runtime Recommendations From SQLite

Status: done

## Story

As a kiosk operator,
I want the FastAPI app to load menu, promotions, and rules from SQLite,
So that the kiosk runs from the relational data source.

## Acceptance Criteria

1. **Given** the SQLite database exists and contains menu, promotion, and affinity-rule data
   **When** FastAPI starts
   **Then** runtime menu, promotion, and rule data are loaded from SQLite as the primary source
   **And** `/api/menu` keeps the same response shape as the current frontend expects.

2. **Given** a request to `/api/recommend` has an empty cart, missing timestamp, or invalid timestamp
   **When** the request is handled
   **Then** the API returns HTTP 200 with an empty list
   **And** this behavior matches the existing contract.

3. **Given** a recommendation request has valid cart items and timestamp
   **When** recommendations are generated from SQLite-loaded data
   **Then** no item already in the cart is recommended
   **And** only the top candidate receives external generated copy while remaining candidates use local fallback copy.

## Tasks / Subtasks

- [x] Task 1: Load Runtime Data from SQLite (AC: 1)
  - [x] Update `main.py` lifespan to load `MENU_ITEMS_DF`, `MENU_PRICE_LOOKUP`, `PROMOTIONS_LIST`, and `AFFINITY_RULES` from the SQLite database `_bmad-output/data/kiosk.db`.
  - [x] Implement fallback to the legacy CSV/JSON files if the SQLite database is missing, empty, or fails to load.
- [x] Task 2: Preserve API Contracts (AC: 2, 3)
  - [x] Ensure that empty carts, missing timestamps, and invalid timestamps return HTTP 200 with an empty list in `/api/recommend`.
  - [x] Ensure that `/api/menu` keeps the exact same output format.
  - [x] Ensure that recommendations never recommend items already in the cart.
  - [x] Ensure that only the top recommendation receives external AI copy, and others use local fallback copy.
- [x] Task 3: Implement Unit Tests (AC: 1, 2, 3)
  - [x] Add unit tests in `tests/test_main.py` (or a new test file) verifying that `main.py` loads data from SQLite database on startup, handles missing SQLite database gracefully by falling back to CSVs/JSONs, and serves recommendation and menu requests successfully.

## Dev Notes

- The database file path is `_bmad-output/data/kiosk.db`.
- Check if database file exists using `os.path.exists()`.
- Use `sqlite3` to connect to the database and query the tables.
- Table names in `kiosk.db`: `menu`, `promotions`, `orders`, `affinity_rules`.
- Ensure JSON deserialization of antecedents/consequents when loading rules.

### References

- [epics-sqlite-layer-2026-07-08.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/epics-sqlite-layer-2026-07-08.md)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Completion Notes

- Updated `main.py` lifespan to load `MENU_ITEMS_DF`, `MENU_PRICE_LOOKUP`, `PROMOTIONS_LIST`, and `AFFINITY_RULES` directly from SQLite `kiosk.db` if it exists.
- Handled parsing and JSON deserialization of affinity rules loaded from the SQLite table.
- Added comprehensive fallback path to legacy CSV/JSON files on database connection failure or missing database file.
- Added unit tests `TestMainSQLiteLoading` in `tests/test_main.py` verifying successful SQLite runtime data load and correct fallback behavior.

### File List

- [main.py](file:///d:/Python/Projects/KFC/main.py)
- [tests/test_main.py](file:///d:/Python/Projects/KFC/tests/test_main.py)
