# KFC Kiosk Recommendation System - Technical Pitch Draft

## 30-Second Technical Summary

This project is a hybrid recommendation engine for a KFC self-service kiosk. It combines offline association-rule mining, dynamic daily promotions, context-aware reranking, a lightweight Thompson Sampling bandit, and AI-generated English recommendation copy with a local fallback. It also includes a separate authenticated customer ordering experience whose personal-history signal comes only from that customer's completed orders.

The goal is simple: when a customer adds food to the cart, the kiosk should recommend useful add-ons without suggesting items already in the cart, without freezing if an AI API is slow, and without needing a heavy production database for the demo.

The current benchmark is a synthetic scenario benchmark, not real production sales proof. In a fixed-seed partial-cart replay over 4,194 eligible generated carts, the hybrid top-3 recommendation panel estimates a 10.14% Average Order Value uplift, about +8,433 VND per eligible transaction, compared with a static Pepsi baseline. A sensitivity check shows that a larger panel can lift the synthetic result further, but I keep top-3 as the default because four or five recommendations can become noisy for a kiosk user.

The customer extension is deliberately separate from the kiosk. At `/customer`, a signed-in user receives a global-signal cold-start fallback with fixed reproducible customer-route weights, then recommendations that combine the current cart, global affinity, and that customer's own completed-order history. An eligible cart may receive one deterministic complementary offer after three completed orders. Its 500-persona replay produced a separate 14.96% synthetic customer-policy uplift (+17,784 VND; 118,908 VND general-hybrid AOV to 136,692 VND customer-policy AOV). That is a controlled synthetic scenario result, not real customer-sales proof and not a number to add to the kiosk benchmark.

## System Flow

The system follows a pipes-and-filters structure:

```text
generate_data.py
  -> _bmad-output/data/orders.csv, menu.csv, promotions.csv
  -> affinity_engine.py
  -> _bmad-output/data/affinity_rules.json
  -> recommender.py
  -> main.py FastAPI endpoints
  -> static kiosk UI
```

The offline part generates or loads menu data, creates synthetic order baskets, creates a controlled daily promotion calendar, and mines item associations. The online part receives the cart, finds candidate recommendations, applies context boosts, adds customer-facing copy, and returns the result to the kiosk UI.

The customer branch uses a separate SQLite database. Passwords are Argon2id hashes; browser sessions are opaque server-side records delivered in `HttpOnly`, `SameSite=Lax` cookies. Customer checkout derives prices and identity on the server, and an issued offer can be redeemed only once for its target item. This keeps customer state out of the rebuildable kiosk database.

## Dynamic Promotions

The promo engine creates deterministic daily sale rows instead of relying only on a static promo list. It uses a Gaussian-style day weighting where Monday and Sunday are stronger sale days, while mid-week is weaker. It also uses item popularity from generated orders, so promoted products are selected from products that actually appear in the synthetic basket history.

Generated discount percentages are limited to 5%, 10%, 15%, or 20%, with 20% as the max. For higher-value products, the system can frame the same discount as an amount-off message, for example "Save 50.000 VND", when that is clearer than a percentage.

## Recommendation Logic

The first layer is association-rule mining. The project uses Apriori through `mlxtend` to find item relationships from synthetic order baskets. Each rule has antecedents, consequents, support, confidence, and lift.

At request time, the recommender checks the active cart against those rules. If a cart item matches a rule antecedent, the consequent becomes a recommendation candidate. The system filters out anything already in the cart.

If no useful association rule applies, the system uses a rule-based fallback so the kiosk can still return reasonable suggestions.

## Context-Aware Reranking

The reranker adjusts the base association score using promotions and time of day:

```text
score = base_confidence * (1 + promo_boost) * (1 + time_boost) * (1 + urgency_boost)
```

Promotion boosts apply when the recommended item matches an active promotion. Time boosts apply during lunch and dinner windows for categories that fit those periods, such as burgers, combos, or sides. Urgency boosts apply only when a matching sale is close to ending.

This is useful because a kiosk should not treat every recommendation the same. A burger add-on at lunch and a bucket add-on at dinner may deserve different ranking behavior.

## Bandit Learning

Instead of hardcoding context boosts forever, the project uses a simple Thompson Sampling bandit.

It keeps Beta distribution parameters for promotion and time-based contexts:

```text
promo: alpha_promo, beta_promo
time:  alpha_time, beta_time
```

When feedback says a recommendation was accepted, the matching context alpha increases. When it was rejected, beta increases. The conservative full-order simulation samples from those distributions to balance exploration and exploitation; the headline partial-cart benchmark uses fixed expected boosts so the held-out panel result stays deterministic.

This is intentionally lightweight. It fits the kiosk demo because it can learn from feedback without requiring a large ML serving stack.

