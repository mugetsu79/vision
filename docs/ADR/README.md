# Architecture Decision Records

Argus stores architecture decisions in `docs/ADR/` using a lightweight MADR-style structure:

- `Status` captures whether the decision is proposed, accepted, deprecated, or superseded.
- `Context` explains the constraints and why the decision mattered.
- `Decision` states the chosen direction in one place.
- `Consequences` records the trade-offs, follow-up work, and what becomes easier or harder.

When you add a new ADR:

1. Copy the structure from the existing files in `/Users/yann.moren/vision/docs/ADR/`.
2. Name it `ADR-XXXX-short-topic.md` with the next sequential number.
3. Fill in the context, decision, options considered, consequences, and action items.
4. Link the ADR back to the relevant sections in `/Users/yann.moren/vision/argus_v4_spec.md`.
5. If it replaces an older decision, update the older ADR to mention the superseding record.

The current seed ADRs are:

- [/Users/yann.moren/vision/docs/ADR/ADR-0001-identity-provider.md](/Users/yann.moren/vision/docs/ADR/ADR-0001-identity-provider.md)
- [/Users/yann.moren/vision/docs/ADR/ADR-0002-central-gpu.md](/Users/yann.moren/vision/docs/ADR/ADR-0002-central-gpu.md)
