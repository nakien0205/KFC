# KFC Kiosk Recommendation System

A local hackathon demo for a smarter KFC self-service kiosk.

The app recommends add-ons while a customer builds a cart. It uses synthetic order history, association rules, active promotions, time-of-day context, and lightweight feedback learning to rank recommendations. The top recommendation can also get AI-generated copy, but the app still works without any API key because it falls back to local template copy.

It now has two separate experiences: the original public kiosk at `/`, and an authenticated customer site at `/customer`. The customer site keeps its own order history and may issue one deterministic complementary offer after three completed orders; it does not change the kiosk's behaviour or data store.

This is a demo and simulation project. The benchmark uses generated synthetic orders, not real KFC sales data.

## What It Shows

- A kiosk-style web UI for adding menu items to a cart.
- Real-time recommendations from the current cart.
- Promotion-aware pricing and recommendation copy.
- A local SQLite data layer for menu, promotions, orders, and rules.
- A synthetic backtest that compares the hybrid recommender with a static baseline.
- A separate authenticated customer ordering site with Argon2id password hashes, opaque `HttpOnly` sessions, isolated customer data, and server-validated one-time offers.
- Safe fallback behavior when Gemini, OpenRouter, or Ollama is unavailable.

## Current Benchmark

The current local backtest reports:

- Benchmark mode: synthetic partial-cart top-3 recommendation panel
- Eligible transactions: 4,194 generated carts
- Baseline AOV: 83.136 VND
- Hybrid recommender AOV: 91.570 VND
- Estimated synthetic AOV uplift: +10.14%
- Conservative full-order top-1 check: +1.82%

These numbers are useful for judging the demo mechanics. They are not production sales proof.

The separate customer-personalization replay uses 500 deterministic synthetic personas, each with earlier purchase history and one later held-out order. Its latest run reports 118,908 VND general-hybrid AOV versus 136,692 VND customer-policy AOV: +17,784 VND or +14.96%. It measures the bundled customer policy—history-aware ranking plus a personal offer replacing the global promotion—not the effect of history alone. This is separate synthetic scenario evidence, not a result to add to the kiosk's 10.14% benchmark and not a claim about real customer sales.

## How It Works

```text
generate_data.py + promo_engine.py
  -> _bmad-output/data/menu.csv, promotions.csv, orders.csv
  -> affinity_engine.py
  -> _bmad-output/data/affinity_rules.json
  -> init_db.py
  -> _bmad-output/data/kiosk.db
  -> main.py + recommender.py
  -> static kiosk UI

customer_store.py + personalization.py
  -> _bmad-output/data/customer.db
  -> /customer authenticated ordering UI
```

Main pieces:

- `main.py` - FastAPI app and API routes.
- `recommender.py` - recommendation ranking, promotion handling, AI copy, and local fallback copy.
- `promo_engine.py` - dynamic promotion generation and urgency logic.
- `bandit.py` - feedback-based weight persistence.
- `generate_data.py` - synthetic menu, promotion, and order data generation.
- `affinity_engine.py` - association rule mining.
- `init_db.py` - SQLite database setup.
- `backtest.py` - synthetic AOV backtest.
- `customer_store.py` - isolated customer accounts, hashed sessions, orders, and one-time offers.
- `personalization.py` - customer-history ranking and deterministic complementary offers.
- `generate_customer_personas.py` and `personalization_backtest.py` - reproducible customer-personalization evidence.
- `static/` - plain HTML, CSS, and JavaScript kiosk UI.
- `tests/` - unittest coverage.

## Requirements

The repo does not pin an exact Python version. You need Python, pip, and the packages in `requirements.txt`.

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run The Demo

From the project root:

```powershell
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

Use the UI by adding menu items to the cart. The recommendation panel updates from the backend.

For the customer experience, open:

```text
http://127.0.0.1:8000/customer
```

Create an account, then sign in and use the protected ordering page. The first three completed orders use the customer route's global-signal cold-start fallback; later eligible carts can receive one deterministic complementary offer. Customer accounts and history are stored separately in `_bmad-output/data/customer.db`; rebuilding kiosk data does not delete them.

## Rebuild The Local Data

The repo includes generated demo data. To refresh it:

```powershell
python generate_data.py
python affinity_engine.py
python init_db.py
```

Run the synthetic benchmark:

```powershell
python backtest.py
```

Run the separate customer fixture and replay:

```powershell
python generate_customer_personas.py
python personalization_backtest.py
```

`init_db.py` rebuilds only kiosk data. To use another location for customer state, set `CUSTOMER_DB_PATH` before starting the app.

Run tests:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

## Optional AI Copy Setup

The app works without AI keys because it falls back to local copy.

Optional environment variables:

- `GEMINI_API_KEY` - use Gemini copy generation.
- `OPENROUTER_API_KEY` - use OpenRouter.
- `OPENROUTER_MODEL` - override the OpenRouter model. Default is `google/gemini-2.5-flash`.
- `USE_OLLAMA=true` - use local Ollama.
- `OLLAMA_HOST` - override Ollama host. Default is `http://localhost:11434`.
- `OLLAMA_MODEL` - override Ollama model. Default is `llama3.2:3b`.

Only the top recommendation uses external AI copy. Other recommendations use local fallback copy to keep the kiosk fast.

## API Quick Reference

Get menu items:

```text
GET /api/menu
```

Get recommendations:

```text
POST /api/recommend
```

Example PowerShell request:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/recommend `
  -ContentType "application/json" `
  -Body '{"cart_items":["Burger Zinger"],"timestamp":"2026-07-06T12:00:00Z"}'
```

Run benchmark through the API:

```text
POST /api/backtest
```

Send feedback for bandit learning:

```text
POST /api/recommend/feedback
```
