---
id: SPEC-kfc-kiosk-recommender
companions:
  - stack.md
  - ../../planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# KFC Kiosk Recommendation System Spec

## Why

Winning a hackathon requires demonstrating a high-uplift recommendation system without real sales data or integration with a physical restaurant kiosk. The challenge is to build a hybrid recommendation engine that balances speed, explainability, and personalization, and to provide a backtest simulator that mathematically proves a simulated Average Order Value (AOV) uplift.

## Capabilities

- **CAP-1**
  - **intent:** System generates structured synthetic dataset (menu catalog, promo calendar, and historical orders with built-in combos and item co-occurrence rules) to train the recommender.
  - **success:** Generates a CSV containing at least 1,000 orders with verifiable associations (e.g. burger orders containing fries/drinks above 50% frequency).
- **CAP-2**
  - **intent:** Offline affinity engine runs association rule mining over the synthetic order history to output item affinity confidence and lift metrics.
  - **success:** Outputs a queryable SQLite database or JSON structure containing mined rule associations (e.g., "burger -> fries" with confidence and lift scores).
- **CAP-3**
  - **intent:** Online context reranker filters and adjusts affinity scores in real-time based on active cart contents, active promos, and time of day.
  - **success:** API endpoint accepts current cart, promo calendar, and timestamp, returning a sorted list of context-adjusted item recommendations.
- **CAP-4**
  - **intent:** GenAI layer takes top reranked items and current context to generate personalized on-screen recommendation copy and rationale.
  - **success:** LLM generates localized promotional copy (e.g., "Add fries for 15,000đ!") and a brief explanation ("recommended because 68% of customers add fries") under 1.5 seconds response time.
- **CAP-5**
  - **intent:** Kiosk UI simulates an interactive ordering screen showing cart building, menu, and a dynamic recommendation panel updating live after each cart change.
  - **success:** Single-page frontend visualizes menu item selection, cart updates, and shows updated GenAI-customized recommendation text and rationale.
- **CAP-6**
  - **intent:** Backtest harness replays synthetic historical orders through both static recommendations and the hybrid pipeline to calculate simulated AOV difference.
  - **success:** Harness runs simulation and produces a final report showing percentage change and absolute AOV difference between static and hybrid models.

## Constraints

- 3-day hackathon timeline for building backend, frontend, and backtest harness.
- Must run fully locally with simple local deployment.
- GenAI calls limited to 1 call per recommendation request (low latency and low cost).
- No physical POS or kiosk hardware integration required.

## Non-goals

- Real-time customer profile database (no login, signup, or user tracking).
- Multi-restaurant support (limited to a single mock KFC menu).
- Real payment processing or checkout integration.

## Success signal

- A functional mock kiosk simulator showing updated recommendations in real-time as items are added, alongside a backtest run that outputs a simulated AOV uplift percentage for the pitch.
