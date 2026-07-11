---
title: 'Task 1 Customer Offer and UI Correctness'
type: 'bugfix'
created: '2026-07-11'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'be17f7a24430ffe9f50aa08edbc3829a9b76ff95'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/guide.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-customer-personalization.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Customer recommendations currently let a client timestamp influence a server-issued personal-offer date, can leave several offers redeemable for one customer, omit global promotions during cold start, and display an offered item at its normal menu price. The customer menu also omits item images, and the declared dependencies omit NumPy.

**Approach:** Repair the customer-only offer lifecycle and ordering UI while preserving all kiosk contracts, promotion tiers, client-server price authority, and Task 2 replay/data scope.

## Boundaries & Constraints

**Always:** Keep `/api/recommend` and kiosk routes unchanged; retain 200/empty-list behavior for empty or invalid customer recommendation input; derive offer dates from trusted server UTC time; keep at most one redeemable personal offer per customer; make equivalent requests idempotent; use the existing global promotion-aware hybrid result during cold start without a personal offer; accept personal-offer redemption only for one target item at the server-issued sale price; keep generated copy English, promotion tiers at 5/10/15/20%, and all tests offline; preserve the user-owned `.gitignore`, `README.md`, and customer-personalization review ledger.

**Ask First:** Change kiosk APIs, kiosk promotion semantics, global generated-data contracts, benchmark/replay dates, persona artifacts, or any user-owned worktree change.

**Never:** Trust client prices or client dates for personal-offer creation; make more than one external copy call per recommendation; issue personal offers before three completed customer orders; change replay evidence or start Task 2/Task 3 work.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Future client timestamp | Authenticated mature customer sends a valid cart and future timestamp | Rank using the supplied timestamp as today, but derive any personal-offer date/id from server UTC date | The client cannot select a future discount tier |
| Repeated/changed offer context | Mature customer repeats an equivalent request, then changes eligible context | Equivalent request returns the same active offer; changed context leaves no stale parallel offer redeemable | Checkout rejects superseded offer IDs |
| Cold start | Customer has fewer than three completed orders | Return global hybrid candidates with active global promotion metadata and `cold_start: true` | No personal offer is persisted or returned |
| Cart offer state | Selected offer target is present exactly once | UI line item and total use its server-issued sale price | Target quantity above one or target removal clears the selected offer and restores menu pricing |
| Menu image | Menu item has/does not have `image` | Render image with item-specific alt text, or an accessible labelled fallback | Missing image never creates a broken image element |

</frozen-after-approval>

## Code Map

- `main.py` -- customer recommendation route, shared global promotions, and kiosk route boundary.
- `personalization.py` -- hybrid customer ranking, cold-start behavior, and deterministic offer construction.
- `customer_store.py` -- persisted offer lifecycle and authoritative checkout redemption.
- `static/customer/app.js` and `static/customer/customer.css` -- customer cart totals, offer selection validity, and menu cards.
- `tests/test_customer_api.py`, `tests/test_customer_store.py`, and a focused offline customer-UI test -- regression proof for customer-only contracts.
- `requirements.txt` -- direct runtime dependencies.

## Tasks & Acceptance

**Execution:**

- [x] `main.py` and `personalization.py` -- retain request validation and ranking timestamp behavior, but pass trusted UTC offer-date input separately; pass active global promotions through the cold-start hybrid path; ensure mature-only personal offers remain customer-only.
- [x] `customer_store.py` -- atomically persist one current redeemable offer per user: identical unredeemed offer IDs remain reusable (including after a context switches away and back), while a changed offer context invalidates other unredeemed offers before its return; preserve one-time checkout redemption.
- [x] `static/customer/app.js` and `static/customer/customer.css` -- retain normal menu cart state and server checkout payload, but calculate the targeted quantity-one line and displayed total from the selected offer sale price; validate selection after every cart mutation; render image or accessible fallback.
- [x] `requirements.txt` -- declare `numpy` directly.
- [x] `tests/` -- add offline regression coverage for future timestamp offer derivation, idempotency/supersession, cold-start global promotion metadata/no offer, client display effective price and invalidation, image fallback, and unchanged kiosk `/api/recommend` behavior.
- [x] `guide.md` -- implementation, tests, and code review passed; Task 1 is logged complete without changing Tasks 2–3.

