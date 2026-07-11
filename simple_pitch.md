**KFC Kiosk Recommendation System**

Most self-service kiosks suggest the same generic add-ons to everyone. That often feels random, and it misses a chance to help the customer build a better meal.

This project is a smarter recommendation system for a KFC kiosk. When a customer adds items to their cart, the system recommends useful add-ons based on what people often buy together, the time of day, current promotions, and whether a sale is close to ending.

There is also a separate customer site at `/customer`. A new signed-in customer starts with a global-signal fallback. After three completed orders, the site combines the current cart, global affinity, and that customer's own history to improve suggestions and may issue one complementary offer. The customer database is separate from the kiosk database, so kiosk rebuilds do not erase accounts or order history.

For example, if someone orders a burger at lunch, the kiosk may suggest fries, a drink, or a dessert with English copy that explains why the item fits their meal.

The system is built to work in a real kiosk setting. It uses offline transaction mining, a lightweight learning model that improves from feedback, and AI-generated recommendation copy. If the AI call is slow or unavailable, it immediately falls back to local template copy, so the kiosk does not freeze.

To test the idea, I ran a synthetic partial-cart benchmark with 5,000 generated orders. After skipping single-item baskets, the top-3 recommendation panel was evaluated on 4,194 eligible carts and estimated a 10.14% average order value uplift, around 8,433 VND more per eligible transaction, compared with a static Pepsi baseline. A panel-size sensitivity check on the same data reaches 12.62% with top-4 and 14.50% with top-5, but I keep top-3 as the default kiosk design because too many recommendations can overwhelm the customer. A stricter full-order top-1 check still shows a smaller positive uplift of 1.82% after counting promoted items at sale price.

I also ran a separate customer-policy replay with 500 deterministic synthetic personas. It compares the general hybrid with global promotions against the customer policy of history-aware ranking plus a personal offer, and reports 118,908 VND versus 136,692 VND AOV: a +17,784 VND, 14.96% synthetic change. This is not real sales proof, does not isolate the effect of history alone, and is not added to the kiosk benchmark; it is evidence that the customer policy can be tested repeatably.

This is not real production sales proof yet, but it shows the mechanics clearly: better recommendations, safer fallback behavior, and a kiosk experience that feels more helpful than random upselling.
