---
baseline_commit: NO_VCS
---

# Story 5.1: Ollama Local LLM Support

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want to configure the recommendation system to call a local Ollama LLM server,
so that the kiosk can generate personalized recommendation copy fully offline without relying on external Gemini API keys.

## Acceptance Criteria

1. **Ollama Configuration**:
   - The application must support and read configuration variables from the environment:
     - `OLLAMA_HOST` (string, default: `http://localhost:11434`)
     - `OLLAMA_MODEL` (string, default: `llama3.2:3b`)
     - `USE_OLLAMA` (boolean or string representation, default: `false`)
2. **Provider Selection Routing**:
   - If `USE_OLLAMA` is configured to `true` (case-insensitive) OR if `GEMINI_API_KEY` is not present in the environment/config, the system must call the local Ollama LLM provider.
   - Otherwise, the system must default to using the Google Gemini API.
3. **API Request & Format**:
   - The Ollama client must use the `POST /api/chat` or `POST /api/generate` endpoint.
   - It must specify `"format": "json"` in the request body to enforce a structured JSON response matching the existing schema: `{"copy": "...", "rationale": "..."}`.
   - Prompt instructions must direct the LLM to output a JSON object with `copy` and `rationale` keys, localized in Vietnamese, identical to the Gemini prompt structure.
4. **Latency & Timeout Guardrail**:
   - The system must enforce a strict `1.2s` timeout threshold on the Ollama API call.
5. **Offline Fallback Engine**:
   - If the Ollama API call fails (Ollama not running, model not pulled) or exceeds the `1.2s` timeout, the system must immediately and gracefully fall back to the local rule-based template copy generator.

## Tasks / Subtasks

- [x] **Task 1: Add configuration variables** (AC: 1)
  - [x] Add `OLLAMA_HOST`, `OLLAMA_MODEL`, and `USE_OLLAMA` to the environment configuration parser or fallback dictionary.
- [x] **Task 2: Implement Ollama client request** (AC: 3)
  - [x] Implement `generate_ollama_recommendation_copy(item_name, item_price, cart_items, host, model, timeout)` calling local Ollama `POST /api/chat` with JSON format.
  - [x] Ensure request body enforces JSON format output.
- [x] **Task 3: Integrate Provider Selection and Fallbacks** (AC: 2, 4, 5)
  - [x] Update `generate_recommendation_copy` in `recommender.py` to route to either Gemini or Ollama based on the environment keys.
  - [x] Ensure any Ollama failure or timeout reverts to the local rule-based fallback generator.
- [x] **Task 4: Implement Unit and Mock Integration Tests** (AC: 1-5)
  - [x] Add unit tests in `test_recommender.py` mock-testing the Ollama client call.
  - [x] Test Ollama success path, parsing correctness, timeout path, and connection failure path.

### Review Findings

- [x] [Review][Patch] Catch-all exception block silently swallows all errors [recommender.py:56]
- [x] [Review][Patch] Host parameter rstrip crash if passed as non-string [recommender.py:15]
- [x] [Review][Patch] Output type validation missing for copy and rationale values [recommender.py:51]
- [x] [Review][Patch] Test isolation issue: test_gemini_non_string_cart_items can make real network calls [test_recommender.py:161]
- [x] [Review][Patch] Missing unit test for connection failure path [test_recommender.py:202]
- [x] [Review][Patch] Unit tests mutate os.environ directly without clean restoring [test_recommender.py:185]

## Dev Notes

- **Architecture Compliance (AD-3)**: Limit LLM API calls to exactly one per recommendation. Enforce 1.2s timeout. Maintain offline fallback.
- **Pipes & Filters (AD-1)**: Keep the new Ollama client driver code completely inside `recommender.py`.

### References

- [ARCHITECTURE-SPINE.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md#L134) (Deferred: Ollama Local LLM Support)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- Verified all 29 unit tests pass.
- Added mock tests covering the Ollama provider routing, successful JSON parsing from message content, and timeout fallbacks.

### Completion Notes List

- Added configuration variables check in `recommender.py`.
- Implemented `generate_ollama_recommendation_copy` driver.
- Added tests in `test_recommender.py`.

### File List

- `recommender.py`
- `test_recommender.py`
