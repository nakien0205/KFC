---
baseline_commit: NO_VCS
---

# Story 2.1: Context-Aware Reranker Algorithm

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want to implement a stateless reranking filter that applies context boosts to mined affinity confidence scores,
so that recommendations dynamically adjust to what is currently in the cart, active promotions, and the time of day.

## Acceptance Criteria

1. **Stateless Reranker Core**: The reranker function must be completely stateless. It accepts `cart_items` (list of item names), `active_promotions` (list of parsed promotions), `affinity_rules` (list of rules), `menu_items` (list of menu item metadata), and a `timestamp` (ISO 8601 string).
2. **Exclusion Constraint**: Mined consequents that are already in the `cart_items` must be filtered out and not recommended.
3. **Multiplicative Scoring**: Mined affinity confidence scores must be adjusted using the formula:
   $$\text{Score} = \text{Base\_Confidence} \times (1 + \text{Promo\_Boost}) \times (1 + \text{Time\_Boost})$$
4. **Promo Boost Logic**:
   - `Promo_Boost` is `+0.20` if the candidate item is actively promoted during the timestamp hour and date.
   - Active promotion matches the timestamp date against `start_date` and `end_date` in `promotions.csv`.
5. **Time Boost Logic**:
   - `Time_Boost` is `+0.15` if the timestamp hour matches the target category peak hours:
     - **Lunch (11:00 - 14:00)**: Boosts items in categories: `Burgers`, `Combos`.
     - **Dinner (17:00 - 21:00)**: Boosts items in categories: `Combos`, `Sides`.
   - Other times: `Time_Boost` is `0.0`.
6. **Sorting & Selection**:
   - Output must be a sorted list of candidate recommendations in descending order of final computed `Score`.
   - If the same item is suggested by multiple matching affinity rules, only keep the entry with the highest final `Score`.

## Tasks / Subtasks

- [x] **Task 1: Define Data Models & Reranker Interface** (AC: 1)
  - [x] Implement data contracts (schemas/models) for menu items, active promotions, and affinity rules.
  - [x] Design stateless interface `rerank_recommendations(cart_items, promotions, rules, menu, timestamp)`.
- [x] **Task 2: Implement Boost Calculations** (AC: 3, 4, 5)
  - [x] Implement time-of-day parser and category checker for `Time_Boost` (+0.15).
  - [x] Implement promotion parser and date/time validator for `Promo_Boost` (+0.20).
  - [x] Implement mathematical score calculation logic.
- [x] **Task 3: Implement Filtering & Deduplication** (AC: 2, 6)
  - [x] Filter out any candidate item already present in `cart_items`.
  - [x] Deduplicate candidates by keeping the highest score version when multiple rules point to the same item.
  - [x] Sort output in descending order.
- [x] **Task 4: Implement Unit Tests** (AC: 1-6)
  - [x] Create `test_recommender.py` covering unit test scenarios: base confidence only, promo boost only, time boost only, double-boost multiplication, cart exclusion, and duplicate resolution.

## Dev Notes

- **Architecture Compliance (AD-1)**: Reranking logic must be placed in a dedicated module `recommender.py` at the project root, keeping `main.py` clean as a driver layer.
- **Storage & Memory (AD-2)**: Mined rules (`affinity_rules.json`), menu (`menu.csv`), and promotions (`promotions.csv`) are loaded once from `_bmad-output/data/` and cached in-memory at startup. Pass these cached collections to the stateless rerank filter.
- **Consistency**: Timestamps in ISO 8601 format (e.g. `2026-07-06T12:30:00+07:00`).

### References

- [SPEC.md](file:///d:/Python/Projects/KFC/_bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md#L25-L27) (CAP-3)
- [ARCHITECTURE-SPINE.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md#L40-L44) (AD-1)
- [ARCHITECTURE-SPINE.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md#L55-L60) (AD-4)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- Mined association rules successfully matched against cart.
- Math boosts: Promo_Boost (+0.20) and Time_Boost (+0.15) applied multiplicatively.
- Cart exclusion verified.
- Unit tests run: 6 tests, all passed.

### Completion Notes List

- Created `recommender.py` containing stateless function `rerank_recommendations`.
- Implemented promotion date-matching and category-specific eligibility matching.
- Implemented lunch/dinner peak hours detection and category boosting.
- Implemented candidate filtering for items already in cart.
- Created `test_recommender.py` unit test suite and verified 100% correctness.

### File List

- `recommender.py`
- `test_recommender.py`

### Review Findings

- [x] [Review][Patch] Timezone-aware/naive comparison bug [recommender.py:25]
- [x] [Review][Patch] Missing promo hour validation [recommender.py:27]
- [x] [Review][Patch] Conflated & over-broad promotion matching [recommender.py:8]
- [x] [Review][Patch] Interface parameter naming mismatch [recommender.py:20]
- [x] [Review][Patch] Inefficient menu linear scans & DataFrame filters [recommender.py:67]
- [x] [Review][Patch] Date parsing optimization [recommender.py:31]
- [x] [Review][Patch] Fragile timezone parsing [recommender.py:22]
- [x] [Review][Patch] Missing None / parameter checks [recommender.py:20]
