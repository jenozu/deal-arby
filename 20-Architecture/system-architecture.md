# System Architecture

## Current pipeline

```text
strategy.yaml ─┐
               ├─> calculator.py -> evaluator.py -> scoring.py -> database.py -> SQLite
watchlist.yaml -> watchlist.py -> future source connectors ────────────────┘
```

## Responsibilities

- `calculator.py`: deterministic financial math and threshold qualification.
- `evaluator.py`: category/condition/risk/confidence/manual-review gates.
- `scoring.py`: weighted 0–100 opportunity ranking and alert eligibility.
- `database.py`: listings, opportunities, price observations, and alert history.
- `watchlist.py`: defines what to search and creates normalized search jobs.
- `sources/`: marketplace-specific clients; connectors should normalize external data rather than leak marketplace-specific structures into core logic.

## Planned flow

Search jobs → connector → normalized listing → cheap watchlist filter → product matcher → comparable valuation → calculator → evaluator → score → database → alert/review UI.
