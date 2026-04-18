# ADR-0002: Central GPU Provisioning for HQ Inference

**Status:** Accepted
**Date:** 2026-04-18
**Deciders:** Platform owner (Yann), infra lead, finance (capex sign-off)
**Related:** `argus_v4_spec.md` §2.2 (process model), §3.2 (edge hardware), §3.3 (central hardware), `ADR-0001-identity-provider.md`

## Context

V3 runs in a **true-hybrid** topology. Cameras marked `central` or `hybrid` have their RTSP decoded + inferred at HQ, which requires a GPU at the central node. Constraints from the spec:

- **Scope:** mid-scale VMS, up to 50 sites and 250 cameras total. Expected steady-state central load: **30–50 concurrent streams**, with bursts to 75 during peak traffic hours or multi-site replay.
- **Per-stream budget (reference workload):** YOLO12n FP16 @ 640×640, BoT-SORT, optional PPE secondary classifier, homography speed calc, privacy blur, WHIP push with NVENC. Measured on L4 24 GB: ~350 MB VRAM and ~3% GPU utilisation per 25 fps stream.
- **Hard requirements:** hardware video encode (NVENC) — the edge Jetson Orin Nano lacks it, so the annotated-frame re-encode for live overlay can only happen centrally. TensorRT 10 support. INT8 support for future quantized models. PCIe form factor that fits 2U / 4U rack and standard workstation chassis.
- **Soft requirements:** low TDP (fits existing colocation power budget), good resale path (public-cloud equivalents available for staging), CUDA 12.6+ driver compatibility.

Non-functional requirements: **reliability (no single GPU as sole failure domain once past 75 streams)**, **headroom for a local LLM fallback** (running a small Llama 3.x / Qwen for air-gapped deployments on the same box is desirable), and **operating-cost predictability** over a 3-year amortization window.

## Decision

**Start with 1× NVIDIA L4 (24 GB PCIe)** in the central node. Plan an upgrade path to **2× L4** when sustained central stream count exceeds 50, and to **1× L40S (48 GB)** when an on-prem LLM is co-resident or when the central stream count passes ~100. Defer H100 / multi-GPU clustering until enterprise-tier scale (ADR-0003 when that happens).

## Options Considered

### Option A: 1× NVIDIA L4 24 GB (chosen baseline)

| Dimension         | Assessment                                                                |
|-------------------|---------------------------------------------------------------------------|
| Architecture      | Ada Lovelace, 7424 CUDA + 58 4th-gen Tensor cores, FP8 native             |
| Memory            | 24 GB GDDR6                                                               |
| TDP               | **72 W** (single-slot, low-profile, passive)                              |
| Video engines     | 2× NVENC (AV1+H.264+H.265), 4× NVDEC — strong for VMS workload            |
| Street price (2026)| ~$2,400 new; ~$1,700 refurb                                              |
| Cloud equivalent  | AWS `g6.xlarge`, GCP `g2-standard-4` — great for CI / staging parity      |
| 50-stream headroom| Yes: ~18 GB VRAM used, ~60% SM util, still leaves room for PPE classifier |
| LLM co-tenancy    | Tight: Llama 3.1 8B Q4 fits (~6 GB) but crowds inference at peak          |

**Pros:** Best perf-per-watt in the Ada family for this workload; single-slot passive card drops into any 2U chassis; cloud-equivalent exists so dev/staging can match prod; NVENC bank is generous enough to annotate and re-stream all central cameras simultaneously.
**Cons:** 24 GB becomes tight if a local LLM is co-located or class count grows with large secondary models; no card-level redundancy; Ada tensor perf is below L40S by ~3×.

### Option B: 1× NVIDIA L40S 48 GB

| Dimension         | Assessment                                                                |
|-------------------|---------------------------------------------------------------------------|
| Architecture      | Ada Lovelace, 18176 CUDA + 568 Tensor cores, FP8 native                   |
| Memory            | 48 GB GDDR6 ECC                                                           |
| TDP               | 350 W (dual-slot, active)                                                 |
| Video engines     | 3× NVENC, 3× NVDEC                                                        |
| Street price (2026)| ~$8,500 new                                                             |
| 50-stream headroom| Huge; room for concurrent on-prem LLM + heavier secondary models          |

