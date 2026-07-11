---
title: 'Customer Recommendation Actions and AOV Simulation'
type: 'feature'
created: '2026-07-12'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'e2b5d873e8e7fcfe91c29ea4737ab73ca7cc1f68'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-customer-personalization.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The authenticated customer page shows recommendations but only personal-offer recommendations can be added directly. It also does not expose the existing customer-personalization AOV replay, making the separate customer evidence difficult to inspect from the customer experience.

**Approach:** Make every customer recommendation actionable with an Add button and expose a read-only endpoint and panel for the existing deterministic customer-personalization AOV replay. Present the values as synthetic scenario evidence, separate from the kiosk benchmark and real customer orders.

## Boundaries & Constraints

**Always:** Preserve kiosk routes and UI; retain server-derived cart pricing, cart exclusion, personal-offer validation, and one-time redemption; authenticate the customer AOV endpoint; use the existing `run_personalization_backtest` logic rather than a new metric; keep the replay and customer history/database isolated; show VND prices and the synthetic-evidence disclaimer in English; make generic recommendations add one menu-priced cart item, and make the personal-offer button continue to apply its issued effective price. If a global-promotion recommendation displays a sale price that customer checkout cannot redeem, label its action clearly as adding at the menu price.

**Ask First:** Change the replay methodology, publish results as real-sales evidence, alter kiosk metrics, alter customer checkout or offer-redemption rules, persist simulation results, or rebuild/change either SQLite database.

**Never:** Read customer orders as the replay fixture, write to `customer.db` or `kiosk.db` when a customer views the simulation, add payment behavior, trust client prices or offer details, or combine the customer uplift with the kiosk uplift.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Authenticated simulation view | Signed-in customer opens the customer app | A customer-only endpoint returns general AOV, personalized AOV, absolute change, uplift, eligible count, panel size, and evidence metadata from the fixed persona replay | A failed replay returns a clear server error; the UI keeps ordering usable and shows an unavailable state |
| Anonymous simulation request | No valid customer session | The endpoint returns 401 and exposes no benchmark response | The UI redirects to login through its existing auth handling |
| Generic recommendation | Customer clicks Add on a non-offer recommendation | Exactly one matching menu item enters the cart at its normal server-validated price; recommendations refresh | Missing menu item is ignored safely |
| Personal offer recommendation | Customer clicks Add on a personal-offer recommendation | The issued offer target enters once at its effective price and the reserved offer behavior remains intact | Invalid offer data is ignored; checkout remains the authority for redemption |

</frozen-after-approval>

## Code Map

- `personalization_backtest.py` -- deterministic, fixture-based customer AOV replay and response metrics; it must remain separate from runtime customer history.
- `main.py` -- customer authentication, recommendation endpoint, static route family, and Pydantic response schemas.
- `static/customer/app.html` -- authenticated customer page layout; will host the clearly labelled AOV evidence panel.
- `static/customer/app.js` -- customer cart, offer state, recommendation rendering, API calls, and stale-response protection.
- `static/customer/customer.css` -- customer-page-specific styling.

## Tasks & Acceptance

**Execution:**

- [x] `main.py` -- add an authenticated, read-only customer AOV simulation response model and endpoint that calls the current deterministic personalization replay without an output path, exposes only required metrics/metadata, and handles replay failure without touching either database.
- [x] `static/customer/app.html` and `static/customer/customer.css` -- add a compact customer-side AOV evidence section that distinguishes the general-hybrid and personalized-policy AOVs, displays uplift, and states that it is synthetic scenario evidence rather than customer-sales proof.
- [x] `static/customer/app.js` -- load the simulation after session validation, render loading/error states without blocking ordering, and add an Add button to every non-personal-offer recommendation. Reuse `add()` for generic candidates; preserve `applyPersonalOffer()` as the only route that reserves an offer and applies a sale price. Label a global-promotion candidate's generic Add action with its actual menu price instead of implying customer checkout will honour its displayed sale price.

**Acceptance Criteria:**

- Given a signed-in user opens `/customer/app`, when the replay is available, then they see the separate customer benchmark values and a synthetic-evidence disclaimer without seeing or changing any real account history.
- Given the replay fails, when the customer page loads, then menu, cart, recommendations, and checkout remain usable while the evidence section reports that the simulation is unavailable.
- Given a generic recommendation is rendered, when the customer selects Add, then it appears in the cart once at the server's menu price and a new recommendation request is queued.
- Given a personal-offer recommendation is rendered, when the customer selects its offer action, then the existing one-time offer rules and effective-price behavior still apply.

## Spec Change Log

## Design Notes

The endpoint is intentionally server-side and authenticated because it prevents the UI from directly opening fixture files while keeping data access patterns consistent. The underlying replay already uses synthetic personas and the kiosk catalog/rules; calling it without `output_path` makes the view read-only and avoids regenerating its JSON report.

The customer page must not claim that the AOV values describe the signed-in user or their actual order history. A concise label such as “Synthetic customer-policy replay” is preferred over a sales-oriented label.

## Verification

**Manual checks (user requested no automated testing):**

- Start the app and open `/customer/app` as an authenticated user -- expected: the synthetic AOV section loads, or shows an isolated unavailable message, while the menu and checkout remain usable.
- Click Add on a normal recommendation and on a personal offer -- expected: the normal item uses its menu price; the offer preserves its issued price and checkout contract.

## Suggested Review Order

**Replay boundary and evidence integrity**

- Authenticate access and run the existing replay against the app's live catalog cache.
  [`main.py:451`](../../main.py#L451)

- Shape the replay response without exposing fixture contents or filesystem details.
  [`main.py:374`](../../main.py#L374)

- Guard the UI against non-synthetic or hold-out-leaking evidence before displaying it.
  [`app.js:205`](../../static/customer/app.js#L205)

**Customer-facing AOV panel**

- Keep loading and failure states isolated from the ordering workflow.
  [`app.html:40`](../../static/customer/app.html#L40)

- Load the evidence only after customer session validation succeeds.
  [`app.js:387`](../../static/customer/app.js#L387)

- Stack the metrics before the customer shell becomes too narrow.
  [`customer.css:111`](../../static/customer/customer.css#L111)

**Recommendation actions and pricing clarity**

- Reuse the existing cart mutation while preserving the personal-offer-only redemption path.
  [`app.js:252`](../../static/customer/app.js#L252)

- Disclose the real menu price when global-promotion checkout cannot redeem the shown sale price.
  [`app.js:266`](../../static/customer/app.js#L266)
