---
stepsCompleted:
  - step-01-validate-prerequisites.md
  - step-02-design-epics.md
  - step-03-create-stories.md
  - step-04-final-validation.md
inputDocuments:
  - _bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md
  - _bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md
---

# KFC Kiosk Recommendation System - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for KFC Kiosk Recommendation System, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Generate synthetic menu catalog (menu.csv), promo calendar (promotions.csv), and historical order logs (orders.csv with >= 1,000 orders) incorporating item combos and co-occurrence rules. (Source: CAP-1)
FR2: Mine item associations from synthetic order history using Apriori/association rules and output confidence and lift metrics. (Source: CAP-2)
FR3: Save mined rules to local file (affinity_rules.json) and cache in-memory at startup. (Source: CAP-2, AD-2)
FR4: Adjust affinity scores in real-time using context reranker based on cart items, promotions, and time of day using the multiplicative scoring formula. (Source: CAP-3, AD-4)
FR5: Generate personalized recommendation copy (in Vietnamese) and brief rationale via single GenAI call per recommendation request. (Source: CAP-4, AD-3)
FR6: Fallback to local rule-based template copy if GenAI call fails or exceeds 1.2s timeout. (Source: AD-3)
FR7: Expose POST /api/recommend endpoint to accept cart items/timestamp and return sorted recommendations with GenAI copy and rationale. (Source: AD-5)
FR8: Expose POST /api/backtest endpoint to run AOV comparison simulation over historical orders. (Source: AD-5)
FR9: Provide Vanilla HTML/JS/CSS Kiosk UI in static/ to visualize menu, interactive cart updates, and live recommendation panel with GenAI custom copy/rationale. (Source: CAP-5, AD-6)
FR10: Provide Backtest Harness script (backtest.py) to replay synthetic orders through baseline and hybrid pipelines and output baseline/hybrid AOV, absolute difference, and percentage uplift. (Source: CAP-6, AD-5)

### NonFunctional Requirements

NFR1: GenAI response latency under 1.5s total (max timeout threshold of 1.2s on Gemini API call). (Source: CAP-4, AD-3)
NFR2: Fully local deployment with simple setup (no external databases, runs on local files cached in-memory). (Source: Constraints, AD-2)
NFR3: GenAI API calls limited to exactly 1 call per recommendation event to optimize cost and latency. (Source: Constraints, AD-3)
NFR4: Robust offline resilience (fallback to local template when API fails/times out). (Source: AD-3)
NFR5: Stateless recommendation pipeline core. (Source: Consistency Conventions)
NFR6: Config parameters (e.g. Gemini API key) loaded via environment variables. (Source: Consistency Conventions)
NFR7: UI styling follows premium design guidelines: Outfit/Inter typography, vibrant gradients, responsive layouts, and micro-animations. (Source: Stack, AD-6)

### Additional Requirements

- Pipes & Filters Architecture: Recommendation logic core must be implemented as modular filters with clear data contracts. main.py FastAPI acts only as a driver and contains no internal processing logic. (Source: AD-1)
- Prices represented in Vietnamese Dong (VND). (Source: Consistency Conventions)
- Timestamps in ISO 8601 format. (Source: Consistency Conventions)
- Error envelopes structured as {"detail": "..."}. (Source: Consistency Conventions)

### UX Design Requirements

