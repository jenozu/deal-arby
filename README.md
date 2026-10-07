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

`watchlist.yaml` → watchlist loader → future marketplace connectors

The next major implementation milestone is the eBay source connector and comparable-price valuation layer.
