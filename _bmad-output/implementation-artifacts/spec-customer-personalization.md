---
title: 'Customer Personalization Extension'
type: 'feature'
created: '2026-07-11'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'e8ba6b5c79c0dacb2dd1b37cafdaa71db2c2fc24'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/_bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md'
  - '{project-root}/_bmad-output/planning-artifacts/epics-sqlite-layer-2026-07-08.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The project only serves an anonymous kiosk, so it cannot retain a customer's orders or tailor recommendations and discounts to that customer. Its synthetic AOV evidence also cannot isolate the added value of logged-in personalization.

**Approach:** Add a separate authenticated customer experience at `/customer` while leaving the kiosk unchanged at `/`. Store customer accounts and completed orders in an independent SQLite database, add customer-only ranking and one complementary offer, then validate it with deterministic repeat-customer personas and an independent replay benchmark.

## Boundaries & Constraints

**Always:** Preserve kiosk pages and APIs; keep customer state out of `kiosk.db` and `init_db.py`; hash passwords with Argon2id; persist only hashes of opaque, expiring session tokens; rotate the session on successful login; use `HttpOnly` and `SameSite=Lax` cookies; retain English customer copy, cart exclusion, one external copy call, and 5/10/15/20% discount tiers with a 20% maximum; keep all tests offline; leave the user's `.gitignore`, `README.md`, and `data/` changes untouched.

**Ask First:** Alter any existing kiosk API response, kiosk promotion behavior, generated global data contract, or the user-owned worktree changes.

**Never:** Add payment processing, real customer data, plaintext/reversible passwords, client-trusted prices or user IDs, customer data to the kiosk rebuild database, or the judge-only AOV simulator to the customer UI. Do not claim a personalization uplift before a fresh replay produces it.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|---------------------------|----------------|
| Registration | Valid new email and password | Create a hashed account in `customer.db` | Duplicate or invalid input returns a client error and creates nothing |
| Authenticated ordering | Valid session and non-empty cart | Server validates menu items/prices and atomically saves an order | Invalid/empty cart or expired session writes nothing |
| Customer recommendation | Valid cart and at least 3 prior orders | Return personalized, cart-safe candidates plus at most one personal offer | New users use the general hybrid result with a cold-start reason |
| Empty or invalid recommendation input | Empty cart or invalid timestamp | Match the kiosk with HTTP 200 and an empty list | No copy call or offer is created |
| Personal offer | Same user/history/cart/date | Deterministic complementary offer with effective price | No eligible candidate produces no offer |
| Replay benchmark | Fixed persona artifact and seed | Compare general hybrid versus personalized top-three AOV | Hold-out rows are never read as history |

</frozen-after-approval>

## Code Map

- `main.py` -- FastAPI lifecycle, kiosk routes, and shared in-memory catalog/rule cache.
- `recommender.py` and `promo_engine.py` -- stable global ranking and tiered promotion primitives to reuse without changing kiosk behavior.
- `static/` -- kiosk assets; new customer assets must be isolated beneath `static/customer/`.
- `backtest.py` and `generate_data.py` -- established global benchmark/data contracts that must remain independent.
- `tests/test_main.py` and existing unittest suite -- kiosk regression baseline and API test conventions.

## Tasks & Acceptance

**Execution:**

- [x] `customer_store.py` -- create the configurable, idempotent `customer.db` store for users, hashed sessions, orders, and order items; rotate sessions on login, validate catalog items and quantities, and calculate checkout totals server-side in one transaction.
- [x] `personalization.py` -- derive a completed-order history profile; combine it with the stable global candidates; emit cart-safe personalized reasons and one deterministic complementary offer using the existing discount primitive.
- [x] `main.py` -- initialize the independent store and add customer pages plus registration, login, logout, session, order-history, checkout, and session-aware recommendation endpoints without changing kiosk handlers.
- [x] `static/customer/` -- add landing, combined registration/login, and protected ordering assets; reuse shared catalog/images, call customer APIs, render cold-start/personalization/offer states, and omit the backtest UI.
- [x] `generate_customer_personas.py` and `personalization_backtest.py` -- generate 500 deterministic persona sequences (8–24 history orders and one later hold-out) outside runtime credentials, and replay general versus personalized top-three AOV with effective offer prices.
- [x] `requirements.txt`, `tests/`, `AGENTS.md`, `docs/index.md`, and a new customer-personalization planning artifact -- declare the password dependency, add offline coverage for session expiry, cross-user access, concurrent checkout, invalid quantities, cart/timestamp edges, and hold-out leakage; document local commands, `CUSTOMER_DB_PATH`, and data separation; preserve the completed kiosk roadmap.