UX-DR1: Implement a typography system using a premium sans-serif display font (e.g., Outfit or Geist) and monospace accents (Geist Mono). Kiosk Hero and promotion headlines must be ultra-wide and restricted to a maximum of 2 lines on desktop with strict line-height/descender clearance.
UX-DR2: Implement a nested "double-bezel" (Doppelrand) container design for all menu cards, checkout panels, and recommendation tiles: an outer shell with a subtle background border (`border-white/10`) and padding, containing an inner core with a smaller, concentrically calculated border radius and inset highlight (`shadow-[inset_0_1px_rgba(255,255,255,0.15)]`).
UX-DR3: Implement an asymmetric Bento Grid layout for the recommendation panel with mathematically interlocking, gapless tiles (`grid-flow-dense` and col/row span combos) that mix text, pricing, and visual imagery.
UX-DR4: All primary kiosk action buttons (e.g., "Add to Cart", "Select Promotion") must be fully rounded pills with a button-in-button trailing icon structure, where the action icon (e.g., `+` or `↗`) sits inside its own distinct circular wrapper flush with the main button's right inner padding.
UX-DR5: Add haptic hover states to interactive elements. On hover, elements scale up (`group-hover:scale-102`) with a diagonal translate of nested icons, and scale down (`active:scale-[0.98]`) when pressed. Use a custom cubic-bezier transition (`transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)]`).
UX-DR6: Apply a premium red and white palette staying true to KFC's original brand colors (clean white/warm-white backgrounds, rich red brand accents, sharp near-black typography, and soft grey highlights, with subtle noise texture/grain overlay for a premium paper feel). Avoid generic AI purple glows.
UX-DR7: Kiosk UI must update dynamically upon cart changes with smooth layout transitions (e.g., items entering via slide-up/fade-in staggered masks), avoiding sudden, un-interpolated content jumps.
UX-DR8: GenAI recommendation panel must display a clear, high-contrast, localized copy card (Vietnamese text, prices in VND) with a distinct secondary text field showing the statistical/mining rationale (e.g., "Recommended because 68% of customers add fries"). Text must be sparse and legible.

### FR Coverage Map

FR1: Epic 1 - Generate synthetic menu catalog, promo calendar, and historical orders.
FR2: Epic 1 - Mine association rules using Apriori/association rules.
FR3: Epic 1 - Save mined rules to local file and cache in-memory.
FR4: Epic 2 - Adjust affinity scores in real-time using multiplicative scoring.
FR5: Epic 2 - Call Gemini API for personalized recommendation copy and rationale.
FR6: Epic 2 - Fallback to local rule-based template if GenAI fails or times out.
FR7: Epic 2 - Expose POST /api/recommend endpoint to serve kiosk recommendations.
FR8: Epic 4 - Expose POST /api/backtest endpoint to run simulator and retrieve results.
FR9: Epic 3 - Provide HTML/JS/CSS Kiosk UI to visualize menu, cart, and recommendations.
FR10: Epic 4 - Provide Backtest Harness script (backtest.py) to replay orders and calculate uplift.

## Epic List

### Epic 1: Offline Data & Association Mining Substrate
Generate synthetic menu, promotions, order logs, and mine association rules using Apriori to build the recommendation substrate.
**FRs covered:** FR1, FR2, FR3

### Epic 2: Context-Aware Hybrid Recommendation API
Implement FastAPI server with context-aware reranking, GenAI personalized copy generation, and fallback logic.
**FRs covered:** FR4, FR5, FR6, FR7
**NFRs covered:** NFR1, NFR3, NFR4, NFR5, NFR6

### Epic 3: Interactive Kiosk UI Simulator
Build a premium, animated single-page kiosk simulator displaying menu catalog, cart, and live recommendation panel with GenAI copy.
**FRs covered:** FR9
**NFRs covered:** NFR7
**UX-DRs covered:** UX-DR1, UX-DR2, UX-DR3, UX-DR4, UX-DR5, UX-DR6, UX-DR7, UX-DR8

### Epic 4: AOV Uplift Backtest Simulator
Create a CLI script and endpoint to replay synthetic order logs to compare models and output AOV uplift metrics.
**FRs covered:** FR8, FR10
**NFRs covered:** NFR2

### Epic 5: Local LLM Integration and Dynamic Contextual Boosts
Implement local Ollama LLM provider and dynamically optimize context boosts via Multi-Armed Bandits (MAB).
**FRs covered:** FR4, FR5, FR6, FR7, FR8, FR10
**NFRs covered:** NFR1, NFR2, NFR3, NFR4, NFR5

## Epic 1: Offline Data & Association Mining Substrate

Generate synthetic menu, promotions, order logs, and mine association rules using Apriori to build the recommendation substrate.

### Story 1.1: Generate Synthetic KFC Menu, Promotions, and Order History

As a data engineer,
I want to execute a data generation script,
So that I have a realistic dataset for training the recommender.

**Acceptance Criteria:**