## AI Copy and Fallbacks

The recommendation is not only an item name. The system also returns English copy and a short rationale.

The primary path calls Gemini 2.5 Flash for structured JSON copy. There is also local Ollama support. If the AI route fails, times out, or is unavailable, the system immediately falls back to local template copy.

This matters for kiosk reliability. A real kiosk cannot freeze because a network API is slow. The recommendation engine must still return something usable.

The FastAPI endpoint also preserves a one-external-call rule: only the top recommendation gets generated AI copy. Lower-ranked recommendations use the local fallback. That keeps latency controlled.

## Backend and Frontend

The backend is a FastAPI app. It loads menu data, promotions, and affinity rules at startup from local CSV and JSON files. It exposes:

- `/api/menu`
- `/api/recommend`
- `/api/backtest`
- `/api/recommend/feedback`

The frontend is plain HTML, CSS, and JavaScript. It renders the menu, cart, recommendations, and backtest simulation without a build step.

The current runtime uses SQLite as the primary local data store, populated from generated CSV and JSON files. If the database is missing or invalid, the app falls back to CSV/JSON loading for demo resilience.

The customer site is available at `/customer`, with a protected ordering page at `/customer/app`. It is a separate route family: the kiosk remains at `/` and its global recommendation behaviour stays unchanged.

## Benchmark

The benchmark uses 5,000 synthetic orders generated from explicit basket scenarios, such as burger meals, fried chicken meals, rice meals, pasta meals, snack baskets, bucket/group meals, dessert-led baskets, and drink-led snack baskets.

The backtest compares:

- a static baseline that suggests one common default item, Pepsi
- the hybrid recommender's top-3 panel using association rules and context reranking

The default benchmark is now a partial-cart replay. It anchors each eligible synthetic order on one starting item, hides the remaining add-ons, and counts a recommendation only when it recovers a held-out item from that same synthetic order. A stricter full-order top-1 Monte Carlo check remains available as secondary evidence.

The current fixed-seed simulation reports:

- 4,194 eligible partial-cart transactions
- +10.14% simulated AOV uplift
- about +8,433 VND per eligible transaction
- +1.82% on the conservative full-order top-1 check after discount-aware sale-price accounting

Panel-size sensitivity on the same generated data:

| Recommendation panel | Synthetic AOV uplift | Approx. VND per eligible transaction |
| --- | ---: | ---: |
| Top-3 default kiosk panel | +10.14% | +8,433 VND |
| Top-4 sensitivity check | +12.62% | +10,494 VND |
| Top-5 sensitivity check | +14.50% | +12,053 VND |

I would not lead with the top-4 or top-5 numbers as the main UX. They are useful for explaining the revenue/usability tradeoff to judges: more visible choices recover more held-out add-ons in the synthetic replay, but the demo intentionally uses a smaller default panel to avoid overwhelming the customer.

I would be careful not to call this real revenue proof. It is evidence that the mechanics work in a controlled synthetic scenario. The next step would be real kiosk logs or an A/B test.

### Customer Personalization Evidence

The customer replay is a second, separate experiment. It creates 500 deterministic personas, each with 8–24 historical orders followed by one strictly later held-out order. The replay compares a general hybrid top-three panel with a history-aware top-three panel and uses an effective sale price when a personal offer is accepted.

- General hybrid AOV: 118,908 VND
- Personalized AOV: 136,692 VND
- Absolute synthetic change: +17,784 VND
- Synthetic uplift: +14.96%

This validates that the bundled customer policy is reproducible and measurable in its own fixture. The comparison changes both ranking signals and promotion treatment: the general arm uses the global promotion calendar, while the customer arm may use a personal offer. It therefore does not isolate the effect of history alone, does not prove that 14.96% of real-world revenue will be created, and should not be combined with the kiosk's 10.14% result.

## Technical Tradeoffs

The main tradeoff is that this demo favors reliability and explainability over complex modeling.

Association rules are simple, inspectable, and easy to run offline. The bandit is lightweight enough for feedback-driven tuning. The copy system uses AI only where it adds user-facing value, while fallback logic protects latency.

The limitation is that synthetic data cannot prove real customer behavior. It only proves that the pipeline, ranking logic, fallback behavior, and simulation harness work end to end.

## Closing Answer

Technically, the project is a practical kiosk recommender, not just an AI wrapper. The AI copy is one layer, but the core system is the recommendation pipeline: offline basket mining, context-aware reranking, feedback-based bandit updates, and strict fallback behavior for kiosk reliability.

The strongest result so far is not that we proved production revenue lift. We have not. The strongest result is that the demo shows a realistic architecture for safer, more relevant kiosk recommendations, with measurable synthetic benchmark output and clear next steps for real-world validation.