**Acceptance Criteria:**

- Given the kiosk is opened at `/`, when its menu, recommendation, feedback, and backtest paths are used, then their responses and UI behavior remain unchanged.
- Given a registered customer logs in, when they access `/customer/app`, then only their authenticated session can save or read their orders; logout and session expiry revoke that access.
- Given a customer has at least three completed orders, when their cart changes, then their recommendations use only completed personal history plus global context, never recommend cart items, and return one deterministic tiered offer at most.
- Given the customer has fewer than three completed orders, when they request recommendations, then the general hybrid path remains usable and clearly reports cold start.
- Given the persona generator and personalization replay run repeatedly with the same seed, when their outputs are compared, then histories, hold-out boundaries, metrics, and effective-sale-price arithmetic are deterministic.

## Design Notes

Customer ranking begins with the existing `rerank_recommendations` result so global affinity, timestamp handling, and cart exclusion stay consistent. A customer-only profile adds deterministic frequency, recency, and historical co-purchase signals; it cannot access another user's data or the held-out replay event. The personal offer replaces the kiosk calendar promotion on the customer site, targets the highest eligible complementary candidate, and derives its tier from a stable hash of the user, canonical history, cart, candidate, and normalized request date. `customer.db` defaults to `_bmad-output/data/customer.db` but is overridden by `CUSTOMER_DB_PATH` in tests and deployments.

## Verification

**Commands:**

- `python generate_data.py; python affinity_engine.py; python init_db.py; python backtest.py` -- existing global data and benchmark complete without changed kiosk semantics.
- `python generate_customer_personas.py; python personalization_backtest.py` -- deterministic customer fixture and separate personalization metrics are produced.
- `python -m unittest discover -s tests -p "test_*.py"` -- customer coverage and all kiosk regressions pass without network calls or production customer writes.

## Suggested Review Order

**Customer API boundary**

