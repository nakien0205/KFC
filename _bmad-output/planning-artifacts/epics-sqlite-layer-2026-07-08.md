---
stepsCompleted:
  - step-01-validate-prerequisites.md
  - step-02-design-epics.md
  - step-03-create-stories.md
inputDocuments:
  - _bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md
  - _bmad-output/specs/spec-kfc-kiosk-recommender/stack.md
  - _bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md
---

# KFC RAG system - SQLite Layer Epic Breakdown

## Overview

This document provides a focused epic and story breakdown for adding a local SQLite data layer to the KFC Kiosk Recommendation System without replacing the existing project-wide epic breakdown.

## Requirements Inventory

### Functional Requirements

FR1: Create a local SQLite database for structured kiosk demo data, including menu catalog, promotions, historical orders, order items, and mined affinity rules.

FR2: Add a repeatable database initialization or loading path that can build the SQLite database from the existing generated CSV and JSON artifacts under `_bmad-output/data/`.

FR3: Update the data generation and affinity-mining pipeline so generated menu, promotion, order, and affinity-rule artifacts remain consistent with the SQLite database.

FR4: Update FastAPI startup data loading so the runtime can use SQLite as the primary source for menu, promotions, and affinity rules while preserving current API response behavior.

FR5: Preserve the existing recommendation contracts: empty carts, missing timestamps, and invalid timestamps still return HTTP 200 with an empty list from `/api/recommend`.

FR6: Preserve the rule that the recommender never recommends an item already in the cart.

FR7: Preserve the current one-external-call rule for `/api/recommend`: only the top recommendation receives generated copy; remaining recommendations use local fallback copy.

FR8: Update the backtest harness so it can read the same structured data source used by runtime recommendation loading and continue reporting baseline AOV, hybrid AOV, absolute change, and percentage uplift.

FR9: Add tests that verify SQLite initialization, data loading, runtime API behavior, and backtest compatibility without making real network calls or writing production bandit weights.

FR10: Update project documentation to explain the SQLite schema, data flow, commands, fallback behavior, and remaining flat-file compatibility.

### NonFunctional Requirements

NFR1: SQLite must remain local and simple to run; no external database server or cloud dependency is introduced.

NFR2: The SQLite layer must preserve the current local demo workflow and be rebuildable from generated artifacts.

NFR3: The runtime recommendation path must remain low-latency by loading required structured data at startup and avoiding per-request heavy database work.

NFR4: Existing API response shapes must remain compatible with the static frontend unless a future product requirement explicitly changes them.

NFR5: Tests must not make real Gemini, OpenRouter, or Ollama calls; network-dependent copy generation must stay mocked.

NFR6: Tests must not write production bandit weights; bandit persistence must keep its existing race-safety guarantees.

NFR7: Prices must continue to be formatted as VND with dot separators through `format_price_vnd`.

NFR8: Customer-facing copy and rationales must remain in Vietnamese unless the product requirement changes.

### Additional Requirements

- The stack companion names SQLite as the selected local database, so this work should move SQLite from a deferred path into the implemented local storage layer.
- The current architecture spine's AD-2 says runtime data is loaded from CSV/JSON under `_bmad-output/data/`; this decision must be updated or superseded so SQLite is the primary structured store while preserving local demo reliability.
- The pipes-and-filters structure must remain intact: data generation, affinity mining, runtime recommendation loading, API delivery, and backtest simulation should stay separated.
- FastAPI endpoints must stay aligned with the frontend: `/api/menu`, `/api/recommend`, `/api/backtest`, and `/api/recommend/feedback`.
- New backend files should remain in the project root unless a small local module is clearly justified by the existing codebase.
- The implementation must not try to solve the AOV uplift target in this SQLite layer scope; AOV improvement will be handled separately.

### UX Design Requirements

No new UX design requirements were found for this SQLite layer scope. Existing frontend behavior should remain unchanged unless required to keep API calls compatible.

### FR Coverage Map

FR1: Epic 1 - Create the SQLite schema and local database.

FR2: Epic 1 - Build repeatable SQLite initialization from generated artifacts.

FR3: Epic 1 - Keep generation, mining, and database artifacts consistent.

FR4: Epic 1 - Load runtime menu, promotions, and rules from SQLite.

FR5: Epic 1 - Preserve `/api/recommend` empty/invalid input behavior.

FR6: Epic 1 - Preserve no-duplicate-cart recommendation rule.

FR7: Epic 1 - Preserve one external copy-generation call rule.

FR8: Epic 1 - Keep backtest compatible with the runtime data source.

FR9: Epic 1 - Add tests for SQLite, API, and backtest behavior.

FR10: Epic 1 - Update docs for schema, commands, and data flow.

## Epic List

### Epic 1: Relational Data-Backed Kiosk Recommendation Demo

Users, judges, and developers can run the kiosk recommender with a real local SQLite data layer instead of relying only on CSV/JSON files, while preserving the existing recommendation behavior, backtest flow, and frontend API contracts.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10

**User value delivered:** The demo better matches the hackathon expectation of structured relational menu data, stays easy to run locally, and keeps the existing kiosk experience working.

