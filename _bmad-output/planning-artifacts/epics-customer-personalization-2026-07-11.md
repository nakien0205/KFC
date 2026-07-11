---
status: implemented
source: _bmad-output/implementation-artifacts/spec-customer-personalization.md
---

# Customer Personalization Extension

This additive roadmap preserves the completed kiosk epics and introduces a separate authenticated customer route family.

## Epic 1: Secure Customer Ordering

- Customer landing, registration, login, logout, and protected customer app.
- Isolated customer SQLite store with Argon2id password hashes, opaque hashed sessions, and atomic server-priced checkout history.

## Epic 2: History-Powered Recommendations and Offers

- Customer-only recommendation endpoint combines global affinity with completed personal orders after the three-order cold-start threshold.
- A deterministic complementary offer uses the existing 5/10/15/20% tiers, excludes cart items, and returns the effective sale price.

## Epic 3: Personalization Evidence

- Deterministic repeat-customer persona fixture keeps history strictly before one hold-out order.
- Independent top-three replay compares general hybrid and personalized AOV without changing the established kiosk benchmark.

## Verification

- Customer tests use `CUSTOMER_DB_PATH` temporary databases.
- Customer fixture/replay files stay separate from global `orders.csv`, `kiosk.db`, and `backtest.py` inputs.