- Customer-only routes protect the kiosk contract while attaching server-controlled sessions.
  [`main.py:442`](../../main.py#L442)

- Registration sets opaque, secure browser-session attributes without exposing credentials.
  [`main.py:188`](../../main.py#L188)

**Independent account and order state**

- The separate schema stores only password and session hashes, orders, and issued offers.
  [`customer_store.py:283`](../../customer_store.py#L283)

- Checkout validates catalog facts, redeems an offer once, and commits the order atomically.
  [`customer_store.py:401`](../../customer_store.py#L401)

**History-powered customer behavior**

- Personal ranking fixes bandit inputs and replaces kiosk calendar sales with a complementary offer.
  [`personalization.py:197`](../../personalization.py#L197)

- The offer identifier and discount tier remain stable for the same user, history, cart, and date.
  [`personalization.py:156`](../../personalization.py#L156)

**Customer UI and evidence**

- Versioned requests prevent a slow recommendation response from overwriting a newer cart.
  [`static/customer/app.js:105`](../../static/customer/app.js#L105)

- Checkout sends only a server-issued offer identifier; it never supplies a discounted price.
  [`static/customer/app.js:172`](../../static/customer/app.js#L172)

- Deterministic personas and strict held-out replay provide the synthetic AOV evidence.
  [`generate_customer_personas.py:77`](../../generate_customer_personas.py#L77)

- Replay records fixture identity, panel size, timestamp policy, and promotion treatment.
  [`personalization_backtest.py:101`](../../personalization_backtest.py#L101)

**Regression coverage**

- API tests cover session protection, cross-user isolation, deterministic offers, and single redemption.
  [`tests/test_customer_api.py:11`](../../tests/test_customer_api.py#L11)

- Replay tests cover determinism, chronological hold-out separation, panel validation, and effective prices.
  [`tests/test_customer_personas.py:28`](../../tests/test_customer_personas.py#L28)

### Review Findings

- [x] [Review][Patch] Server-issued personal offers use a client-controlled date, so an authenticated customer can request future dates until a 20% tier appears [main.py:449] — derive the offer date from trusted server time and prevent parallel active offers for the same eligible context. **Severity: high.**
- [x] [Review][Patch] The personalization replay's 2025 hold-outs never overlap the 2026 promotion calendar, so its published general-hybrid comparison does not exercise the promotion condition it labels [generate_customer_personas.py:88] — align the deterministic evaluation dates with a controlled promotion calendar before reporting uplift. **Severity: high.**
- [x] [Review][Patch] Cold-start results omit active global promotions instead of using the promised general-hybrid fallback [personalization.py:223] — pass the active global promotions during cold start, while keeping personal offers unavailable until three completed orders. **Severity: medium.**
- [x] [Review][Patch] Applying a personal offer leaves the cart and total at menu price, and raising the offered item's quantity leaves an invalid offer ID selected [static/customer/app.js:64] — model the active offer's effective price in cart state and clear it when the cart no longer satisfies one-target-item redemption. **Severity: medium.**
- [x] [Review][Patch] Replay accepts panel sizes above the general reranker's five-result limit, comparing unequal-sized panels [personalization_backtest.py:112] — reject values above five or parameterize both ranking paths with the same limit. **Severity: medium.**
- [x] [Review][Patch] The customer ordering UI does not render the shared menu images required by the feature spec [static/customer/app.js:49] — render each menu item's existing image field with an accessible fallback. **Severity: low.**
- [x] [Review][Patch] Dependency setup adds Argon2 but still omits the direct numpy requirement [requirements.txt:1] — declare numpy explicitly as required by the project contract. **Severity: low.**

## Finalization Evidence (2026-07-11)

All findings have been thoroughly verified and resolved. The complete rebuild, verification, and regression tests have been executed successfully:

### Command & Verification Results

1. **Global Kiosk Benchmark (`backtest.py`):**
   - Percentage AOV Uplift: **+10.14%** (Baseline AOV: 83.136 VND, Recommender AOV: 91.570 VND)
2. **Customer Personalization Replay (`personalization_backtest.py`):**
   - Eligible Repeat-Customer Count: **500**
   - General Hybrid AOV: **118,908.00 VND**
   - Personalized AOV: **136,692.00 VND**
   - Absolute change: **+17,784.00 VND**
   - Percentage uplift: **+14.96%** (Synthetic scenario evidence only; not real customer-sales proof)
   - Active promotion coverage: **1.0** (100% of the replay personas evaluated on active 2026 calendar dates)
3. **Unit Tests Run:**
   - Command: `python -m unittest discover -s tests -p "test_*.py"`
   - Result: **85 tests passed** (OK)

### Fixture & Report Verification

- **Customer Persona Fixture (`_bmad-output/data/customer_personas.json`):**
  - Deterministic SHA-256: `68f6612f94f4aecbfec35f55f3e5bf3c9e8d898ec73c79260a7f86afdabe7802`
- **Replay Report (`_bmad-output/data/personalization_backtest.json`):**
  - Match SHA-256 fixture verification: `68f6612f94f4aecbfec35f55f3e5bf3c9e8d898ec73c79260a7f86afdabe7802`

### Code Paths & Test Reference Map

- **Server offer date and parallel offer safety:**
  - Code: `main.py` calling `_customer_offer_date()`, which uses server UTC date.
  - Code: `customer_store.py`'s `issue_personal_offer` transaction automatically updates and expires existing unredeemed/active offers for the user.
  - Tests: `tests/test_customer_store.py` (`test_only_current_unredeemed_personal_offer_can_be_redeemed`, `test_concurrent_offer_contexts_leave_only_one_active_offer`), `tests/test_customer_api.py` (future timestamp coverage).
- **Promotion Calendar coverage in Replay:**
  - Code: `generate_customer_personas.py` choosing holdout dates strictly from `_controlled_promotion_dates(resolved_calendar)`.
  - Tests: `tests/test_customer_personas.py` (`test_personas_are_deterministic_and_holdout_is_on_active_2026_calendar_date`).
- **Cold start promotion behavior:**
  - Code: `personalization.py`'s cold-start branch checks history and fetches active global promotions.
  - Tests: `tests/test_personalization.py` and `tests/test_customer_api.py` (cold-start validation).
- **Frontend offer calculation & invalidation:**
  - Code: `static/customer/app.js` (`effectiveItemPrice()`, `validateActiveOffer()`, `checkoutPayload()`).
  - Tests: `tests/test_customer_frontend.py` (offline browser-script test harness).
- **Replay panel size enforcement:**
  - Code: `personalization_backtest.py` bounds checks and asserts `1 <= panel_size <= MAX_PANEL_SIZE`.
  - Tests: `tests/test_customer_personas.py` (asserts panel sizes 1 and 5 are valid, while other inputs raise `ValueError`).
- **UI menu images rendering and fallback:**
  - Code: `static/customer/app.js` (`menuImage()` and img `error` event handlers).
  - Tests: `tests/test_customer_frontend.py` (image rendering and fallback DOM tests).
- **Numpy dependency:**
  - Code: `requirements.txt` direct declaration (`numpy`).
  - Docs: Updated in `AGENTS.md` and `docs/index.md`.

