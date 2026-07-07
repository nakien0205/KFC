---
title: 'Generate Synthetic Dataset and Affinity Mining Engine'
type: 'feature'
created: '2026-07-05T17:45:00'
status: 'completed'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The KFC Kiosk Recommendation System has no real POS/sales transaction data to train recommendation models or run backtest simulations, preventing development of the item-affinity engine.

**Approach:** Create a synthetic data generator script that produces a realistic menu catalog, promotional calendar, and historical orders containing built-in item associations. Then, build an association mining engine that processes the orders to produce item affinity confidence and lift metrics.

## Boundaries & Constraints

**Always:**
- Generate menu categories: Burgers, Sides, Drinks, Desserts, Combos.
- Historical orders must contain at least 1,000 transactions with custom co-occurrence patterns (e.g., burger orders must co-occur with fries and/or drinks with a >60% probability to ensure Apriori mines strong rules).
- Outputs must be clean CSV files saved in a dedicated data directory (`_bmad-output/data/`).
- The affinity mining engine must use mlxtend or custom association rules to find frequent itemsets and association rules.
- Write clean, documented Python files.

**Ask First:**
- Customizing the menu items list or categories.
- Changing dataset size beyond 1,000 orders.

**Never:**
- Hardcode association rule output (rules must be mined from the generated CSV).
- Use external database engines (keep to raw files or SQLite).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Generate Data | Command run | Creates menu catalog, promo calendar, and historical orders CSV files | Output error if folder not writeable |
| Mine Affinity | Generated historical orders CSV | Finds frequent itemsets and rules; saves them to `affinity_rules.json` | Handle cases where support threshold is too high and no rules are found (fallback to lower support) |

</frozen-after-approval>

## Code Map

- `generate_data.py` -- Generates synthetic menu, promotions, and historical orders.
- `affinity_engine.py` -- Mines association rules from orders and outputs rule confidence metrics.

## Tasks & Acceptance

**Execution:**
- [x] `generate_data.py` -- Implement synthetic data generation -- Create a realistic POS simulator that outputs menu catalog (items, categories, prices), active promotions, and 1,000+ transaction orders with designed item associations.
- [x] `affinity_engine.py` -- Implement association rule mining engine -- Load the transactions, run association rule mining (using mlxtend Apriori/Association Rules, or custom FP-Growth), and output the rules to a queryable format (e.g. JSON or SQLite).

**Acceptance Criteria:**
- Given no prior data, when `generate_data.py` is run, then it creates `menu.csv`, `promotions.csv`, and `orders.csv` containing at least 1,000 orders with realistic combo/co-occurrence patterns.
- Given the generated `orders.csv`, when `affinity_engine.py` is run, then it successfully mines at least 5 strong association rules (e.g., Burger -> Fries with support > 0.05 and confidence > 0.50) and saves them to `affinity_rules.json`.

## Design Notes

For association mining, we'll use `mlxtend.frequent_patterns.apriori` and `mlxtend.frequent_patterns.association_rules`.
We need to format the transactional data: group by transaction ID and one-hot encode items.
The synthetic orders generator can use a probabilistic model where:
- 40% of orders are Burgers. If a Burger is selected, there is a 70% chance of adding French Fries (Side) and a 65% chance of adding Pepsi (Drink).
- 20% of orders are Fried Chicken. If Fried Chicken is selected, there is an 80% chance of adding Pepsi (Drink).
- 15% of orders are Desserts alone (e.g., Ice Cream).
- 25% of orders are random mixtures.

## Verification

**Commands:**
- `uv run generate_data.py` -- expected: creates CSV files with >1,000 orders.
- `uv run affinity_engine.py` -- expected: mines rules successfully and writes `affinity_rules.json`.
