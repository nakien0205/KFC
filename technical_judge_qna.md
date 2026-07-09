# Technical Judge Q&A Rehearsal

This Q&A is based on a judge agent that only received a brief project summary, not the full repository context. The answers are written as short speaking answers you can use if judges ask technical follow-up questions.

## 1. How exactly is the synthetic order data generated?

The synthetic data is not just random item mixing. I generate 5,000 orders using explicit basket scenarios, such as burger meals, fried chicken meals, rice meals, pasta meals, snack meals, group buckets, dessert-led baskets, and drink-led snack baskets.

Each scenario has hand-coded attachment probabilities. For example, burger baskets are more likely to include fries and Pepsi, while dessert-led baskets are more likely to include a drink or snack add-on.

I should be clear that this is still synthetic data. It is useful for testing the mechanics of the recommender, but it is not a substitute for real kiosk sales logs.

## 2. How do you know the reported 10.14% AOV uplift is meaningful?

I treat the 10.14% uplift as a synthetic benchmark result, not as production proof.

The default backtest uses a fixed-seed partial-cart replay. It starts each eligible synthetic order with one anchor item, hides the remaining add-ons, and tests whether the top-3 recommendation panel can recover held-out items from that same order. In the current run, it evaluates 4,194 eligible carts and estimates about +8,433 VND per eligible transaction, or +10.14% AOV uplift, against a static Pepsi baseline.

I also keep a stricter full-order top-1 benchmark. That conservative check is smaller, but still positive at +1.82% after accepted promoted items are counted at sale price.

What this proves is that the pipeline can create measurable lift inside the synthetic scenario. What it does not prove is that real customers would behave the same way.

## 3. What is the baseline recommender you compare against?

The baseline is intentionally simple. It suggests a common default item, currently Pepsi, based on item support in the synthetic orders.

The headline benchmark compares that one-item baseline against the hybrid recommender's top-3 panel during partial-cart replay. The hybrid recommender is more dynamic because it uses association rules, active promotions, sale-ending urgency, time-of-day context, and bandit-updated context weights.

This is a reasonable first baseline for a hackathon demo, but I would add more baselines next, such as top-selling add-ons by category, promotion-only ranking, and random add-ons, to make the evaluation stronger.

## 4. How do you prevent recommending items already in the cart?

The recommendation logic filters out cart items before returning candidates. That rule is part of the core recommender behavior because recommending something already in the cart is a bad kiosk experience.

This also applies when the system falls back from association rules to rule-based recommendations.

## 5. How do association rules, time-of-day logic, promotions, and bandit feedback combine into one final ranking?

The system starts with a base score from association-rule confidence. Then it applies context multipliers:

```text
score = base_confidence * (1 + promo_boost) * (1 + time_boost) * (1 + urgency_boost)
```

Promotion boost applies when the item matches an active promotion. Time boost applies when the item category fits the current time window, such as lunch or dinner. Urgency boost applies only when the matched sale is close to ending.

The dynamic promo engine also calculates sale price and amount-off framing, and the backtest uses the sale price when a promoted recommendation is accepted.

The bandit controls the boost values. In expected mode, it uses the mean of the learned Beta distribution. In simulation mode, it samples from the Beta distribution using Thompson Sampling.

## 6. How do you avoid overfitting the recommender to the synthetic data generator?

I do not fully solve that yet. The honest answer is that synthetic data always carries overfitting risk.

To reduce the risk, I separate the stages: data generation creates baskets, Apriori mines association rules from the generated orders, and the recommender consumes the mined rules instead of directly reading the generator logic.

But the true fix is real validation. Before claiming business impact, I would need real kiosk logs or an A/B test against live customer behavior.

## 7. What happens when there are no useful association rules for the current cart?

The system falls back to rule-based recommendations. It still filters out cart items and applies the same context logic, so the kiosk can return a useful suggestion even when association rules do not match the current basket.

This is important because sparse carts and unusual baskets are normal in kiosk usage.

## 8. How does the Thompson Sampling bandit learn from feedback, and what feedback signal does it use?

The bandit tracks two context families: promotion context and time-of-day context.

Each context has alpha and beta values. If feedback says the recommendation was accepted, alpha increases. If it was rejected, beta increases.

The feedback endpoint accepts recommendation feedback, and the backtest also simulates accepted or rejected recommendations. During ranking, the system can sample from the learned distributions to balance exploration and exploitation.

## 9. How do you stop the bandit from learning bad behavior from sparse or biased feedback?

For this demo, the bandit starts with priors instead of starting from zero. That makes early behavior more stable.

But I would not claim this fully solves sparse or biased feedback. In production, I would add safeguards such as minimum sample thresholds, decay windows, per-store monitoring, and limits on how much the bandit can move ranking weights.

I would also separate real acceptance from noisy signals like accidental taps.

## 10. How is AI-generated English copy controlled for quality, speed, and safety?

The AI call asks for structured JSON with English copy and rationale. The system enforces a strict timeout for the Gemini path and falls back to local English template copy if the call fails, times out, returns bad output, or returns the wrong language.

The FastAPI recommendation endpoint also limits external generation to the top recommendation. Lower-ranked recommendations use local fallback copy. That keeps latency bounded.

For production, I would add stronger content filters and approval rules, but the current demo already handles the main kiosk risk: the UI should not freeze because an AI service is slow.

## 11. What is the kiosk user experience when the AI service is unavailable?

The kiosk still works. The recommender returns local English template copy and a rationale instead of waiting for the AI service.

The customer can still see recommendations, add items, and continue checkout. The AI layer improves copy quality, but it is not required for the kiosk to function.

## 12. What would be required before claiming real business impact instead of synthetic uplift?

I would need real production evidence.

The next step would be an A/B test where one group sees the baseline recommendation strategy and another group sees the hybrid recommender. I would measure average order value, attach rate, acceptance rate, checkout completion, latency, and any negative user experience signals.

Until then, the correct claim is: this demo shows a working architecture and a positive synthetic benchmark. It does not prove real sales uplift yet.
