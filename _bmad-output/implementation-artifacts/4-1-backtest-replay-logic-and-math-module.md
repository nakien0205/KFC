---
baseline_commit: 0c73971bbed139e82ed7b68124b6ec545a88f65a
---

# Story 4.1: Backtest Replay Logic and Math Module

Status: done

## Story

As a business analyst,
I want to execute an offline simulation script that replays historical transactions through different recommendation pipelines,
so that I can mathematically prove the AOV (Average Order Value) uplift of the hybrid model over a static recommendation model.

## Acceptance Criteria

1. **Transaction Replay**: Given `orders.csv` (historical orders) and mined `affinity_rules.json`, when the script is executed, it must replay transactions one-by-one to simulate checkout totals under two recommendation models: Baseline and Hybrid (FR10).
2. **Baseline Model**: Recommends a static default item (e.g. "Pepsi"). Simulated customer accepts it based on its baseline support (overall frequency of "Pepsi" in order history).
3. **Hybrid Model**: Recommends the top context-reranked item. Simulated customer accepts it based on a dynamic probability: $P(\text{Accept}) = \text{Confidence} \times (1 + \text{Promo\_Boost}) \times (1 + \text{Time\_Boost})$. If no association rule matches the current cart, it falls back to the baseline support of that recommended item.
4. **Scoring Alignment**: The hybrid model's probability calculation must align with Story 2.1: `Promo_Boost` is `+0.20` if the item is in an active promotion; `Time_Boost` is `+0.15` if the timestamp matches the target category time (e.g. lunch/dinner).
5. **Uplift Calculation**: Calculate and report: Baseline AOV, Hybrid AOV, absolute change (VND), and percentage uplift (e.g. "+12.4%").

## Tasks / Subtasks

- [x] **Task 1: Create `backtest.py` replay harness structure** (AC: 1)
- [x] **Task 2: Implement support/probability math module** (AC: 2, 3, 4)
- [x] **Task 3: Implement replayer loop for all orders** (AC: 1, 2, 3)
- [x] **Task 4: Calculate final AOV, absolute and percentage metrics** (AC: 5)
- [x] **Task 5: Add CLI entry point and verify command runs** (AC: 1, 5)

### Review Findings

- [x] [Review][Patch] ZeroDivisionError on empty orders list [backtest.py:161-172]
- [x] [Review][Patch] Datetime parsing crash in promotion filtering [backtest.py:82-97]
- [x] [Review][Patch] AttributeError when menu category is float NaN [backtest.py:127-133]
- [x] [Review][Patch] Fallback probability uses context boosts instead of raw support [backtest.py:127-133]
- [x] [Review][Patch] Print prices in standard Vietnamese currency format [backtest.py:177-183]

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Completion Notes List

- Implemented offline simulation replay harness in `backtest.py`.
- Developed support/probability math module based on rules, active promotions, and time boosts.
- Added replayer loop simulating baseline and hybrid models for all transactions.
- Output baseline/hybrid AOV, absolute uplift, and percentage uplift.
- Added unit tests in `test_backtest.py` to verify simulation results.

### File List

- `backtest.py`
- `test_backtest.py`

## Dev Notes

- The script must load data from `_bmad-output/data/orders.csv`, `_bmad-output/data/menu.csv`, `_bmad-output/data/promotions.csv`, and `_bmad-output/data/affinity_rules.json`.
- The default item to recommend is Pepsi. The baseline support of Pepsi is its occurrence count in `orders.csv` divided by the total number of orders.
- Since this runs in an offline/simulation mode, we simulate customer choice. If the simulated customer accepts the recommendation, we add its price to the transaction.
- Hybrid recommendation logic should reuse the reranker logic from `recommender.py` if possible.
