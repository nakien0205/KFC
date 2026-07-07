---
baseline_commit: 0c73971bbed139e82ed7b68124b6ec545a88f65a
---

# Story 3.2: Interactive Cart, Menu Selection, and API Integration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a kiosk customer,
I want to click on menu items to add them to my cart, view my current cart list, and have recommendations update automatically,
so that my ordering session is fully interactive and personalized to my selections.

## Acceptance Criteria

1. **Dynamic Menu Rendering**: Given a list of menu items from `menu.csv` loaded by the backend, when the kiosk page loads, the menu items must be fetched from the backend API and rendered dynamically as double-bezel cards in the menu grid (replacing any hardcoded mock items).
2. **Add to Cart Interaction**: When a user clicks a menu item card's "Thêm" button, the item is added to the active cart, and the cart list in the sidebar updates immediately showing item name, price, quantity, and a remove button.
3. **Cart State Management**: The cart must support adding duplicate items (incrementing quantity), removing items (decrementing quantity or full removal), and recalculating subtotal/total on every state change. Prices formatted in VND using Geist Mono.
4. **API Recommendation Trigger**: On every cart state change (item added or removed), `static/app.js` must trigger a `POST /api/recommend` request with the current cart item names and active ISO 8601 timestamp.
5. **Loading States**: The UI must handle loading states smoothly while waiting for the recommendation API response — show a subtle loading indicator in the recommendation panel and disable rapid re-fetching (debounce).
6. **Recommendation Panel Update**: When the API response arrives, render recommendation tiles in the bento grid panel with item name, price (VND), copy, and rationale. Recommendation cards must use existing double-bezel and bento-tile CSS classes.
7. **Category Filtering**: Sidebar category navigation links must filter displayed menu items by category when clicked, using the category data from the menu API.

## Tasks / Subtasks

- [x] **Task 1: Add `/api/menu` endpoint to FastAPI backend** (AC: 1)
  - [x] Add a `GET /api/menu` endpoint in `main.py` that returns the in-memory `MENU_ITEMS_DF` as a JSON array of `{name, category, price}` objects.
  - [x] Add unit test for the new endpoint in `test_main.py`.

- [x] **Task 2: Create `static/app.js` — Cart state module and menu fetch** (AC: 1, 2, 3)
  - [x] Create `static/app.js` with a cart state object (array of `{name, price, quantity}` items).
  - [x] On `DOMContentLoaded`, fetch `GET /api/menu` and dynamically render menu cards into `#menu-items-container` using the same double-bezel HTML structure from `index.html`.
  - [x] Implement `addToCart(name, price)` — adds item or increments quantity, then calls `renderCart()` and `fetchRecommendations()`.
  - [x] Implement `removeFromCart(name)` — decrements quantity or removes item, then calls `renderCart()` and `fetchRecommendations()`.
  - [x] Implement `renderCart()` — updates `#cart-items-list` with cart item rows (name, qty, price, remove button), recalculates subtotal/total into `#cart-subtotal` and `#cart-total`, toggles checkout button disabled state.

