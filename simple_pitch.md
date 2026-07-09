**KFC Kiosk Recommendation System**

Most self-service kiosks suggest the same generic add-ons to everyone. That often feels random, and it misses a chance to help the customer build a better meal.

This project is a smarter recommendation system for a KFC kiosk. When a customer adds items to their cart, the system recommends useful add-ons based on what people often buy together, the time of day, current promotions, and whether a sale is close to ending.

For example, if someone orders a burger at lunch, the kiosk may suggest fries, a drink, or a dessert with Vietnamese copy that explains why the item fits their meal.

The system is built to work in a real kiosk setting. It uses offline transaction mining, a lightweight learning model that improves from feedback, and AI-generated recommendation copy. If the AI call is slow or unavailable, it immediately falls back to local template copy, so the kiosk does not freeze.

To test the idea, I ran a synthetic partial-cart benchmark with 5,000 generated orders. After skipping single-item baskets, the top-3 recommendation panel was evaluated on 4,194 eligible carts and estimated a 12.17% average order value uplift, around 9,527 VND more per eligible transaction, compared with a static Pepsi baseline. A stricter full-order top-1 check still shows a smaller positive uplift of 1.82% after counting promoted items at sale price.

This is not real production sales proof yet, but it shows the mechanics clearly: better recommendations, safer fallback behavior, and a kiosk experience that feels more helpful than random upselling.
