# Sprint Change Proposal - Recommendation Coverage, AOV Credibility, Dataset Assumptions, Railway Demo

Date: 2026-07-07
Project: KFC RAG system
Mode: Batch proposal
Scope: Moderate documentation and demo-hardening change

## 1. Issue Summary

Four areas need correction before demo or submission:

1. Recommendation coverage is strong in the UI path, but mined-rule coverage is narrow.
2. AOV simulation works, but the current credibility claim is too strong.
3. Dataset assumptions are valid for a hackathon proof of concept, but need clearer disclosure.
4. Railway demo behavior is not guaranteed by the repo because no Railway start config is present.

Evidence from local verification:

- Tests pass: 40 passed, 1 warning.
- Seeded CLI backtest produced +4.06% AOV uplift.
- Multiple seeded backtests ranged from +3.48% to +4.77%.
- Submission currently claims +5.83% and +5,748 VND per transaction.
- Dataset has 92 menu items, 1,200 orders, 2,668 order lines, and 124 mined rules.
- Rule consequents cover 15 unique menu items, or 16.3% of the 92-item menu.
- Recommender returns recommendations for 100% of tested single-item carts and 100% of historical full-order carts because fallback recommendations fill gaps.
- Repo has `requirements.txt`, but no `railway.json`, `railway.toml`, `Procfile`, or `Dockerfile`. The user reports Railway has already been configured manually with a volume, so this is an external deployment assumption rather than a repo change requirement.

## 2. Impact Analysis

### Epic Impact

- Epic 1 remains viable. Synthetic data generation and association mining work.
- Epic 2 remains viable. Recommendation API returns live recommendations and has fallback behavior.
- Epic 3 remains viable. UI can show recommendations and backtest output.
- Epic 4 needs wording correction. It proves a simulated uplift under synthetic assumptions; it does not prove real business uplift.
- Epic 5 remains viable, but the pitch should avoid overstating real-time customer learning unless feedback collection is shown in the demo.

### Story Impact

- Story 1.1: Add dataset disclosure to acceptance notes or submission.
- Story 1.2: Clarify that mined-rule coverage is narrow and fallback logic is part of final recommendation coverage.
- Story 4.1: Adjust credibility language and report actual current range or pinned seed result.
- Story 4.2: Stabilize demo output or label it as Monte Carlo simulation.
- Story 5.2: Explain that bandit learning is simulated in backtest and only learns live if feedback events are sent.

### Artifact Conflicts

- `hackathon_submission.md` conflicts with current evidence because it claims +5.83% while the current seeded CLI run gives +4.06%.
- `hackathon_submission.md` says "mathematically validated" and "Proven Revenue Uplift"; this is too strong for synthetic data.
- `static/app.js` always prefixes AOV output with `+`, even if a future simulation returns a negative result.
- `main.py` uses `run_backtest_simulation(seed=None)`, so the Railway/UI demo result can change on each click.
- No Railway config file exists, so deployment behavior depends on manual Railway settings.

## 3. Recommended Approach

Recommended path: Direct Adjustment.

Rationale:

- The core app works. There is no need to roll back features.
- The risk is mostly credibility and demo repeatability, not broken implementation.
- Changes are small and targeted: update pitch wording, stabilize demo output, and add Railway start config.

Effort: Low to medium.
Risk: Low.
Timeline impact: Same-day.

## 4. Detailed Change Proposals

### Proposal A - Recommendation Coverage

Current claim style:

> The system has a broad recommendation engine across the menu.

Recommended replacement:

> The UI returns recommendations for all tested cart states by combining mined association rules with a rule-based fallback. The mined rules are intentionally narrow and high-signal: current rule consequents cover 15 unique menu items, while fallback logic keeps the kiosk experience from going empty.

Rationale:

This is more honest. It does not pretend the mined rules cover the whole menu.

### Proposal B - AOV Simulation Credibility

Current text in `hackathon_submission.md`:

> mathematically validated 5.83% Average Order Value (AOV) uplift

Recommended replacement:

> simulated 3.5% to 4.8% AOV uplift across seeded Monte Carlo replays on 1,200 synthetic transactions

Current text:

