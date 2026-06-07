# Core Link Reflector Packet Loss Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make state-of-the-art edge-to-reflector packet-loss measurement operational with an authenticated UDP sequence sender/reflector flow.

**Architecture:** Keep Vezor master as the control plane and result store. Link Performance configuration remains edge-site only: a site must have a registered edge node before it can receive link paths, monitoring targets, probe samples, policies, budgets, or throughput checks. Extend the edge agent to run UDP sequence sessions from the edge site, add a small authenticated UDP reflector service, compute loss/RTT/jitter from observed sequence replies, and post summarized samples through the existing Core Link edge sample ingestion path. If the master hosts a reflector, configure it as deployment infrastructure, not as a master-site Link path.

**Tech Stack:** Python `asyncio` datagrams, HMAC-SHA256, FastAPI/Pydantic, React/TypeScript, pytest, Vitest, Ruff, mypy.

---

## File Structure

- Create `backend/src/argus/link/udp_sequence.py`: packet codec, HMAC auth, statistics helpers.
- Create `backend/src/argus/link/reflector.py`: UDP reflector server and CLI.
- Modify `backend/src/argus/services/app.py`: expose edge-site eligibility helpers backed by registered edge nodes.
- Modify `backend/src/argus/link/edge_agent.py`: add `udp_sequence` sender mode.
- Modify `backend/src/argus/link/api.py`: enforce edge-site eligibility and validate richer UDP sequence sample metadata.
- Modify `frontend/src/components/link/types.ts`: add reflector target fields and sample metadata helpers.
- Modify `frontend/src/components/link/LinkActionDialogs.tsx`: expose reflector fields in the link-path form.
- Modify `frontend/src/components/link/LinkProbePanel.tsx`: show edge-to-reflector path and sequence statistics.
- Update generated OpenAPI files if API schemas change.
- Test `backend/tests/link/test_udp_sequence.py`, `backend/tests/link/test_reflector.py`, `backend/tests/link/test_edge_agent.py`, `backend/tests/api/test_link_routes.py`, `backend/tests/services/test_site_service.py` if service-level coverage is needed, and `frontend/src/pages/Links.test.tsx`.

## Task 0: Edge-Site Eligibility And Master Reflector Boundary

**Files:**
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/link/api.py`
- Test: `backend/tests/api/test_link_routes.py`

- [x] **Step 1: Write failing eligibility tests**

Add route tests proving:

- `/api/v1/link/sites/summary` lists only sites with registered edge nodes.
- Existing non-edge/master sites reject link connection setup with `409`.
- Existing non-edge/master sites reject probe sample recording with `409`.

- [x] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py::test_link_site_summary_route_only_lists_edge_sites tests/api/test_link_routes.py::test_link_configuration_rejects_master_or_non_edge_site tests/api/test_link_routes.py::test_link_probe_sample_rejects_master_or_non_edge_site -q
```

Expected: FAIL before the guard is implemented.

- [x] **Step 3: Implement edge-site guard**

Implement:

- `SiteService.list_edge_sites(...)` using `Site` joined to `EdgeNode`.
- `SiteService.is_edge_site(...)`.
- Link summary uses `list_edge_sites`.
- Every site-scoped Link route calls an edge-site guard before reading or mutating Link state.
- Probe routes use probe-specific error text.

- [x] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py -q
```

Expected: PASS.

Master reflector configuration remains a separate deployment service profile. Do not add Link paths or monitoring targets to a master/control-plane site.

## Task 1: UDP Sequence Packet Codec

**Files:**
- Create: `backend/src/argus/link/udp_sequence.py`
- Test: `backend/tests/link/test_udp_sequence.py`

- [ ] **Step 1: Write failing codec tests**

Add tests for:

- Encoding and decoding a request packet.
- Encoding and decoding a reply packet.
- Rejecting bad magic/version/auth tag.
- Preserving session id, sequence, transmit timestamp, and nonce.

Expected test shape:

```python
def test_udp_sequence_packet_round_trips_authenticated_request() -> None:
    secret = b"shared-secret"
    packet = build_probe_packet(
        session_id=bytes.fromhex("00" * 16),
        sequence=7,
        transmit_ns=123456789,
        nonce=42,
        secret=secret,
        reply=False,
    )

    decoded = parse_probe_packet(packet, secret=secret)

    assert decoded.session_id == bytes.fromhex("00" * 16)
    assert decoded.sequence == 7
    assert decoded.transmit_ns == 123456789
    assert decoded.nonce == 42
    assert decoded.reply is False
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_udp_sequence.py -q
```

Expected: FAIL because `argus.link.udp_sequence` does not exist.

- [ ] **Step 3: Implement codec**

Implement:

- `UdpSequencePacket` dataclass.
- `build_probe_packet(...) -> bytes`.
- `parse_probe_packet(packet: bytes, *, secret: bytes) -> UdpSequencePacket`.
- `UdpSequencePacketError`.
- Constants for magic `VZLP`, version `1`, request/reply flags, and 16-byte truncated HMAC-SHA256.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_udp_sequence.py -q
```

