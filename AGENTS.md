# AGENTS.md

These instructions apply to the whole repository.

## Working Style

- Do not agree with a claim unless it is universally true or supported by evidence in this repo.
- Use plain, simple terms.
- Say "I do not know" when there is not enough evidence.
- When the user proposes an approach, judge whether it is the best fit for the current situation. If it is not, explain the better approach.
- If the current session is no longer efficient for the next task, tell the user to start a new session.

## Project Summary

This repo is a local KFC kiosk recommendation demo. It is a small monolith:

- FastAPI backend in `main.py`.
- Recommendation and copy logic in `recommender.py`.
- Bandit weight persistence in `bandit.py`.
- Synthetic data generation in `generate_data.py`.
- Association rule mining in `affinity_engine.py`.
- Backtest simulation in `backtest.py`.
- Static frontend in `static/`.
- Generated demo data in `_bmad-output/data/`.

The main architecture is a pipes-and-filters flow:

`generate_data.py` -> `_bmad-output/data/*.csv` -> `affinity_engine.py` -> `_bmad-output/data/affinity_rules.json` -> `recommender.py` -> `main.py` API -> `static/` UI.

## Commands

Use these from the repo root:

```powershell
python generate_data.py
python affinity_engine.py
python backtest.py
python -m unittest discover -s tests -p "test_*.py"
uvicorn main:app --reload
```

The app serves the UI at `/` and static assets from `/static`.

## Data Contracts

- `main.py` loads runtime data from `_bmad-output/data/menu.csv`, `_bmad-output/data/promotions.csv`, and `_bmad-output/data/affinity_rules.json` during FastAPI lifespan startup.
- `menu.csv` must include `name`, `category`, and `price`. If `image` exists, `/api/menu` includes it.
- `orders.csv` must include `order_id` and `item_name`.
- `affinity_rules.json` is a list of rule objects with `antecedents`, `consequents`, `support`, `confidence`, and `lift`.
- Root `affinity_rules.json` and `_bmad-output/data/affinity_rules.json` can both be written by `affinity_engine.py`; keep them consistent if changing mining behavior.

## Implementation Rules

- Preserve the API behavior that empty carts, missing timestamps, and invalid timestamps return HTTP 200 with an empty list from `/api/recommend`.
- Never recommend an item already in the cart.
- Keep recommendation copy resilient: external LLM calls must fall back to `generate_local_fallback`.
- Keep the current one-external-call rule for `/api/recommend`: only the top candidate gets generated copy; remaining candidates use local fallback.
- Keep generated customer-facing copy and rationales in Vietnamese unless the product requirement changes.
- Keep prices formatted as VND with dot separators through `format_price_vnd`.
- Do not let tests make real network calls. Mock `requests.post` for Gemini, OpenRouter, and Ollama paths.
- Do not let tests write production bandit weights. Patch `bandit.WEIGHTS_PATH` or pass a temp path.
- `bandit.py` uses `threading.RLock` and atomic `os.replace` writes. Preserve that race-safety when editing persistence.
- If changing recommendation scoring, update `tests/test_recommender.py` and run the full unittest suite.
- If changing synthetic data, menu parsing, or affinity mining, run `python generate_data.py`, `python affinity_engine.py`, and the tests.
- If changing API response shapes, update `tests/test_main.py`, the static frontend, and this file.
- `generate_data.py` imports `numpy`, but `requirements.txt` does not currently list it directly. Add it if you touch dependency setup.
- SQLite is described as a future/deferred direction in project docs, but the current runtime uses CSV and JSON files. Do not introduce a database unless the user asks for it.

## Frontend Rules

- The frontend is plain HTML/CSS/JavaScript under `static/`; there is no package manager or build step.
- Keep API calls aligned with `main.py`: `/api/menu`, `/api/recommend`, `/api/backtest`, and `/api/recommend/feedback`.
- Do not move image assets or rename menu item images unless you also update generated menu data and frontend references.

## Reference

- Start future repo orientation from `docs/index.md`.
- The canonical product spec is `_bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md`.
- The stack companion is `_bmad-output/specs/spec-kfc-kiosk-recommender/stack.md`.