**Natural dependency:** This epic depends on the existing CSV/JSON pipeline as source material, but it does not depend on any future AOV work.

## Epic 1: Relational Data-Backed Kiosk Recommendation Demo

Users, judges, and developers can run the kiosk recommender with a real local SQLite data layer instead of relying only on CSV/JSON files, while preserving the existing recommendation behavior, backtest flow, and frontend API contracts.

### Story 1.1: Build SQLite Catalog And Promotion Store

**Requirements Covered:** FR1, FR2

As a developer,
I want menu and promotion CSVs loaded into SQLite,
So that the demo has a relational source for structured catalog data.

**Acceptance Criteria:**

**Given** `_bmad-output/data/menu.csv` and `_bmad-output/data/promotions.csv` exist with their required fields
**When** the SQLite initialization command is run
**Then** a local SQLite database is created or rebuilt with menu and promotion tables
**And** the imported records preserve item names, categories, prices, images when present, promotion names, discount values, and date ranges.

**Given** the SQLite initialization command has already been run once
**When** the command is run again with the same source files
**Then** the resulting catalog and promotion rows are deterministic
**And** duplicate rows are not accumulated.

**Given** a required menu field such as `name`, `category`, or `price` is missing
**When** SQLite initialization runs
**Then** the command fails with a clear validation error
**And** it does not silently create an incomplete runtime database.

### Story 1.2: Store Orders And Affinity Rules In SQLite

**Requirements Covered:** FR1, FR2, FR3

As a developer,
I want historical orders and mined rules stored in SQLite,
So that recommendation inputs live in one relational dataset.

**Acceptance Criteria:**

**Given** `_bmad-output/data/orders.csv` and `_bmad-output/data/affinity_rules.json` exist
**When** the SQLite loading path runs
**Then** orders, order items, and affinity rules are imported into SQLite
**And** each affinity rule preserves `antecedents`, `consequents`, `support`, `confidence`, and `lift`.

**Given** generated orders include the optional `scenario` column
**When** orders are loaded into SQLite
**Then** the scenario value is preserved where available
**And** downstream consumers that only require `order_id` and `item_name` still work.

**Given** SQLite loading finishes successfully
**When** validation checks run
**Then** row counts and required fields are checked against the flat source artifacts
**And** mismatches fail clearly instead of producing a stale or partial database.

### Story 1.3: Load Runtime Recommendations From SQLite

**Requirements Covered:** FR4, FR5, FR6, FR7

As a kiosk operator,
I want the FastAPI app to load menu, promotions, and rules from SQLite,
So that the kiosk runs from the relational data source.

**Acceptance Criteria:**

**Given** the SQLite database exists and contains menu, promotion, and affinity-rule data
**When** FastAPI starts
**Then** runtime menu, promotion, and rule data are loaded from SQLite as the primary source
**And** `/api/menu` keeps the same response shape as the current frontend expects.

**Given** a request to `/api/recommend` has an empty cart, missing timestamp, or invalid timestamp
**When** the request is handled
**Then** the API returns HTTP 200 with an empty list
**And** this behavior matches the existing contract.

**Given** a recommendation request has valid cart items and timestamp
**When** recommendations are generated from SQLite-loaded data
**Then** no item already in the cart is recommended
**And** only the top candidate receives external generated copy while remaining candidates use local fallback copy.

### Story 1.4: Run Backtest From The Same SQLite Dataset

**Requirements Covered:** FR8, FR9

As a judge or developer,
I want the backtest to use the same SQLite-backed data source,
So that demo metrics match runtime data.

**Acceptance Criteria:**

**Given** the SQLite database has been built from the generated artifacts
**When** `python backtest.py` runs
**Then** it reads the same structured menu, promotion, order, and affinity-rule data used by runtime loading
**And** it still reports baseline AOV, hybrid AOV, absolute change, percentage uplift, and total simulated transactions.

**Given** the backtest runs with a fixed seed
**When** the simulation completes
**Then** the result is deterministic for unchanged input data
**And** the backtest uses temporary bandit weights instead of writing production bandit state.

**Given** the SQLite database is missing or stale
**When** the backtest starts
**Then** the failure mode is explicit
**And** the user can rebuild the database from the documented local command.

### Story 1.5: Document And Verify SQLite Data Flow

**Requirements Covered:** FR9, FR10

As a maintainer,
I want docs and tests updated,
So that future work knows SQLite is implemented and how to rebuild it.

**Acceptance Criteria:**

**Given** the SQLite layer is implemented
**When** project documentation is updated
**Then** `AGENTS.md`, `docs/index.md`, stack/spec wording, and submission wording explain SQLite as implemented local storage
**And** no document still describes SQLite only as deferred.

**Given** tests are run for the SQLite layer
**When** the test suite executes
**Then** tests cover SQLite initialization, data import validation, runtime API behavior, and backtest compatibility
**And** tests do not make real Gemini, OpenRouter, or Ollama network calls.

**Given** bandit persistence is involved in tests or backtest execution
**When** those paths run
**Then** production bandit weights are not written
**And** the existing `threading.RLock` and atomic `os.replace` persistence behavior remains preserved.