**Given** raw menu data or fallback catalog
**When** `generate_data.py` runs
**Then** it creates `menu.csv`, `promotions.csv`, and `orders.csv` in `_bmad-output/data/`
**And** `orders.csv` has >= 1,000 orders
**And** burger orders contain fries/drinks at >50% frequency

### Story 1.2: Mine Item Affinities and Save Rules

As a data analyst,
I want to run association mining on order history,
So that I extract item affinity rules with support, confidence, and lift.

**Acceptance Criteria:**

**Given** `orders.csv` exists
**When** `affinity_engine.py` runs
**Then** it mines association rules via Apriori
**And** saves rules to `affinity_rules.json` and `_bmad-output/data/affinity_rules.json`
**And** fallback mechanism triggers lower thresholds if rule count < 5

## Epic 2: Context-Aware Hybrid Recommendation API

Implement FastAPI server with context-aware reranking, GenAI personalized copy generation, and fallback logic.

> [!NOTE]
> **Future Personalization Expansion:** Currently, the system uses synthetic historical data to recommend to anonymous/offline kiosk users. After MVP completion, we will expand this to support online personalization (for users with logged-in KFC accounts ordering online). The offline kiosk recommender will then combine online personalization profiles with real-time offline cart preferences.

### Story 2.1: Context-Aware Reranker Algorithm

As a developer,
I want to implement a stateless reranking filter that applies context boosts to mined affinity confidence scores,
So that recommendations dynamically adjust to what is currently in the cart, active promotions, and the time of day.

**Acceptance Criteria:**

**Given** an active cart of items, a list of active promotions, and a timestamp
**When** the reranking function evaluates candidate items
**Then** it must apply the multiplicative scoring formula: `Score = Base_Confidence * (1 + Promo_Boost) * (1 + Time_Boost)`
**And** the `Promo_Boost` must be `+0.20` if the candidate is part of an active promotion
**And** the `Time_Boost` must be `+0.15` if the timestamp matches the target category time (e.g. lunch/dinner)
**And** the output must be a sorted list of candidate recommendations in descending order of score

### Story 2.2: GenAI Copy Generation and Fallback Engine

As a developer,
I want to implement a promotional copy generator using the Gemini API with a local rule-based fallback,
So that customers see engaging, personalized recommendation copy and statistical rationales without risking kiosk latency or offline demo failures.

**Acceptance Criteria:**

**Given** a reranked candidate recommendation item and current cart context
**When** calling the GenAI engine
**Then** it must make exactly one structured JSON call to `gemini-2.5-flash`
**And** it must generate localized promotional copy (in Vietnamese) and a brief reason (e.g. "recommended because 68% of customers add fries")
**And** if the Gemini API call fails or exceeds a `1.2s` timeout threshold, the system must immediately fall back to generating copy via a local rule-based template (e.g., "Complete your meal! Add [item] for only [price]đ")

### Story 2.3: FastAPI Server and `/api/recommend` Endpoint

As a kiosk developer,
I want to create a FastAPI web server that loads offline data and exposes the recommendation pipeline,
So that the frontend Kiosk UI can request and display live context-adjusted recommendations.

**Acceptance Criteria:**

**Given** the local files `menu.csv`, `promotions.csv`, and `affinity_rules.json`
**When** the FastAPI server (`main.py`) starts up
**Then** it must read and cache these files in-memory
**And** it must expose a stateless `POST /api/recommend` endpoint that accepts cart items and a timestamp
**And** it must return a list of recommendations, each containing the item name, price, final confidence score, copy, and rationale in under 1.5 seconds

## Epic 3: Interactive Kiosk UI Simulator

Build a premium, animated single-page kiosk simulator displaying menu catalog, cart, and live recommendation panel with GenAI copy.

### Story 3.1: UI Layout, Typography, and Base Styles

As a kiosk customer,
I want to see a visually stunning, high-fidelity ordering screen with premium styling, typography, and a cohesive layout,
So that my first impression of the ordering experience feels premium, clean, and modern.

**Acceptance Criteria:**

**Given** static directory guidelines
**When** the kiosk UI page is loaded
**Then** the page must use a premium red and white palette staying true to KFC's original brand colors (clean white/warm-white backgrounds, rich red brand accents, sharp near-black typography, and soft grey highlights, with subtle noise texture/grain overlay)
**And** it must load and use a premium sans-serif typography system (e.g. Outfit or Geist) for display text and Geist Mono for code/numbers/labels
**And** all display headlines (H1/H2) must be restricted to a maximum of 2 lines on desktop
**And** it must adapt responsively below `768px` to a single-column layout