**Acceptance Criteria:**

- Given the same mature customer, history, cart, and server date, when they request recommendations repeatedly, then exactly one active personal-offer row is redeemable and its returned offer is stable.
- Given a context change produces a different personal offer, when the prior offer ID is presented at checkout, then checkout rejects it without creating an order.
- Given a cold-start customer requests recommendations on an active global promotion date, when results are returned, then global promotion metadata is preserved and no personal offer exists.
- Given an offer is selected in the customer UI, when the target has quantity one, then its line and total display the offer sale price; when target quantity changes or is removed, then no offer ID is submitted.
- Given kiosk menu/recommendation endpoints and the complete suite run, then their existing behavior remains unchanged and all tests pass.

### Review Findings

- [x] [Review][Patch] Capture offer issue time only after the SQLite write lock is acquired [customer_store.py:310] -- avoids a midnight lock wait returning an already expired offer.
- [x] [Review][Patch] Hold a selected personal offer while its target remains redeemable and discard stale recommendation cards [static/customer/app.js:117] -- prevents a follow-up request from superseding the ID still shown in the cart.
- [x] [Review][Patch] Return a retryable conflict when a concurrent checkout changes the offer before it is persisted [main.py:471] -- prevents an unhandled store error becoming a 500 response.
- [x] [Review][Patch] Replace failed menu-image loads with the same accessible fallback used for missing image data [static/customer/app.js:63] -- prevents broken image elements.
- [x] [Review][Patch] Extend browser-script coverage for offer refresh holds, target removal, checkout payload invalidation, and image load failure [tests/test_customer_frontend.py:10].
- [x] [Review][Patch] Extend store coverage for switch-away-and-back offer reactivation and concurrent contexts [tests/test_customer_store.py:84].

## Suggested Review Order

**Customer offer boundary**

- The route separates trusted offer dates from client ranking context.
  [`main.py:447`](../../main.py#L447)

- Cold-start global promotions and mature personal offers remain distinct.
  [`personalization.py:206`](../../personalization.py#L206)

- A write lock enforces one current redeemable offer transactionally.
  [`customer_store.py:283`](../../customer_store.py#L283)

**Customer ordering experience**

- The browser holds one selected offer at its server-issued effective price.
  [`app.js:195`](../../static/customer/app.js#L195)

- Menu media has both absent-image and failed-load accessible fallbacks.
  [`app.js:75`](../../static/customer/app.js#L75)

**Verification and setup**

- API tests cover trusted dates, cold start, and retryable conflicts.
  [`test_customer_api.py:118`](../../tests/test_customer_api.py#L118)

- Store tests prove offer reactivation and concurrent single-offer behavior.
  [`test_customer_store.py:84`](../../tests/test_customer_store.py#L84)

- The offline browser harness exercises prices, invalidation, and image recovery.
  [`test_customer_frontend.py:13`](../../tests/test_customer_frontend.py#L13)

- NumPy is now declared as a direct generator dependency.
  [`requirements.txt:8`](../../requirements.txt#L8)

## Design Notes

The request timestamp is still the ranking context because the existing API contract depends on it; only personal-offer derivation must use a server-owned UTC date. Offer replacement belongs in the store transaction so concurrent requests cannot leave multiple unredeemed IDs; an unredeemed deterministic ID may be reactivated when its context becomes current again, but a redeemed ID never may. The browser may display the issued sale price but never transmits it, leaving `customer_store.py` as the checkout authority. Global promotions returned for cold start are descriptive results from the shared hybrid path, not personal offer IDs and must never be persisted or sent as checkout offers.

## Verification

**Commands:**

- `python -m unittest tests.test_customer_api tests.test_customer_store` -- expected: focused customer API/store offer and cold-start regressions pass offline.
- `python -m unittest discover -s tests -p "test_*.py"` -- expected: all customer and kiosk tests pass with no API-contract regression.
- `python -m unittest tests.test_main` -- expected: existing kiosk `/api/recommend` tests remain green.
- Required `bmad-code-review` workflow -- expected: no unresolved high, medium, or low findings in the Task 1 diff.
