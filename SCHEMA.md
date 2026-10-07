# Second-Brain Schema

Use Markdown as the durable knowledge format. Code, tests, and configuration on `main` are authoritative when they conflict with older notes.

## Note rules

1. Keep raw or unverified ideas in `00-Inbox/`.
2. Store durable business logic in `10-Strategy/`.
3. Store architecture and interface contracts in `20-Architecture/`.
4. Record consequential choices in `30-Decisions/` using ADR-style notes.
5. Never commit credentials, API tokens, private customer data, or raw marketplace account exports.
6. Update `70-Project-State/current-state.md` after material milestones.
7. Keep `master_plan.md` synchronized with actual implementation status.
8. Use `[[wikilinks]]` where helpful for navigation.
9. Mark uncertain claims as **Needs verification** rather than presenting them as fact.