**Pros:** Comfortably co-hosts a 7–13 B LLM alongside inference; ECC memory; 3-year headroom.
**Cons:** 4× the cost of an L4; needs active cooling + more rack power; overkill until stream count doubles or on-prem LLM is mandatory.

### Option C: 1× NVIDIA RTX A4000 / RTX 4000 Ada 20 GB

| Dimension         | Assessment                                                                |
|-------------------|---------------------------------------------------------------------------|
| Memory            | 16–20 GB GDDR6                                                            |
| TDP               | 140 W (dual-slot, active)                                                 |
| Street price (2026)| ~$1,200 (A4000) / ~$1,400 (4000 Ada)                                    |
| 50-stream headroom| Borderline: ~14 GB VRAM at 50 streams, hits thermal limits                |

**Pros:** Cheapest sensible option; plentiful secondhand supply.
**Cons:** Thermally cramped in a 2U rack; no cloud parity (not a standard datacenter SKU); fewer NVENC sessions; A4000 is already 2 generations old.

### Option D: 2× NVIDIA T4 16 GB

**Pros:** Proven VMS card, low TDP (70 W each), cheap used (~$500 each).
**Cons:** Turing is EOL for new drivers; FP8 unsupported; no TRT 10 longevity; rejected.

### Option E: AMD MI210 / Intel Gaudi / Consumer RTX 4090

Rejected. AMD ROCm + ONNX Runtime + TensorRT tooling is not on par; Gaudi is Habana-specific and painful outside its own SDK; RTX 4090 lacks datacenter thermals / ECC / passive cooling and has no NVENC session headroom for >3 concurrent streams (driver limitation on consumer cards).

## Trade-off Analysis

The decision axes are **stream capacity at steady state**, **NVENC session count**, **power/cooling**, and **cost**. L4 hits the sweet spot at mid-scale: 50 streams at <70% GPU with a passive 72 W card that fits any chassis. L40S is 4× the cost for ~3× the headroom we do not yet need. A4000/4000 Ada saves capex but eats the margin via thermal derating and gives up cloud parity. T4 is dead. The consumer alternatives are non-starters in a production VMS.

The upgrade path matters as much as the baseline. L4 → 2× L4 is mechanically trivial (same TDP, same cooling, same driver) and gives deterministic scale-out. L4 → L40S is a forklift change; we do it only if a co-resident LLM becomes mandatory.

## Consequences

**Becomes easier:**
- Match cloud (AWS `g6`, GCP `g2`) to on-prem for staging and disaster recovery.
- Annotate + re-stream all central cameras via NVENC without CPU fallback.
- Hit the 50-camera target at steady state within the initial capex envelope (~$2.5k card + ~$3k chassis).

**Becomes harder:**
- Running an on-prem LLM > 7 B parameters *and* 50 streams on the same card — we will fall back to a separate L4 or push LLM to a cloud provider.
- Adding large secondary models (e.g. a 200 MB vision-language model) at scale — track VRAM.
- Redundancy: a single L4 is a SPoF until we deploy the second one. Mitigate via camera-side `edge` failover for the most critical sites.

**To revisit:**
- When central stream count passes **50 sustained** or **75 peak** — add second L4.
- When a customer contract requires an on-prem LLM — upgrade path: swap to L40S or add a second dedicated L4 for LLM only.
- At V3.2 cycle — reassess whether H100 PCIe / B40-class cards make sense as price decays.

## Action Items

1. [ ] Capex request: 1× NVIDIA L4 24 GB + 2U chassis with ≥1 passive-cooling-compatible PCIe slot.
2. [ ] Staging parity: provision an AWS `g6.xlarge` or GCP `g2-standard-4` for CI end-to-end tests.
3. [ ] Benchmark: run the Prompt 3 Jetson bench (adapted) on the L4 and confirm ≥50 streams at 25 fps with the full pipeline enabled. Record results in `docs/benchmarks/central-l4.md`.
4. [ ] Driver + runtime pinning: NVIDIA driver ≥ 560, CUDA 12.6, TensorRT 10.x. Document in `infra/central/README.md`.
5. [ ] Prometheus exporter for `nvidia-smi` to track VRAM, NVENC sessions, and SM utilization; alert at 80% of any.
6. [ ] Capacity review on the first day the fleet exceeds 40 central streams; trigger the 2× L4 procurement when we cross 50.
