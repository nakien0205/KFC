# Project Documentation Index

Generated: 2026-07-11

## Project Overview

- **Project:** KFC RAG system / KFC kiosk recommendation demo
- **Type:** Monolith with FastAPI backend and static frontend
- **Primary languages:** Python, JavaScript, HTML, CSS
- **Architecture:** Pipes-and-filters recommendation pipeline
- **Runtime data:** Relational local SQLite database (`_bmad-output/data/kiosk.db`) populated from generated CSV and JSON files
- **Primary agent guide:** [AGENTS.md](../AGENTS.md)

## Quick Reference

- **Backend entry point:** [`main.py`](../main.py)
- **Frontend entry point:** [`static/index.html`](../static/index.html)
- **Recommendation engine:** [`recommender.py`](../recommender.py)
- **Promotion engine:** [`promo_engine.py`](../promo_engine.py)
- **Bandit persistence:** [`bandit.py`](../bandit.py)
- **Synthetic data generator:** [`generate_data.py`](../generate_data.py)
- **Affinity miner:** [`affinity_engine.py`](../affinity_engine.py)
- **Backtest harness:** [`backtest.py`](../backtest.py)
- **Customer store:** [`customer_store.py`](../customer_store.py) - Isolated accounts, sessions, and completed orders.
- **Customer personalization:** [`personalization.py`](../personalization.py) - History-aware ranking and complementary offers; issued offers are server-validated and redeemable once.
- **Persona generator and replay:** [`generate_customer_personas.py`](../generate_customer_personas.py), [`personalization_backtest.py`](../personalization_backtest.py)
- **Tests:** [`test_main.py`](../tests/test_main.py), [`test_recommender.py`](../tests/test_recommender.py), [`test_promo_engine.py`](../tests/test_promo_engine.py), [`test_bandit.py`](../tests/test_bandit.py), [`test_backtest.py`](../tests/test_backtest.py)

## Generated Documentation

- [Agent Implementation Guide](../AGENTS.md)
- [Project Overview](./project-overview.md) _(To be generated)_
- [Architecture](./architecture.md) _(To be generated)_
- [Source Tree Analysis](./source-tree-analysis.md) _(To be generated)_
- [Development Guide](./development-guide.md) _(To be generated)_

## Existing Documentation

- [Hackathon Submission](../hackathon_submission.md) - Narrative product and architecture summary.
- [Canonical Spec](../_bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md) - Product capabilities, constraints, and success signal.
- [Stack Companion](../_bmad-output/specs/spec-kfc-kiosk-recommender/stack.md) - Technology and architecture companion.
- [Sprint Status](../_bmad-output/implementation-artifacts/sprint-status.yaml) - BMAD implementation status artifact.
- [Deferred Work](../_bmad-output/implementation-artifacts/deferred-work.md) - Known follow-up work.

## Source Tree

```text
KFC/
|-- main.py                         # FastAPI app and API routes
|-- recommender.py                  # Reranking and LLM/local copy generation
|-- promo_engine.py                 # Dynamic daily promotions, discount framing, urgency math
|-- bandit.py                       # Thompson-sampling weight storage
|-- generate_data.py                # Synthetic menu, promotion, and order data
|-- affinity_engine.py              # Association rule mining
|-- init_db.py                      # SQLite database initialization
|-- backtest.py                     # AOV uplift simulation
|-- customer_store.py               # Customer accounts, sessions, and order history
|-- personalization.py              # Customer-only ranking and personal offer logic
|-- generate_customer_personas.py   # Deterministic repeat-customer fixture generator
|-- personalization_backtest.py     # General versus personal synthetic AOV replay
|-- static/                         # Plain frontend assets and served images
|-- _bmad-output/data/              # SQLite DB and source CSV/JSON files
|-- _bmad-output/specs/             # Product spec and stack context
|-- _bmad-output/implementation-artifacts/
|-- docs/                           # Documentation index and future docs
|-- tests/                          # unittest coverage and integration tests
```

## Getting Started

Install dependencies in the active Python environment:

```powershell
pip install -r requirements.txt
```

### Complete Rebuild & Replay Flow

To reproduce the entire data generation, mining, initialization, kiosk benchmarking, customer persona generation, and customer replay benchmark, run the following commands in this exact order:

```powershell
python generate_data.py
python affinity_engine.py
python init_db.py
python backtest.py
python generate_customer_personas.py
python personalization_backtest.py
python -m unittest discover -s tests -p "test_*.py"
```

### Kiosk Benchmark vs. Customer Replay

1. **Global Kiosk Benchmark (`backtest.py`)**:
   - Evaluates general hybrid recommender performance on global historical orders.
   - Operates on the SQLite database `_bmad-output/data/kiosk.db`.

2. **Customer Personalization Replay (`personalization_backtest.py`)**:
   - Replays 500 deterministic repeat-customer personas to evaluate personalization against the general hybrid recommender.
   - **Crucial Warning:** The customer personalization replay results are **synthetic scenario evidence** only and must *never* be interpreted as real customer-sales proof.
   - **Replay Metrics (Latest Fresh Run):**
     - Eligible customer count: 500
     - General hybrid AOV: 118,908.00 VND
     - Personalized AOV: 136,692.00 VND
     - Absolute change: +17,784.00 VND
     - Percentage uplift: +14.96%

---

## Customer Personalization Experience

The customer-personalization feature extends the kiosk with user authentication, custom order histories, and personal offers.

### Customer Route Family

- **Static Pages:**
  - `GET /customer` — Customer portal landing page
  - `GET /customer/login` — Combined login and registration page
  - `GET /customer/app` — Protected customer ordering workspace (requires active authenticated session)

- **API Endpoints:**
  - `POST /api/customer/register` — Create a new customer account
  - `POST /api/customer/login` — Authenticate and start a new session (cookie-based)
  - `POST /api/customer/logout` — Terminate current session
  - `GET /api/customer/session` — Retrieve profile of the currently logged-in customer
  - `GET /api/customer/orders` — List completed orders for the authenticated customer
  - `POST /api/customer/checkout` — Save a new order and invalidate/redeem any active offer
  - `POST /api/customer/recommend` — Fetch personalized recommendations and deterministic personal offers

### Customer Database (`customer.db`)

- **State Isolation:** All customer state (accounts, sessions, order histories, issued offers) is stored in a separate SQLite database.
- **Default Path:** `_bmad-output/data/customer.db`
- **Override Path:** Set the `CUSTOMER_DB_PATH` environment variable.
- **Initialization:** Created and initialized automatically at startup. The global kiosk build script `init_db.py` **never** creates, modifies, or rebuilds the customer database.
- **Testing:** Unit tests must configure a temporary `CUSTOMER_DB_PATH` override (e.g. using a temporary directory) to avoid writing to the production database.

---

## Notes For Future Agents

- Read [AGENTS.md](../AGENTS.md) before changing code.
- NumPy is explicitly declared in `requirements.txt`.
- Treat `_bmad-output/data/` as runtime data, not throwaway scratch files.
- Preserve local fallback behavior for all LLM paths.
- Dynamic promotions keep required fields plus optional targeting fields; accepted promoted recommendations use sale price in backtest AOV math.

