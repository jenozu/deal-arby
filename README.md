# Deal Arby

Deal Arby is a configurable online-arbitrage opportunity engine. It is designed to discover underpriced products, estimate conservative resale economics, score opportunities, store observations, and eventually alert on strong deals.

The first implementation is deliberately conservative: known products, fixed-price listings, configurable risk filters, manual-review gates, and a maximum source price of CAD 150 by default.

## Repository structure

This repo uses the same numbered second-brain structure used across the project system:

- `00-Inbox/` — unsorted notes and incoming ideas
- `10-Strategy/` — business rules and product strategy
- `20-Architecture/` — system design and interfaces
- `30-Decisions/` — ADR-style decisions
- `40-Data/` — data definitions and safe sample data
- `50-Code/` — executable Python package, configs, and tests
- `60-Operations/` — runbooks and testing/deployment notes
- `70-Project-State/` — current status and handoff context
- `80-Outputs/` — generated reports/exports (not secrets)
- `90-Sources/` — research/source notes
- `Templates/` — reusable note templates
- `master_plan.md` — roadmap-tool source of truth
- `Home.md` — second-brain navigation
- `SCHEMA.md` — documentation conventions
- `.hermes.md` — operating instructions for Hermes/AI coding agents

## Run the code

```bash
cd 50-Code
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Current architecture

`strategy.yaml` → calculator → evaluator → scoring → database

`watchlist.yaml` → watchlist loader → eBay Browse connector → normalized listings → database

The next major implementation milestone after the live eBay smoke test is comparable-price valuation.

## eBay connector

Phase 3 uses the official eBay Buy Browse API. Copy the variable names from `50-Code/.env.example` into your local/VPS environment and provide your own eBay Developer Program Client ID and Client Secret. Real credentials and generated access tokens must never be committed.

The connector defaults to the eBay Canada marketplace (`EBAY_CA`) and CAD. Its automated tests use mocked HTTP responses, so CI does not require secrets.