Expected: PASS.

## Task 2: UDP Session Statistics

**Files:**
- Modify: `backend/src/argus/link/udp_sequence.py`
- Test: `backend/tests/link/test_udp_sequence.py`

- [ ] **Step 1: Write failing statistics tests**

Add:

```python
def test_udp_sequence_statistics_counts_loss_late_duplicates_and_out_of_order() -> None:
    stats = summarize_sequence_results(
        sent_sequences=[1, 2, 3, 4, 5],
        replies=[
            SequenceReply(sequence=1, rtt_ms=10, late=False),
            SequenceReply(sequence=3, rtt_ms=30, late=False),
            SequenceReply(sequence=3, rtt_ms=31, late=False),
            SequenceReply(sequence=2, rtt_ms=20, late=False),
            SequenceReply(sequence=5, rtt_ms=100, late=True),
        ],
    )

    assert stats.packet_count == 5
    assert stats.packets_received == 3
    assert stats.packets_lost == 2
    assert stats.packets_duplicate == 1
    assert stats.packets_late == 1
    assert stats.packets_out_of_order == 1
    assert stats.rtt_avg_ms == 20
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_udp_sequence.py::test_udp_sequence_statistics_counts_loss_late_duplicates_and_out_of_order -q
```

Expected: FAIL because statistics helpers do not exist.

- [ ] **Step 3: Implement statistics**

Implement:

- `SequenceReply` dataclass.
- `UdpSequenceStats` dataclass.
- `summarize_sequence_results(...)`.
- RTT min/avg/p95/max and variation from on-time unique replies.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_udp_sequence.py -q
```

Expected: PASS.

## Task 3: Reflector Server

**Files:**
- Create: `backend/src/argus/link/reflector.py`
- Test: `backend/tests/link/test_reflector.py`

- [ ] **Step 1: Write failing reflector tests**

Add tests that start a UDP reflector on `127.0.0.1:0`, send an authenticated request packet, and assert a valid authenticated reply is received.

Also test that a packet with the wrong secret gets no reply.

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_reflector.py -q
```

Expected: FAIL because `argus.link.reflector` does not exist.

- [ ] **Step 3: Implement reflector**

Implement:

- `UdpSequenceReflectorProtocol(asyncio.DatagramProtocol)`.
- `start_reflector(bind_host, port, secret, key_id)`.
- CLI:
  - `--bind`
  - `--port`
  - `--secret` / `ARGUS_LINK_REFLECTOR_SECRET`
  - `--key-id`
- Conservative behavior:
  - no reply on bad auth
  - reply packet no larger than request packet
  - per-source counter map for future rate limiting

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_reflector.py -q
```

Expected: PASS.

## Task 4: Edge Agent UDP Sequence Sender

**Files:**
- Modify: `backend/src/argus/link/edge_agent.py`
- Test: `backend/tests/link/test_edge_agent.py`

- [ ] **Step 1: Write failing sender tests**

Add tests for:

- `parse_args` accepts `--method udp_sequence`, `--reflector`, `--reflector-secret`, `--packet-spacing-ms`, and `--loss-timeout-ms`.
- `run_udp_sequence_probe` sends N packets and computes stats from replies.
- Payload builder includes `method: "udp_sequence"` and richer metadata fields.

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_edge_agent.py -q
```

Expected: FAIL because only ICMP mode is implemented.

- [ ] **Step 3: Implement sender mode**

Update `edge_agent.py`:

- Add `--method` with choices `icmp_sequence` and `udp_sequence`.
- Add reflector options.
- Add `run_udp_sequence_probe(...)`.
- Use monotonic nanosecond timestamps for RTT.
- Send fixed count with configurable spacing.
- Wait until timeout for late replies and track late replies separately.
- Build sample payload with existing top-level fields plus `measurement_metadata` values supported by API.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_edge_agent.py tests/link/test_udp_sequence.py tests/link/test_reflector.py -q
```

Expected: PASS.

## Task 5: API Metadata Validation

**Files:**
- Modify: `backend/src/argus/link/api.py`
- Test: `backend/tests/api/test_link_routes.py`

- [ ] **Step 1: Write failing API tests**

Add an API test that posts a UDP sequence sample with `measurement_metadata` containing reflector address, session id, late/duplicate/out-of-order counters, timeout, packet spacing, and RTT stats. Assert the payload is stored and returned.

Add a validation test that rejects `method: "udp_sequence"` if the target is not configured as `probe_type: "udp"`.

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py::test_edge_agent_udp_sequence_sample_stores_reflector_metadata -q
```

Expected: FAIL because route validation does not understand richer UDP sequence metadata.

- [ ] **Step 3: Implement validation**

Update `LinkEdgeProbeSampleCreate` or add a UDP-specific nested metadata model:

- Preserve backward compatibility for `icmp_sequence`.
- For `udp_sequence`, require target probe type `udp`.
- Allow validated metadata fields:
  - `protocol`
  - `protocol_version`
  - `reflector_id`
  - `reflector_address`
  - `reflector_port`
  - `session_id`
  - `packets_late`
  - `packets_duplicate`
  - `packets_out_of_order`
  - `loss_timeout_ms`
  - `packet_spacing_ms`
  - `packet_size_bytes`
  - `rtt_min_ms`
  - `rtt_avg_ms`
  - `rtt_p95_ms`
  - `rtt_max_ms`
  - `rtt_variation_ms`
  - `clock_sync`

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py -q
```

Expected: PASS.

## Task 6: Frontend Configuration And Display

**Files:**
- Modify: `frontend/src/components/link/types.ts`
- Modify: `frontend/src/components/link/LinkActionDialogs.tsx`
- Modify: `frontend/src/components/link/LinkProbePanel.tsx`
- Test: `frontend/src/pages/Links.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Add tests for:

- Link path form saves reflector address, port, packet spacing, timeout, and key id.
- Monitoring card displays `UDP sequence via host:port`.
- Sample history displays received/sent, loss, RTT average, RTT variation, late, duplicate, and out-of-order counts.

- [ ] **Step 2: Run RED**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
```

Expected: FAIL because fields and display helpers do not exist.

- [ ] **Step 3: Implement UI**

Update:

- `MonitoringTarget` type with reflector fields.
- Metadata normalization for reflector fields.
- Link path dialog fields shown when source is `edge_agent` and method is `udp_sequence`, `stamp`, or `twamp`.
- Target card text.
- Sample metadata summary helper.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
```

Expected: PASS.

## Task 7: Generated API And Verification

**Files:**
- Modify if needed: `frontend/src/lib/openapi.json`
- Modify if needed: `frontend/src/lib/api.generated.ts`

- [ ] **Step 1: Regenerate OpenAPI**

Run if API schemas changed:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python -m argus.scripts.export_openapi_schema ../frontend/src/lib/openapi.json
```

- [ ] **Step 2: Regenerate frontend API types**

Run if OpenAPI changed:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm generate:api
```

- [ ] **Step 3: Full scoped verification**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_udp_sequence.py tests/link/test_reflector.py tests/link/test_edge_agent.py tests/api/test_link_routes.py tests/link/test_link_service.py -q
python3 -m uv run ruff check src/argus/link tests/link/test_udp_sequence.py tests/link/test_reflector.py tests/link/test_edge_agent.py tests/api/test_link_routes.py tests/link/test_link_service.py
python3 -m uv run mypy src/argus/link

cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
corepack pnpm lint
corepack pnpm build

cd /Users/yann.moren/vision
git diff --check
```

Expected: all pass.

- [ ] **Step 4: Commit and push**

Run:

```bash
cd /Users/yann.moren/vision
git status --short
git add backend/src/argus/link/udp_sequence.py backend/src/argus/link/reflector.py backend/src/argus/link/edge_agent.py backend/src/argus/link/api.py backend/tests/link/test_udp_sequence.py backend/tests/link/test_reflector.py backend/tests/link/test_edge_agent.py backend/tests/api/test_link_routes.py frontend/src/components/link/types.ts frontend/src/components/link/LinkActionDialogs.tsx frontend/src/components/link/LinkProbePanel.tsx frontend/src/pages/Links.test.tsx frontend/src/lib/openapi.json frontend/src/lib/api.generated.ts
git commit -m "feat: add core link reflector loss measurement"
git push origin codex/sceneops-pack-registry
```

Do not stage unrelated untracked files.