- [x] **Task 3: Implement recommendation API integration with debounce** (AC: 4, 5, 6)
  - [x] Implement `fetchRecommendations()` — `POST /api/recommend` with `{cart_items: [...names], timestamp: new Date().toISOString()}`. Debounce 300ms to prevent rapid fire.
  - [x] Show a loading indicator in `#recommendation-bento-panel` while waiting.
  - [x] On response, render recommendation tiles into `#recommendation-bento-panel` using existing bento-tile + double-bezel CSS. Each tile shows: badge, price (VND), item name, copy, rationale, and an "add to cart" mini button.
  - [x] Handle empty cart state (clear recommendations, show empty message).
  - [x] Handle API error gracefully (show fallback message, don't crash).

- [x] **Task 4: Implement category filtering** (AC: 7)
  - [x] Attach click handlers to `.category-item` sidebar links.
  - [x] On click, filter displayed menu cards by matching `data-category` attribute. The "active" category gets the `.active` class.
  - [x] Add "Tất cả" (All) category as first option to show all items.

- [x] **Task 5: Update `index.html` to load `app.js` and clean up mock data** (AC: 1, 6)
  - [x] Add `<script src="/static/app.js"></script>` before closing `</body>` tag.
  - [x] Remove all hardcoded mock menu cards from `#menu-items-container`.
  - [x] Remove all hardcoded mock recommendation tiles from `#recommendation-bento-panel`.
  - [x] Keep the cart empty state message as default.

- [x] **Task 6: Add CSS for new dynamic elements** (AC: 2, 3, 5)
  - [x] Add `.cart-item-row` styles (flex row: name, qty badge, price, remove button).
  - [x] Add `.loading-indicator` styles (subtle pulsing animation).
  - [x] Add `.recommendation-empty` styles for empty/loading states.
  - [x] Add slide-up/fade-in entry animation classes for dynamically inserted cards (UX-DR7).

### Review Findings

- [x] [Review][Patch] getCartItemNames sends duplicate names for qty>1 items [static/app.js:37]
- [x] [Review][Defer] Pydantic field name "copy" shadows BaseModel attribute [main.py:118] — deferred, pre-existing
- [x] [Review][Defer] Sync requests block FastAPI thread in recommender [main.py:123] — deferred, pre-existing
- [x] [Review][Defer] Menu card fixed height may clip long item names [static/style.css:196] — deferred, pre-existing

## Dev Notes

- **Architecture (AD-6)**: All frontend JS must live in `static/`. Backend in project root.
- **Architecture (AD-5)**: Backend exposes `POST /api/recommend` accepting `{cart_items, timestamp}`. No `/api/menu` endpoint exists yet — must be added.
- **Architecture (AD-1)**: `main.py` is a driver only. Don't put processing logic in the endpoint — just serialize and return cached data.
- **Existing Code State**:
  - `main.py` already caches `MENU_ITEMS_DF` (pandas DataFrame with columns `name`, `category`, `price`) in global memory at startup.
  - `main.py` already has `POST /api/recommend` working with `RecommendRequest(cart_items, timestamp)` and returns `RecommendationResponse(name, price, score, copy, rationale)`.
  - `static/index.html` has hardcoded mock menu cards and one mock recommendation tile — both must be removed and rendered dynamically via JS.
  - `static/style.css` has all needed CSS classes: `.double-bezel`, `.card-inner`, `.menu-card`, `.btn-pill`, `.icon-circle`, `.bento-tile`, `.tile-header`, `.badge`, `.tile-item-title`, `.tile-copy`, `.tile-footer`, `.tile-rationale`, `.add-to-cart-btn-mini`, `.empty-cart-message`, `.cart-items-list`, `.price-mono`, `.price-text`.
  - No `app.js` exists yet (deferred from 3-1 review finding).
- **Price Formatting**: VND prices use dot separator: `format_price_vnd(179000) → "179.000"`. Append `đ` suffix. Use Geist Mono font for all prices.
- **Menu CSV Structure**: `_bmad-output/data/menu.csv` has columns: `item_id, name, category, price`. Categories include: `Combos`, `Burgers`, `Sides`, `Desserts`, `Drinks`.
- **Naming Conventions**: Python = `snake_case`, JavaScript = `camelCase`, API routes = `/api/` prefix.
- **Timestamps**: ISO 8601 format. JS: `new Date().toISOString()`.
- **Testing Pattern**: Existing tests use `unittest` + `FastAPI TestClient` with `setUp/tearDown` context manager pattern (see `test_main.py`).
- **DO NOT** use any third-party JS libraries — vanilla JS only.
- **DO NOT** create new CSS files — extend `static/style.css`.
- **DO NOT** modify recommendation logic in `recommender.py`.

### Previous Story Intelligence (3-1)

- Story 3-1 established the complete CSS design system in `style.css` with all tokens, double-bezel, pill buttons, haptic animations.
- Review findings from 3-1 noted "Frontend HTML contains no interactive JS file" — this story resolves that.
- FastAPI `StaticFiles` mount at `/static` and root `/` serving `index.html` already configured.
- Sidebar categories already exist in HTML with `data-category` attributes: `Combos`, `Burgers`, `Sides`, `Desserts`, `Drinks`.

### Project Structure Notes

- New file: `static/app.js`
- Modified files: `main.py` (add `/api/menu`), `static/index.html` (add script tag, remove mocks), `static/style.css` (add cart/loading styles), `test_main.py` (add menu endpoint test)

### References

- [ARCHITECTURE-SPINE.md AD-5](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md#L62-L67) — API interfaces
- [ARCHITECTURE-SPINE.md AD-6](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md#L69-L72) — Directory structure
- [epics.md Story 3.2](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/epics.md#L197-L209) — Story requirements
- [epics.md UX-DR7](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/epics.md#L58) — Smooth layout transitions

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (Thinking)

### Debug Log References

- All 24 tests pass (8 test_main + 16 test_recommender). Zero regressions.
- `GET /api/menu` returns 200 with 92 menu items.
- `GET /static/app.js` returns 200 with `application/javascript` content-type.
- `GET /` returns 200 with HTML including `app.js` script tag.

### Completion Notes List

- Added `GET /api/menu` endpoint to `main.py` — returns cached `MENU_ITEMS_DF` as JSON array of `{name, category, price}` objects.
- Created `static/app.js` — IIFE module with cart state management (add/remove/quantity), menu fetch from `/api/menu`, dynamic card rendering using existing double-bezel CSS, recommendation API integration with 300ms debounce, loading indicator, category filtering with "Tất cả" (All) option, and slide-up/fade-in entry animations.
- Updated `static/index.html` — removed all hardcoded mock menu cards and recommendation tiles, added `<script src="/static/app.js">` before `</body>`.
- Extended `static/style.css` — added `.cart-item-row`, `.cart-remove-btn`, `.loading-indicator`, `.loading-pulse`, `.recommendation-empty`, and `@keyframes cardEnter` / `.card-enter` animation classes.
- Added 2 new tests in `test_main.py`: `test_menu_endpoint_returns_200` and `test_menu_endpoint_structure`.

### Change Log

- Story 3-2 implementation complete — interactive cart, dynamic menu, API recommendation integration (Date: 2026-07-06)

### File List

- `static/app.js` (NEW)
- `main.py` (MODIFIED — added `/api/menu` endpoint)
- `static/index.html` (MODIFIED — removed mocks, added script tag)
- `static/style.css` (MODIFIED — added cart/loading/animation styles)
- `test_main.py` (MODIFIED — added menu endpoint tests)
- `requirements.txt` (NEW)
