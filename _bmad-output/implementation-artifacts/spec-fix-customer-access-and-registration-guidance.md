---
title: 'Add Reciprocal Kiosk and Customer Navigation'
type: 'feature'
created: '2026-07-11'
status: 'done'
route: 'plan-code-review'
review_loop_iteration: 0
baseline_commit: 'cc4c82f5b63112dda9d492bde7f10a0de79c112f'
context:
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The kiosk and customer experiences are separate routes, but visitors cannot directly switch from the kiosk to the customer site or from every customer page back to the kiosk.

**Approach:** Add accessible semantic navigation anchors between the existing routes, reusing the established page styling and leaving all APIs, authentication, customer data, and kiosk behaviour untouched.

## Boundaries & Constraints

**Always:** Keep the kiosk at `/` and the customer route family at `/customer`; use anchors for navigation; keep all copy in English; preserve the current page layouts and responsive styles; preserve every existing uncommitted change; do not commit.

**Ask First:** Change routes, API responses, authentication/session behaviour, recommendation behaviour, data, or any existing user-owned worktree change.

**Never:** Add a router, database work, login/registration changes, JavaScript click interception for navigation, or the kiosk backtest modal to the customer site.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|---------------------------|----------------|
| Kiosk visitor | Opens `/` | Can select Customer site and follow an anchor to `/customer` | Normal browser navigation |
| Customer visitor | Opens landing, login, or signed-in app page | Can select Kiosk demo and follow an anchor to `/` | Normal browser navigation |
| Customer app session | Authenticated at `/customer/app` | Kiosk link works without logging out or changing the session | Session remains customer-only |

</frozen-after-approval>

## Code Map

- `static/index.html` and `static/style.css` -- kiosk header and its existing visual system.
- `static/customer/index.html` -- customer landing-page navigation.
- `static/customer/login.html` -- already has the kiosk link; retain it.
- `static/customer/app.html` and `static/customer/customer.css` -- authenticated customer header and action layout.
- `tests/test_customer_api.py` -- page-serving regression coverage.

## Tasks & Acceptance

**Execution:**

- [x] `static/index.html` and `static/style.css` -- add a visible Customer site anchor in the kiosk header, styled with the existing design system and outside category navigation.
- [x] `static/customer/index.html` -- add a visible Kiosk demo anchor in the landing-page header.
- [x] `static/customer/app.html` -- add a visible Kiosk demo anchor next to account actions; retain the existing logout control and session behaviour.
- [x] `tests/test_customer_api.py` -- verify the kiosk, customer landing, login, and authenticated customer app serve the expected reciprocal links.

**Acceptance Criteria:**

- Given a kiosk visitor, when they select Customer site, then the browser navigates to `/customer` without kiosk JavaScript preventing it.
- Given a customer visitor on the landing, login, or authenticated app page, when they select Kiosk demo, then the browser navigates to `/`.
- Given an authenticated customer selects Kiosk demo, when they return to `/customer/app`, then their existing valid customer session still grants access.
- Given existing kiosk and customer API tests run, when navigation is added, then no route, authentication, or recommendation contract changes.

## Verification

**Commands:**

- `python -m unittest tests.test_customer_api -v` -- expected: reciprocal links, page protection, and registration regression coverage pass.
- `python -m unittest discover -s tests -p "test_*.py"` -- expected: complete kiosk and customer suite passes.

**Manual checks:**

- Start `uvicorn main:app --reload`; open `/`, `/customer`, `/customer/login`, and `/customer/app` while signed in; confirm all visible route switches work.

## Suggested Review Order

**Kiosk entry point**

- Keeps customer navigation outside the kiosk category links intercepted by JavaScript.
  [`index.html:66`](../../static/index.html#L66)

- Reuses the kiosk action treatment while allowing its narrow header to wrap cleanly.
  [`style.css:133`](../../static/style.css#L133)

**Customer return paths**

- Adds the public kiosk switch without changing landing-page sign-in behaviour.
  [`customer/index.html:10`](../../static/customer/index.html#L10)

- Keeps the signed-in session intact while exposing the public kiosk route.
  [`customer/app.html:10`](../../static/customer/app.html#L10)

**Regression coverage**

- Proves every served page contains its expected reciprocal route anchor.
  [`test_customer_api.py:48`](../../tests/test_customer_api.py#L48)
