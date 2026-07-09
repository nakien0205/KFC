# Story 1.5: Document And Verify SQLite Data Flow

Status: done

## Story

As a maintainer,
I want docs and tests updated,
so that future work knows SQLite is implemented and how to rebuild it.

## Acceptance Criteria

1. **Given** the SQLite layer is implemented
   **When** project documentation is updated
   **Then** `AGENTS.md`, `docs/index.md`, stack/spec wording, and submission wording explain SQLite as implemented local storage
   **And** no document still describes SQLite only as deferred.

2. **Given** tests are run for the SQLite layer
   **When** the test suite executes
   **Then** tests cover SQLite initialization, data import validation, runtime API behavior, and backtest compatibility
   **And** tests do not make real Gemini, OpenRouter, or Ollama network calls.

3. **Given** bandit persistence is involved in tests or backtest execution
   **When** those paths run
   **Then** production bandit weights are not written
   **And** the existing `threading.RLock` and atomic `os.replace` persistence behavior remains preserved.

## Tasks / Subtasks

- [x] Task 1: Update Project Documentation (AC: 1)
  - [x] Update [AGENTS.md](file:///d:/Python/Projects/KFC/AGENTS.md) to explain that SQLite is the active local database, detail the startup loading lifespan in `main.py`, and document command `python init_db.py`.
  - [x] Update [docs/index.md](file:///d:/Python/Projects/KFC/docs/index.md) to describe `kiosk.db` under `_bmad-output/data/` as the primary repository of active menu, promotions, and rule data, and add the database initialization script to "Getting Started".
  - [x] Update [_bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md](file:///d:/Python/Projects/KFC/_bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md) and [_bmad-output/specs/spec-kfc-kiosk-recommender/stack.md](file:///d:/Python/Projects/KFC/_bmad-output/specs/spec-kfc-kiosk-recommender/stack.md) to remove mentions of SQLite as a deferred/deferred migration path, establishing it as the active local store.
  - [x] Update [hackathon_submission.md](file:///d:/Python/Projects/KFC/hackathon_submission.md) to declare the local SQLite database as fully implemented.
  - [x] Verify if SQLite is marked as deferred in [_bmad-output/implementation-artifacts/deferred-work.md](file:///d:/Python/Projects/KFC/_bmad-output/implementation-artifacts/deferred-work.md) and clean/align it.
- [x] Task 2: Verify Test Isolation and Coverage (AC: 2, 3)
  - [x] Audit [tests/test_sqlite.py](file:///d:/Python/Projects/KFC/tests/test_sqlite.py), [tests/test_main.py](file:///d:/Python/Projects/KFC/tests/test_main.py), and [tests/test_backtest.py](file:///d:/Python/Projects/KFC/tests/test_backtest.py) to ensure they cover database init, validation, api endpoint fallback, and backtest loading.
  - [x] Confirm no SQLite-related tests trigger real network connections to Gemini, OpenRouter, or Ollama.
  - [x] Confirm all tests involving bandit weights (e.g. [tests/test_bandit.py](file:///d:/Python/Projects/KFC/tests/test_bandit.py), [tests/test_backtest.py](file:///d:/Python/Projects/KFC/tests/test_backtest.py)) isolate their writes using temporary files or mocks, preventing updates to production `bandit_weights.json` and keeping concurrency properties safe.

## Dev Notes

- The database file is located at `_bmad-output/data/kiosk.db`.
- Database initialization code: `init_db.py` (`python init_db.py`).
- Runtime data loading logic is in `main.py` lifespan startup, falling back to CSVs/JSONs if database is not ready or missing.
- Backtest loading logic is in `backtest.py` `_load_backtest_inputs()`.

### Project Structure Notes

- Keep all changes concentrated in documentation updates and verifying/improving unit tests under the `tests/` directory.

### References

- [epics-sqlite-layer-2026-07-08.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/epics-sqlite-layer-2026-07-08.md)
- [init_db.py](file:///d:/Python/Projects/KFC/init_db.py)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

### Completion Notes List

- Updated `AGENTS.md` with active SQLite database flow, database init command, and revised implementation rules.
- Updated `docs/index.md` getting started guide and source tree structure.
- Updated product specification `SPEC.md` to remove deferred database descriptions.
- Updated `hackathon_submission.md` to show SQLite relational store is fully implemented.
- Updated `ARCHITECTURE-SPINE.md` to move SQLite out of the deferred section and mark it as active.
- Ran the full test suite of 54 tests and verified 100% success and safety of the SQLite data flow, Gemini/Ollama mocking, and isolated bandit weights.

### File List

- [AGENTS.md](file:///d:/Python/Projects/KFC/AGENTS.md)
- [docs/index.md](file:///d:/Python/Projects/KFC/docs/index.md)
- [_bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md](file:///d:/Python/Projects/KFC/_bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md)
- [hackathon_submission.md](file:///d:/Python/Projects/KFC/hackathon_submission.md)
- [_bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md)
