# Superseded Handoff: Jetson Optimized Runtime Artifacts And Open-Vocab

Date: 2026-05-10
Superseded: 2026-05-11

This handoff has been superseded by:

```text
docs/superpowers/status/2026-05-11-next-chat-accountable-scene-intelligence-handoff.md
```

The Jetson optimized runtime Track A/B work that was originally planned here has
now landed on `codex/omnisight-ui-spec-implementation`:

- runtime artifact data contract, service, API, and worker candidates
- runtime artifact selector
- TensorRT `.engine` detector wrapper
- worker runtime selection integration
- fixed-vocab artifact register/validate CLI
- compiled YOLOE scene artifact build/register path
- open-vocab compiled scene runtime selection
- UI runtime artifact status
- runtime artifact docs and model loading/configuration guide

Track C / DeepStream remains future work.

Use the current handoff above for the next chat. It starts the Accountable Scene
Intelligence And Evidence Recording implementation, including scene contracts,
privacy manifests, evidence ledger, short incident recording, local/remote
artifact storage, and edge USB/UVC camera sources.