### Story 3.2: Interactive Cart, Menu Selection, and API Integration

As a kiosk customer,
I want to click on menu items to add them to my cart, view my current cart list, and have recommendations update automatically,
So that my ordering session is fully interactive and personalized to my selections.

**Acceptance Criteria:**

**Given** a list of menu items from `menu.csv` loaded by the backend
**When** a user clicks a menu item card
**Then** the item is added to the active cart, and the cart list updates in the UI
**And** on every cart state change (item added or removed), the JavaScript application (`static/app.js`) must trigger a `POST /api/recommend` request with the current cart item names and active ISO 8601 timestamp
**And** the UI must handle loading states smoothly while waiting for the recommendation API response

### Story 3.3: High-Fidelity Recommendation Panel

As a kiosk customer,
I want to see recommended items presented in an elegant, animated layout with personalized promotional copy and clear reasons,
So that I can easily decide to add recommended items to my cart.

**Acceptance Criteria:**

**Given** a response from `/api/recommend`
**When** displaying recommendations in the UI panel
**Then** the recommendations must be displayed in an asymmetric, gapless Bento Grid of interlocking cells
**And** each card container must utilize the "double-bezel" (Doppelrand) card design: a nested layout with an outer shell (`border border-black/5` or `border-white/10`) and a concentrically smaller inner core with an inset highlight shadow
**And** all recommendation action buttons must be fully rounded pills with a button-in-button trailing icon format (e.g., plus icon inside a smaller nested circle)
**And** cards must slide up and fade in with staggered entry animations, and have haptic hover states (scale up, diagonal icon translate) and active states (pressed scaling `scale-[0.98]`)
**And** each recommendation must display clear Vietnamese promotional copy and its statistical co-occurrence rationale in a secondary stats text field

## Epic 4: AOV Uplift Backtest Simulator

Create a CLI script and endpoint to replay synthetic order logs to compare models and output AOV uplift metrics.

> [!NOTE]
> **MVP/Hackathon Scope:** Since this project is a hackathon proof-of-concept and not production class, all standard security measures (such as authentication, session management, route protection, API rate limiting, and CORS constraints) are explicitly skipped to optimize implementation speed.

### Story 4.1: Backtest Replay Logic and Math Module

As a business analyst,
I want to execute an offline simulation script that replays historical transactions through different recommendation pipelines,
So that I can mathematically prove the AOV (Average Order Value) uplift of the hybrid model over a static recommendation model.

**Acceptance Criteria:**

**Given** synthetic orders log `orders.csv` and mined `affinity_rules.json`
**When** the `backtest.py` harness is executed
**Then** it must simulate order-building by replaying transactions one-by-one
**And** for each order, it must calculate checkout totals under two models:
  - **Baseline Model**: Recommends a static default item (e.g. Pepsi). Simulated customer accepts it based on its baseline support (overall popularity in order history).
  - **Hybrid Model**: Recommends the top context-reranked item. Simulated customer accepts it based on a dynamic probability: $P(\text{Accept}) = \text{Confidence} \times (1 + \text{Promo\_Boost}) \times (1 + \text{Time\_Boost})$ (falling back to baseline support if no association rule matches).
**And** it must output a summary report containing: Baseline AOV, Hybrid AOV, absolute change (VND), and percentage uplift (e.g. "+12.4%")

### Story 4.2: FastAPI Integration for `/api/backtest`

As a kiosk developer,
I want to expose the backtest simulation via a web API,
So that the kiosk UI (or pitch dashboard) can trigger the simulation dynamically and retrieve results.

**Acceptance Criteria:**

**Given** the FastAPI backend
**When** a client sends a `POST /api/backtest` request
**Then** the server must execute the backtest replay simulation module
**And** return a structured JSON response containing: baseline AOV, hybrid AOV, absolute change, and percentage uplift
**And** return the results within standard HTTP response time without memory leaks

### Story 4.3: Partial-Cart Top-K Panel Backtest