> Proven Revenue Uplift

Recommended replacement:

> Simulated Revenue Uplift

Rationale:

The current local results do not support the exact 5.83% claim. The simulation also uses synthetic orders and simulated acceptance probabilities, so "proven" is too strong.

### Proposal C - Backtest Demo Stability

Current behavior:

`main.py` calls `run_backtest_simulation(seed=None)`, so the API demo changes every run.

Recommended change:

- Use a fixed demo seed for the public demo, for example `seed=42`.
- Optionally expose a `randomize` flag later if varied simulations are desired.
- Update the UI to display a minus sign correctly if uplift is negative.

Rationale:

Hackathon demos should be repeatable. Random output during judging can make the app look inconsistent.

### Proposal D - Dataset Assumptions

Recommended disclosure:

> The dataset is synthetic and generated with explicit co-occurrence assumptions. It is suitable for demonstrating recommender mechanics, not for claiming production sales impact.

Add the main assumptions:

- 1,200 synthetic orders.
- Burger orders are biased toward fries and Pepsi.
- Fried chicken, rice/pasta, combos, snacks, and desserts have hand-coded attachment probabilities.
- Data is generated with a fixed random seed.

Rationale:

This protects the project from overclaiming. It also helps judges understand why association rules exist.

### Proposal E - Railway Demo Behavior - Rejected by User

Current repo state:

- No `railway.json`.
- No `railway.toml`.
- No `Procfile`.
- No `Dockerfile`.
- `requirements.txt` includes the needed Python packages for the current app.

Decision:

Do not add Railway files. The user has configured Railway manually and added a Railway volume.

Residual risk:

This is acceptable for the current demo if the manual Railway service start command, public domain, environment variables, and volume mount path are already correct. I cannot verify that from repo contents alone. The trade-off is that deployment behavior is less reproducible from Git, but that is acceptable if the demo environment is already working.

## 5. Implementation Handoff

Scope classification: Moderate.

Developer agent:

- Update `hackathon_submission.md` wording.
- Stabilize `/api/backtest` demo behavior.
- Fix UI plus/minus formatting.
- Do not add Railway config files; rely on the existing manual Railway setup.
- Run tests.

Product owner / reviewer:

- Approve whether the pitch should show a fixed seed result, a range, or both.
- Approve whether the demo should prioritize repeatability or random replay.

Success criteria:

- Submission no longer claims unsupported 5.83% if current code does not reproduce it.
- Backtest demo is repeatable or clearly labeled as randomized.
- Railway deployment works from the manually configured service and volume.
- Tests still pass.

## 6. Checklist Status

- [x] 1.1 Triggering issue identified: demo and pitch credibility gaps.
- [x] 1.2 Core problem defined: implementation works, but claims and demo deployment are not fully aligned with evidence.
- [x] 1.3 Evidence gathered from local tests, code, and data.
- [x] 2.1 Current epics still viable.
- [x] 2.2 Epic-level changes are documentation and demo-hardening only.
- [x] 2.3 Remaining epics reviewed.
- [x] 2.4 No new epic required.
- [x] 2.5 No epic reorder required.
- [x] 3.1 PRD/SPEC impact reviewed.
- [x] 3.2 Architecture impact reviewed.
- [x] 3.3 UI impact reviewed.
- [x] 3.4 Deployment and demo artifacts reviewed.
- [x] 4.1 Direct adjustment is viable.
- [x] 4.2 Rollback is not needed.
- [x] 4.3 MVP review is not needed.
- [x] 4.4 Recommended path selected.
- [x] 5.1 Issue summary created.
- [x] 5.2 Epic and artifact impact documented.
- [x] 5.3 Recommended path documented.
- [x] 5.4 MVP impact and action plan defined.
- [x] 5.5 Handoff plan defined.
- [x] 6.1 Checklist reviewed.
- [x] 6.2 Proposal checked for consistency.
- [x] 6.3 User approval captured with exception: Proposal E rejected.
- [N/A] 6.4 Sprint status not updated because no epic/story structure change is approved yet.
- [x] 6.5 Next steps confirmed: implement Proposals A-D only and keep Railway setup manual.

