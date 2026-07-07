---
baseline_commit: 0c73971bbed139e82ed7b68124b6ec545a88f65a
---

# Story 2.3: FastAPI Server and /api/recommend Endpoint

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a kiosk developer,
I want to create a FastAPI web server that loads offline data and exposes the recommendation pipeline,
so that the frontend Kiosk UI can request and display live context-adjusted recommendations.

## Acceptance Criteria

1. **FastAPI Web Server (`main.py`)**: Expose web API using FastAPI framework. Core recommendation logic remains stateless and isolated inside [recommender.py](file:///d:/Python/Projects/KFC/recommender.py) (AD-1).
2. **In-Memory Cache on Startup**:
   - At application startup, read local data files:
     - `menu.csv` (menu catalog)
     - `promotions.csv` (active promotions calendar)
     - `affinity_rules.json` (mined association rules)
   - Read from `_bmad-output/data/` directory (AD-2).
   - Cache loaded objects in-memory for O(1) retrieval during recommendation requests.
3. **Stateless `/api/recommend` Endpoint**:
   - Expose `POST /api/recommend` route.
   - Request schema:
     - `cart_items`: list of string item names (e.g., `["Burger Zinger"]`)
     - `timestamp`: ISO 8601 string (e.g., `"2026-07-06T12:00:00+07:00"`)
   - If `cart_items` is null/empty or `timestamp` is invalid, return an empty list of recommendations with a `200 OK` status, or handle errors gracefully without crashes.
4. **Recommendation Rerank & Copy Generation**:
   - Step 1: Call `rerank_recommendations(cart_items, active_promotions, affinity_rules, menu_items, timestamp)` from [recommender.py](file:///d:/Python/Projects/KFC/recommender.py) to get ranked candidate items and scores.
   - Step 2: For each returned candidate (up to a reasonable limit, e.g. top 5 candidates):
     - Look up candidate price from cached menu data.
     - Call `generate_recommendation_copy(item_name, item_price, cart_items)` from [recommender.py](file:///d:/Python/Projects/KFC/recommender.py) to fetch Vietnamese copy and rationale.
5. **Response Contract & Performance (NFR1)**:
   - Response envelope must be a JSON array of recommendations.
   - Each recommendation object must contain:
     - `name`: string (item name)
     - `price`: float (item price in VND)
     - `score`: float (final confidence score)
     - `copy`: string (Vietnamese localized copy)
     - `rationale`: string (Vietnamese localized rationale)
   - Total response time must be under 1.5 seconds (NFR1). Limit Gemini API call inside copy generation to exactly 1 call with a strict `1.2s` timeout (AD-3).
6. **Error Envelope (Consistency Conventions)**:
   - Return standard error envelope `{"detail": "error message"}` for HTTP exceptions.

## Tasks / Subtasks

- [x] **Task 1: Setup FastAPI Server & Startup Logic** (AC: 1, 2)
  - [x] Implement `main.py` driving layer.
  - [x] Define startup event handler to load CSV/JSON files from `_bmad-output/data/`.
  - [x] Implement robust caching mechanism for menu list, promotions list, and affinity rules.
- [x] **Task 2: Define Request and Response Schemas** (AC: 3, 5)
  - [x] Implement Pydantic request model (`RecommendRequest`) containing `cart_items` and `timestamp`.
  - [x] Implement Pydantic response models matching the specified contract.
- [x] **Task 3: Implement POST /api/recommend Endpoint** (AC: 3, 4, 5, 6)
  - [x] Route the request to the recommender pipeline filters in `recommender.py`.
  - [x] Construct the response by merging candidate metadata, prices, confidence scores, and promotional copies.
  - [x] Implement error handling wrapping exceptions in `{"detail": "..."}` envelopes.
- [x] **Task 4: Implement Server Verification & Mock Tests** (AC: 1-6)
  - [x] Add API integration test cases (e.g. in `test_main.py` using FastAPI's `TestClient`).
  - [x] Verify endpoints with empty cart, active timezone offsets, and simulated API timeouts.

### Review Findings

- [x] [Review][Patch] Lifespan context manager instead of deprecated on_event [main.py:21]
- [x] [Review][Patch] Missing float casting error validation in menu.csv parsing [main.py:37]
- [x] [Review][Patch] Missing menu.csv structure validation for name/price columns [main.py:33]
- [x] [Review][Patch] Missing validation for affinity_rules.json schema structure [main.py:53]
- [x] [Review][Patch] Missing None check for candidates returned from recommender [main.py:84]
- [x] [Review][Patch] Potential KeyErrors if candidate dict lacks name or score [main.py:85]
- [x] [Review][Patch] Potential AttributeError if generate_recommendation_copy returns None [main.py:89]
- [x] [Review][Patch] Pydantic RecommendRequest rejects null/missing cart_items with 422 instead of returning 200 OK empty list [main.py:57]
- [x] [Review][Patch] Hardcoded paths to data files prevent running from different directory [main.py:26]
- [x] [Review][Patch] Silent startup errors print to stdout instead of standard logging [main.py:39]
- [x] [Review][Patch] Caching MENU_ITEMS_DF starts as None, crashes rerank_recommendations [main.py:15]
- [x] [Review][Patch] Missing default item price fallback in recommend [main.py:87]
- [x] [Review][Patch] Missing top-5 limit in candidate iteration [main.py:84]
- [x] [Review][Patch] Multiple Gemini API calls triggered inside recommendation loop [main.py:89]
- [x] [Review][Defer] Loop uses pandas iterrows [main.py:36] — deferred, pre-existing
- [x] [Review][Defer] No API request size limit [main.py:57] — deferred, pre-existing

## Dev Notes

- **Pipes & Filters Architecture (AD-1)**: Keep `main.py` as a thin driver. No recommendation algorithms or raw string parsing should happen inside endpoint functions.
- **Directory Structure (AD-6)**: `main.py` must reside at the project root.
- **Vietnamese Dong Representation**: Represent all prices in VND.
- **Environment API Key (NFR6)**: Gemini API key should be loaded via the environment variable `GEMINI_API_KEY`.

### References

- [SPEC.md](file:///d:/Python/Projects/KFC/_bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md#L25-L30) (CAP-3, CAP-4)
- [ARCHITECTURE-SPINE.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md#L40-L44) (AD-1)
- [ARCHITECTURE-SPINE.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md#L45-L54) (AD-2, AD-3)
- [recommender.py](file:///d:/Python/Projects/KFC/recommender.py) (Existing module)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- API tests cover empty cart, timezone-aware timestamp, and mock Gemini API calls.
- Run tests command: `python -m unittest test_main.py` -> 4 tests passed.
- Run all tests command: `python -m unittest discover -p "test_*.py"` -> 20 tests passed.

### Completion Notes List

- Implemented `main.py` driving layer utilizing FastAPI.
- Implemented startup caching handler loading `menu.csv`, `promotions.csv`, and `affinity_rules.json` from `_bmad-output/data/` in-memory.
- Implemented `RecommendRequest` and `RecommendationResponse` Pydantic models.
- Implemented endpoint `POST /api/recommend` routing to `recommender.py`.
- Developed mock and integration tests in `test_main.py`.

### File List

- `main.py`
- `test_main.py`
