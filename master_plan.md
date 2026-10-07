# Deal Arby — Master Plan

> Roadmap source of truth. Check tasks only when the implementation exists in the repository and is validated at the level described.

## Phase 1 — Foundation and Deal Logic
- [x] Define configurable purchase/profit/risk strategy in `50-Code/config/strategy.yaml`
- [x] Implement conservative deal calculator
- [x] Implement listing evaluator and hard-reject/manual-review logic
- [x] Implement 0–100 opportunity scoring
- [x] Implement SQLite persistence layer
- [x] Define product watchlist configuration
- [x] Implement watchlist loader, validation, search-job generation, and first-pass filtering

## Phase 2 — Tests and Repository Baseline
- [x] Add unit tests for calculator
- [x] Add unit tests for evaluator
- [x] Add unit tests for scoring
- [x] Add unit tests for database
- [x] Add unit tests for watchlist
- [x] Confirm the complete test suite passes in GitHub Actions
- [x] Add coverage reporting and define a minimum coverage target (80% branch coverage)

## Phase 3 — eBay Source Connector
- [x] Confirm current eBay API/application requirements and approved endpoints
- [x] Add environment-variable configuration and `.env.example`
- [x] Implement eBay authentication/client module
- [x] Convert watchlist `SearchJob` objects into eBay search requests
- [x] Normalize eBay results into a common listing model
- [x] Handle pagination, rate limits, retries, and API errors
- [x] Add connector fixtures/mocks and automated tests
- [x] Persist discovered listings without duplicates
- [ ] Run a live authenticated eBay smoke test with the user's eBay developer keyset

## Phase 4 — Comparable-Price Valuation
- [ ] Define normalized comparable-sale data model
- [ ] Retrieve trustworthy sold/completed comparable data where permitted
- [ ] Exclude accessories, bundles, wrong models, damaged items, and obvious outliers
- [ ] Add condition-aware comparable filtering
- [ ] Calculate conservative market value and quick-sale value
- [ ] Calculate `price_confidence` from comparable quality/quantity/spread
- [ ] Store price observations for historical valuation
- [ ] Add valuation tests using fixed fixtures

## Phase 5 — Matching and Opportunity Pipeline
- [ ] Create canonical product/model matcher
- [ ] Support aliases, punctuation variants, generations, storage/size/kit distinctions
- [ ] Calculate `match_confidence`
- [ ] Build end-to-end pipeline: search → normalize → filter → value → calculate → evaluate → score → persist
- [ ] Suppress duplicate opportunities and repeated alerts
- [ ] Add dry-run mode with no outbound notifications
- [ ] Add end-to-end fixture test

## Phase 6 — Alerts and Review Workflow
- [ ] Define alert payload with purchase price, market value, profit, ROI, score, confidence, and source link
- [ ] Implement first notification channel
- [ ] Respect configured alert thresholds and duplicate suppression
- [ ] Flag manual-review reasons prominently
- [ ] Record successful/failed alerts in SQLite
- [ ] Add purchased/passed/watching/expired workflow states

## Phase 7 — Operator Dashboard
- [ ] Create simple dashboard/API for top active opportunities
- [ ] Show score breakdown and rejection/manual-review reasons
- [ ] Show product price history and comparable evidence
- [ ] Add filters by source, category, score, ROI, and status
- [ ] Add actions for purchased, passed, watching, and sold

## Phase 8 — Broader Discovery and Additional Sources
- [ ] Evaluate additional sources using legal/technical feasibility first
- [ ] Add retailer-clearance connector framework
- [ ] Evaluate Facebook Marketplace integration constraints
- [ ] Evaluate Kijiji integration constraints
- [ ] Add category-wide discovery mode only after exact-model pipeline is reliable
- [ ] Add trending/unknown-product discovery with stricter confidence gates

## Phase 9 — Production Reliability
- [ ] Add structured logging and run IDs
- [ ] Add scheduled scans
- [ ] Add health checks and failure alerts
- [ ] Add database backup/retention plan
- [ ] Add configuration validation command
- [ ] Add CI checks for tests and formatting
- [ ] Document deployment on the chosen host/VPS

## Phase 10 — Learning Loop and Optimization
- [ ] Track predicted vs realized sale price/profit
- [ ] Track time-to-sale and stale inventory
- [ ] Measure false-positive/manual-review rates
- [ ] Tune thresholds using actual outcomes
- [ ] Add per-category/per-source fee and shipping models
- [ ] Expand purchase limits only after validated performance data exists
