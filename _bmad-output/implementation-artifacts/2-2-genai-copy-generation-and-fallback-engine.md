---
baseline_commit: NO_VCS
---

# Story 2.2: GenAI Copy Generation and Fallback Engine

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want to implement a promotional copy generator using the Gemini API with a local rule-based fallback,
so that customers see engaging, personalized recommendation copy and statistical rationales without risking kiosk latency or offline demo failures.

## Acceptance Criteria

1. **Dynamic Copy Generation (GenAI)**:
   - Must generate a personalized promotional copy in Vietnamese.
   - Must generate a brief rationale/reason in Vietnamese (e.g., "Được gợi ý vì 68% khách hàng mua kèm khoai tây chiên").
   - Prompt should incorporate current `cart_items` context to make copy personalized.
2. **Single API Call Constraint**:
   - Limit to exactly one API call to `gemini-2.5-flash` per recommendation event.
3. **Structured JSON Output**:
   - Must request and enforce structured JSON response from Gemini API containing fields:
     - `copy`: string (Vietnamese promotional copy)
     - `rationale`: string (Vietnamese rationale/reason)
4. **Latency & Timeout Guardrail**:
   - Enforce a strict `1.2s` timeout on the Gemini API call.
5. **Offline Fallback Engine**:
   - If Gemini API call fails (network error, bad key) or times out (> 1.2s), must immediately trigger local template fallback.
6. **Local Rule-Based Copy Template**:
   - Fallback copy: `"Hoàn thành bữa ăn! Thêm [item_name] chỉ với [price]đ"`
   - Fallback rationale: `"Thường được mua kèm với các sản phẩm trong giỏ hàng."`
7. **Stateless API Wrapper**:
   - Logic must be stateless and accept target item details (`item_name`, `price`), `cart_items`, and configuration parameters (API key, timeout limit).

## Tasks / Subtasks

- [x] **Task 1: Implement Local Fallback Generator** (AC: 6)
  - [x] Implement `generate_local_fallback(item_name, item_price)` returning local copy and rationale in Vietnamese.
- [x] **Task 2: Implement GenAI Client Wrapper with Structured JSON** (AC: 2, 3, 4)
  - [x] Set up client call using Gemini API (`gemini-2.5-flash`).
  - [x] Define prompt system instruction and JSON schema format for `{ "copy": "...", "rationale": "..." }`.
  - [x] Apply strict timeout of `1.2` seconds on API call.
- [x] **Task 3: Implement Fallback Wrapper in Recommender** (AC: 1, 5, 7)
  - [x] Implement `generate_recommendation_copy(item_name, item_price, cart_items, api_key, timeout=1.2)` in `recommender.py`.
  - [x] Wrap Gemini call in `try-except` block to capture all exceptions (Timeout, API errors, JSON parse errors) and return fallback copy.
- [x] **Task 4: Implement Unit and Mock Integration Tests** (AC: 1-7)
  - [x] Add test cases to `test_recommender.py` covering copy generator.
  - [x] Mock Gemini API response to test success path.
  - [x] Mock Gemini API timeout/failure to verify fallback logic is invoked and returns correct fallback strings.

### Review Findings

- [x] [Review][Patch] TypeError if `cart_items` has non-string elements in `generate_recommendation_copy` [recommender.py:163]
- [x] [Review][Defer] Brittle promotion matching via hardcoded substring checks [recommender.py:11] — deferred, pre-existing
- [x] [Review][Defer] Generic promotions without matched keywords ignored [recommender.py:28] — deferred, pre-existing
- [x] [Review][Defer] Time boosts limited to lunch/dinner [recommender.py:43] — deferred, pre-existing
- [x] [Review][Defer] Confidence fallback to support metric [recommender.py:92] — deferred, pre-existing
- [x] [Review][Defer] Potential crash if menu DataFrame lacks columns [recommender.py:78] — deferred, pre-existing
- [x] [Review][Defer] Potential crash if menu_items is a dictionary or other collection [recommender.py:72] — deferred, pre-existing
- [x] [Review][Defer] Deduplication only keeps highest score [recommender.py:122] — deferred, pre-existing
- [x] [Review][Defer] Return value lacks item metadata [recommender.py:129] — deferred, pre-existing
- [x] [Review][Defer] TypeError if `active_promotions` contains non-dict elements [recommender.py:54] — deferred, pre-existing
- [x] [Review][Defer] TypeError if `timestamp` is passed as datetime instead of string [recommender.py:35] — deferred, pre-existing
- [x] [Review][Defer] AttributeError if menu item has category set to None [recommender.py:100] — deferred, pre-existing
- [x] [Review][Defer] AttributeError if `item_name`, `item_category`, or `promo_name` is non-string in `is_item_in_promotion` [recommender.py:7] — deferred, pre-existing
- [x] [Review][Defer] Test suite lacks edge case coverage [test_recommender.py:222] — deferred, pre-existing

## Dev Notes

- **Architecture Compliance (AD-3)**: Limit to exactly one API call. Enforce 1.2s timeout. Ensure local fallback works offline.
- **Environment Configuration (NFR6)**: Load `GEMINI_API_KEY` from environment variables.
- **Pipes & Filters Architecture (AD-1)**: Place all copy generation and fallback logic inside `recommender.py`.

### Project Structure Notes

- Add `generate_recommendation_copy` to `recommender.py`.
- No dependencies on local databases; keep all configurations and fallback templates code-defined.

### References

- [SPEC.md](file:///d:/Python/Projects/KFC/_bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md#L28-L30) (CAP-4)
- [ARCHITECTURE-SPINE.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md#L50-L54) (AD-3)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- API mock testing successfully verifies success, timeout, network error, and missing key fallbacks.
- Tests passed: `python -m unittest test_recommender.py` executed successfully.

### Completion Notes List

- Implemented `format_price_vnd` to format prices in Vietnamese Dong format (using dots as thousands separators, e.g., `20.000đ`).
- Implemented `generate_local_fallback` to construct local template copy and rationale.
- Implemented `generate_recommendation_copy` doing direct REST call to Gemini 2.5 Flash, handling structured JSON output, and enforcing a 1.2s timeout.
- Added mock unit tests in `test_recommender.py` covering all success, failure, timeout, and API key scenarios.

### File List

- `recommender.py`
- `test_recommender.py`
