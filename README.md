# KFC Kiosk Recommendation System

A local hackathon demo for a smarter KFC self-service kiosk.

The app recommends add-ons while a customer builds a cart. It uses synthetic order history, association rules, active promotions, time-of-day context, and lightweight feedback learning to rank recommendations. The top recommendation can also get AI-generated copy, but the app still works without any API key because it falls back to local template copy.

This is a demo and simulation project. The benchmark uses generated synthetic orders, not real KFC sales data.

## What It Shows

- A kiosk-style web UI for adding menu items to a cart.
- Real-time recommendations from the current cart.
- Promotion-aware pricing and recommendation copy.
- A local SQLite data layer for menu, promotions, orders, and rules.
- A synthetic backtest that compares the hybrid recommender with a static baseline.
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