As a business analyst,
I want the backtest harness to simulate recommendations while the kiosk cart is still being built,
So that the hackathon benchmark measures the recommendation panel flow shown in the UI instead of only a final-basket upsell.

**Acceptance Criteria:**

**Given** synthetic orders log `orders.csv`, mined `affinity_rules.json`, and menu pricing
**When** `backtest.py` runs with the default fixed demo seed
**Then** it must run a partial-cart replay where each eligible synthetic order is split into an anchor cart item and held-out add-ons
**And** the baseline must remain a static one-item default upsell strategy using Pepsi
**And** the hybrid model must evaluate the top 3 context-reranked recommendations as a kiosk recommendation panel
**And** only held-out items that were present in the original synthetic order may count as accepted add-ons
**And** the fixed-seed default benchmark must report a simulated AOV uplift in the 10% to 15% target band
**And** the older full-order, top-1 conservative benchmark must remain available as secondary evidence
**And** all benchmark wording must clearly say this is a synthetic scenario benchmark, not real production sales proof

## Epic 5: Local LLM Integration and Dynamic Contextual Boosts

Implement local Ollama LLM provider and dynamically optimize context boosts via Multi-Armed Bandits (MAB).

### Story 5.1: Ollama Local LLM Support

As a developer,
I want to configure the recommendation system to call a local Ollama LLM server,
So that the kiosk can generate personalized recommendation copy fully offline without relying on external Gemini API keys.

**Acceptance Criteria:**

**Given** the local server configuration
**When** the recommendation copy generator is called
**Then** it must check if `USE_OLLAMA` is true or if `GEMINI_API_KEY` is not configured
**And** if so, it must format and send the promotional copy request to `POST /api/chat` or `POST /api/generate` on `OLLAMA_HOST` (defaulting to `http://localhost:11434`) using `OLLAMA_MODEL` (defaulting to `llama3.2:3b`)
**And** it must request and successfully parse a JSON response matching the existing schema: `{"copy": "...", "rationale": "..."}`
**And** it must enforce a `1.2s` timeout threshold and instantly fall back to the local rule-based template copy generator upon failure or timeout

### Story 5.2: Dynamic Contextual Reranking via Multi-Armed Bandits

As a data scientist,
I want to apply a Multi-Armed Bandit (MAB) algorithm to dynamically adjust recommendation contextual boosts based on customer click/acceptance feedback,
So that the system continuously learns the optimal promo and time boosts instead of using hardcoded coefficients.

**Acceptance Criteria:**

**Given** a recommendation request and customer interactions
**When** the rerank algorithm scores candidate items
**Then** it must compute scores using dynamically updated bandit weights for each context (e.g. active promotions, time of day)
**And** it must support a feedback endpoint `POST /api/recommend/feedback` that receives rewards (1.0 for accepted, 0.0 for rejected/ignored) and updates the bandit parameters (e.g., via Beta-Binomial Thompson Sampling or LinUCB updates)
**And** it must persist the learned bandit parameters/weights locally to `bandit_weights.json` so they survive server restarts
**And** the backtest harness `backtest.py` must simulate the bandit's online learning over the 1,000+ synthetic transactions, updating weights after each order, and outputting the final learned parameters and resulting AOV uplift

### Story 5.3: Dynamic Promo Calendar and Urgency Boost

As a growth-focused kiosk operator,
I want the demo to generate controlled daily sale promotions and boost items when those sales are close to ending,
So that recommendations can use realistic promotion psychology without making unsupported production-sales claims.

**Acceptance Criteria:**

**Given** generated menu and order data
**When** `generate_data.py` creates the promotion calendar
**Then** it must generate deterministic daily promo rows using weighted category and item-popularity probabilities
**And** generated dynamic discounts must be one of `5`, `10`, `15`, or `20` percent, with `20%` as the maximum
**And** amount-off and sale-price framing must be calculated from the selected item price
**And** the existing required promotion fields must remain compatible with CSV and SQLite loading
**And** `recommender.py` must apply urgency scoring only to matching active promotions close to ending
**And** `backtest.py` must use discounted sale revenue for accepted promoted recommendations
**And** docs and benchmark wording must keep the claim framed as synthetic benchmark evidence, not real production sales proof
