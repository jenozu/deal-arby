# Current Project State

**Updated:** 2026-10-07

Deal Arby now has the core offline decision engine plus the first marketplace connector foundation. Phase 2 is complete: GitHub Actions is green, pytest runs on pushes/PRs, coverage XML is uploaded as an artifact, and CI enforces an 80% minimum branch-coverage floor.

## eBay connector status
The eBay Browse API connector is implemented with environment-based credentials, OAuth client-credentials token caching, EBAY_CA/CAD defaults, watchlist SearchJob conversion, result normalization, pagination, retries/rate-limit handling, and duplicate-safe SQLite persistence. The connector is covered by mocked automated tests; no secret credentials are committed.

## Current validation
- Local suite: 38 tests passing
- Local branch coverage after eBay connector: ~81%
- Phase 2 GitHub Actions coverage-gated run: passed

## Remaining Phase 3 gate
Run a live authenticated smoke test using an eBay Developer Program keyset. Sandbox can be used for development; production Buy API access is restricted by eBay and depends on the application's approval/access.

## Immediate next step
Obtain/configure the user's eBay Client ID and Client Secret outside Git, run the live smoke test, then begin Phase 4 comparable-price valuation.

## Important constraints
- Prefer official APIs/feeds when available.
- Keep credentials out of Git.
- Preserve manual review for counterfeit-prone or ambiguous items.
- Conservative valuation is preferred to optimistic profit estimates.
