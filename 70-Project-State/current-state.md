# Current Project State

**Updated:** 2026-10-07

Deal Arby has the core offline decision engine in place: strategy config, profitability calculator, listing evaluator, scoring, SQLite persistence, watchlist config/loader, and unit tests. The repository also uses the standard numbered second-brain layout and `master_plan.md` for the Voyages/Roadmap tool.

## Current boundary
No live marketplace connector or live comparable-price source is implemented yet. The system can evaluate normalized/test listings but cannot discover real deals on its own.

## Immediate next milestone
Build the eBay connector, then add a defensible comparable-price valuation layer before enabling automated deal alerts.

## Important constraints
- Prefer official APIs/feeds when available.
- Keep credentials out of Git.
- Preserve manual review for counterfeit-prone or ambiguous items.
- Conservative valuation is preferred to optimistic profit estimates.
