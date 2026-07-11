# Customer Personalization: Next-Session Guide

## Purpose

This guide records the remaining work after the customer-personalization feature was implemented in commit `a57dfad`. Do **not** restart the feature or continue the old monolithic task. Complete exactly one task below per new Codex session, in order.

## Current State

- The customer site, authentication, separate `customer.db`, checkout history, personalized recommendations, personal offers, persona generator, and replay already exist.
- `python -m unittest discover -s tests -p "test_*.py"` passed **76 tests** on 2026-07-11.
- The feature is **not ready for final sign-off**. The current review ledger in `_bmad-output/implementation-artifacts/spec-customer-personalization.md` contains seven evidence-backed unresolved findings.
- Do not treat the current `13.46%` synthetic personalization uplift as valid evidence until Task 2 regenerates and reruns the replay.
- Preserve the existing user-owned worktree changes: `.gitignore`, `README.md`, and the review ledger itself. Do not reset, discard, or overwrite them.

## Task 1 — Fix Customer Offer and UI Correctness

### Goal

Close the two customer-runtime review findings and the dependency gap without changing kiosk behavior.

### Required changes

1. In the customer recommendation API, retain the existing empty/invalid-input behavior, but derive the browser-issued personal offer date from trusted server UTC time rather than the request timestamp.
2. Keep only one current redeemable personal offer per customer. Repeated requests for the same context must be idempotent; a changed context must not leave parallel stale offers redeemable.
3. For customers with fewer than three completed orders, use the existing global promotion-aware hybrid result. Do not issue a personal offer during cold start.
4. In `static/customer/app.js`, calculate cart and displayed total from the effective personal-offer price when the target quantity is exactly one. Clear the selected offer whenever the cart no longer satisfies redemption rules.
5. Render the existing menu image on the customer ordering page, with accessible alt text and a safe fallback when no image is present.
6. Add the direct `numpy` requirement required by `generate_data.py`.

### Tests and acceptance

- Add offline tests for a future client timestamp, one active redeemable offer, cold-start global promotion metadata, effective checkout/displayed price, and offer invalidation after cart changes.
- Run focused customer tests, then `python -m unittest discover -s tests -p "test_*.py"`.
- Confirm kiosk routes and `/api/recommend` stay unchanged.

### Stop condition

Commit Task 1 separately only after the full suite passes. Do not modify benchmark dates or generated persona data in this task.

## Task 2 — Repair Replay Fairness and Evidence

### Goal

Make the synthetic AOV comparison exercise the promotion behavior it claims to compare.

### Required changes

1. Generate each deterministic persona hold-out on a controlled active date from the 2026 promotion calendar. Generate that persona's 8–24 history orders strictly before its hold-out date.
2. Ensure the replay uses the hold-out timestamp for both strategies, never puts a hold-out into customer history, and records nonzero promotion-calendar coverage.
3. Enforce the same recommendation panel range for both strategies: accept only panel sizes `1` through `5`.
4. Regenerate the persona fixture and replay report only after generator and replay tests pass.

### Tests and acceptance

- Prove fixture byte determinism, strictly earlier histories, active-promotion hold-out coverage, no hold-out leakage, panel-size rejection above five, and stable effective-sale-price calculations.
- Run the required data chain:

```powershell
python generate_data.py
python affinity_engine.py
python init_db.py
python backtest.py
python generate_customer_personas.py
python personalization_backtest.py
python -m unittest discover -s tests -p "test_*.py"
```

- Record the fresh replay as **synthetic scenario evidence**, never as real customer-sales proof.

### Stop condition

Commit Task 2 separately only when the kiosk benchmark and the refreshed personalization replay are reproducible.

## Task 3 — Update Docs and Finalize Review

### Goal

Make the repaired feature runnable and reviewable by another developer.

### Required changes

1. Update `docs/index.md` and any relevant operating documentation with the customer routes, separate database behavior, `CUSTOMER_DB_PATH`, exact generation/replay order, and the synthetic-evidence limitation.
2. Mark review findings resolved only when their corresponding code and tests exist. Do not mark the feature done before this step.
3. Review source, UI, tests, fixture schema, and replay output. Do not inspect all 76,503 generated JSON lines; validate its generator, schema, deterministic hash, and report instead.
4. Keep generated persona-fixture tracking unchanged during these three tasks. Treat any decision to stop tracking the bulk JSON as a separate repository-hygiene task.

### Final acceptance

- No unresolved high, medium, or low review findings remain.
- Fresh full regression passes.
- Kiosk benchmark behavior is unchanged.
- Customer documentation is sufficient for a fresh local setup and clearly labels replay results as synthetic.

## Next Session Prompt

Use this prompt verbatim in the next session:

> Read `AGENTS.md`, `guide.md`, and `_bmad-output/implementation-artifacts/spec-customer-personalization.md`. Implement **Task 1 only** from `guide.md`. Preserve the user-owned `.gitignore`, `README.md`, and review ledger; do not begin Task 2 or Task 3. Run the stated tests and report exact evidence.
