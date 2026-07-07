# Tech Stack and Architecture Companion

This document details the tech stack, library choices, and architectural pipeline structure for the KFC Kiosk Recommendation System.

## Stack Overview
- **Language:** Python (FastAPI backend) for logic and API, JavaScript for frontend.
- **ML / Analysis:** `pandas` and `mlxtend` (for Apriori or FP-Growth association rule mining).
- **Database:** `SQLite` (local file database, no setup required).
- **Frontend:** Single-page modern HTML/JS/CSS (using modern layout, clean typography, gradients, and micro-animations to create a premium feel).
- **LLM API:** Google Gemini API (or Anthropic API) for late-stage personalized copy generation.

## 3-Day Development Plan
- **Day 1: Data & Proof (Core Engines)**
  - Synthetic dataset generator (`generate_data.py`).
  - Association rule mining model (`affinity_engine.py`).
  - Backtest harness (`backtest.py`) comparing static suggestions vs. affinity recommendations.
- **Day 2: API & GenAI Layer (Backend integration)**
  - FastAPI server (`app.py`).
  - Online reranker logic.
  - LLM integration.
- **Day 3: Kiosk UI & Presentation**
  - Frontend kiosk simulator interface.
  - Integration with FastAPI.
  - Visual Polish and preparation for pitch deck.
