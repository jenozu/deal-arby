# ADR-001 — Python + YAML + SQLite for the first implementation

**Status:** Accepted

## Decision
Use Python for the engine, YAML for editable strategy/watchlist configuration, pytest for tests, and SQLite for local persistence.

## Why
This keeps the first version inexpensive, inspectable, easy to run on Windows or a VPS, and simple enough to iterate before adding heavier infrastructure.

## Consequences
- Marketplace integrations remain modular connectors.
- SQLite is sufficient for the MVP but may be replaced if concurrency/scale demands it.
- Strategy and watchlist behavior can change without editing Python source.
