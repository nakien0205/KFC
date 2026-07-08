# Project Documentation Index

Generated: 2026-07-07

## Project Overview

- **Project:** KFC RAG system / KFC kiosk recommendation demo
- **Type:** Monolith with FastAPI backend and static frontend
- **Primary languages:** Python, JavaScript, HTML, CSS
- **Architecture:** Pipes-and-filters recommendation pipeline
- **Runtime data:** Local CSV and JSON files under `_bmad-output/data/`
- **Primary agent guide:** [AGENTS.md](../AGENTS.md)

## Quick Reference

- **Backend entry point:** [`main.py`](../main.py)
- **Frontend entry point:** [`static/index.html`](../static/index.html)
- **Recommendation engine:** [`recommender.py`](../recommender.py)
- **Bandit persistence:** [`bandit.py`](../bandit.py)
- **Synthetic data generator:** [`generate_data.py`](../generate_data.py)
- **Affinity miner:** [`affinity_engine.py`](../affinity_engine.py)
- **Backtest harness:** [`backtest.py`](../backtest.py)
- **Tests:** [`test_main.py`](../test_main.py), [`test_recommender.py`](../test_recommender.py), [`test_bandit.py`](../test_bandit.py), [`test_backtest.py`](../test_backtest.py)

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
|-- bandit.py                       # Thompson-sampling weight storage
|-- generate_data.py                # Synthetic menu, promotion, and order data
|-- affinity_engine.py              # Association rule mining
|-- backtest.py                     # AOV uplift simulation
|-- static/                         # Plain frontend assets
|-- images/                         # Menu image assets
|-- _bmad-output/data/              # Generated runtime CSV/JSON files
|-- _bmad-output/specs/             # Product spec and stack context
|-- _bmad-output/implementation-artifacts/
|-- docs/                           # Documentation index and future docs
`-- test_*.py                       # unittest coverage
```

## Getting Started

Install dependencies in the active Python environment:

```powershell
pip install -r requirements.txt
```

Generate or refresh local data:

```powershell
python generate_data.py
python affinity_engine.py
```

Run tests:

```powershell
python -m unittest discover -p "test_*.py"
```

Run the app:

```powershell
uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000/`.

## Notes For Future Agents

- Read [AGENTS.md](../AGENTS.md) before changing code.
- Do not assume the dependency manifest is complete; `generate_data.py` imports `numpy`, but `requirements.txt` currently omits it.
- Treat `_bmad-output/data/` as runtime data, not throwaway scratch files.
- Preserve local fallback behavior for all LLM paths.
