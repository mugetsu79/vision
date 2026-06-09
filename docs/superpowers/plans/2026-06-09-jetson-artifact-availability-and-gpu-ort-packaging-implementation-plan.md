# Jetson Artifact Availability and GPU ORT Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Jetson GPU ONNX Runtime packaging automatic and make edge-built TensorRT artifacts appear as valid runtime artifacts in the UI only after target-local validation.

**Architecture:** Add a trusted Jetson ORT wheel resolver to installer manifests and move the edge Dockerfile from operator-provided URL to manifest-resolved URL+SHA256. Add runtime artifact reconciliation so actual edge-built artifact paths are validated against edge inventory before the master/UI marks them ready.

**Tech Stack:** Bash installers, Python manifest resolver, Dockerfile edge build, FastAPI, SQLAlchemy, pytest, Vitest.

---

## File Structure

- Modify: `installer/vezor_installer/manifest.py`
  - Parse Jetson ORT wheel entries with `jetpack`, `l4t`, `python`, `arch`, `url`, and `sha256`.
- Create: `installer/vezor_installer/jetson_ort.py`
  - Resolve the best wheel entry from Jetson preflight JSON.
- Modify: `installer/manifests/dev-example.json`
  - Add a non-secret Jetson ORT wheel entry with SHA256.
- Modify: `installer/linux/install-edge.sh`
  - Resolve ORT wheel automatically before `build_local_edge_image`.
- Modify: `backend/Dockerfile.edge`
  - Verify wheel SHA256 before installing and run an ONNX Runtime provider probe.
- Modify: `installer/tests/test_manifest.py`
  - Cover manifest parsing and digest validation.
- Create: `installer/tests/test_jetson_ort_resolver.py`
  - Cover resolver selection and fail-closed cases.
- Modify: `installer/tests/test_edge_installer_artifacts.py`
  - Assert installer no longer requires manual wheel URL in normal manifest mode.
- Modify: `backend/src/argus/supervisor/model_jobs.py`
  - Include `validation_status=valid` only after local file validation succeeds.
- Modify: `backend/src/argus/api/v1/runtime_artifacts.py`
  - Add or tighten reconciliation from build completion and edge inventory.
- Modify: `backend/tests/supervisor/test_artifact_build_jobs.py`
  - Cover actual runtime-artifacts path payload and validation status.
- Modify: `backend/tests/api/test_runtime_artifact_routes.py`
  - Cover artifact reconciliation from edge inventory.
- Modify: `frontend/src/pages/Models.tsx`
  - Stop presenting static catalog engine paths as missing artifacts when actual runtime artifacts exist.
- Modify: `frontend/src/pages/Models.test.tsx`
  - Cover built-but-unvalidated, valid, and stale static-path UI states.
- Modify: `docs/product-installer-and-first-run-guide.md`
  - Document automatic GPU ORT packaging and the diagnostic-only CPU fallback.

## Task 1: Manifest-Based Jetson ORT Wheel Resolution

- [ ] **Step 1: Write failing manifest tests**

Add to `installer/tests/test_manifest.py`:

```python
def test_manifest_parses_jetson_ort_wheels() -> None:
    manifest = ReleaseManifest.model_validate(
        {
            "schema_version": 1,
            "release_channel": "dev",
            "images": {},
            "jetson_ort_wheels": [
                {
                    "jetpack": "6.2",
                    "l4t": "36.4",
                    "python": "cp310",
                    "arch": "aarch64",
                    "url": "https://example.invalid/onnxruntime_gpu.whl",
                    "sha256": "a" * 64,
                }
            ],
        }
    )

    assert manifest.jetson_ort_wheels[0].python == "cp310"
    assert manifest.jetson_ort_wheels[0].sha256 == "a" * 64
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m uv run --project installer pytest installer/tests/test_manifest.py::test_manifest_parses_jetson_ort_wheels -q
```

Expected: FAIL because the manifest model does not expose `jetson_ort_wheels`.

- [ ] **Step 3: Add manifest models**

In `installer/vezor_installer/manifest.py`, add:

```python
class JetsonOrtWheel(BaseModel):
    jetpack: str
    l4t: str
    python: str
    arch: str
    url: AnyUrl
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
```

and add `jetson_ort_wheels: list[JetsonOrtWheel] = Field(default_factory=list)`
to `ReleaseManifest`.

- [ ] **Step 4: Run manifest tests**

Run:

```bash
python3 -m uv run --project installer pytest installer/tests/test_manifest.py -q
```

Expected: PASS.

## Task 2: Resolver And Installer Integration

- [ ] **Step 1: Write failing resolver tests**

Create `installer/tests/test_jetson_ort_resolver.py`:

```python
from installer.vezor_installer.jetson_ort import resolve_jetson_ort_wheel


def test_resolves_matching_jetson_ort_wheel() -> None:
    preflight = {
        "arch": "arm64",
        "jetpack": "6.2",
        "l4t": "36.4.0",
        "python_abi": "cp310",
    }
    wheels = [
        {
            "jetpack": "6.2",
            "l4t": "36.4",
            "python": "cp310",
            "arch": "aarch64",
            "url": "https://example.invalid/ort.whl",
            "sha256": "b" * 64,
        }
    ]

    resolved = resolve_jetson_ort_wheel(preflight, wheels)

    assert resolved.url == "https://example.invalid/ort.whl"
    assert resolved.sha256 == "b" * 64


def test_resolver_fails_closed_when_no_wheel_matches() -> None:
    preflight = {"arch": "arm64", "jetpack": "6.2", "l4t": "36.4.0", "python_abi": "cp310"}

    try:
        resolve_jetson_ort_wheel(preflight, [])
    except ValueError as exc:
        assert "No Jetson GPU ONNX Runtime wheel" in str(exc)
    else:
        raise AssertionError("resolver must fail closed")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m uv run --project installer pytest installer/tests/test_jetson_ort_resolver.py -q
```

Expected: FAIL because the resolver does not exist.

- [ ] **Step 3: Implement resolver**

Create `installer/vezor_installer/jetson_ort.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ResolvedJetsonOrtWheel:
    url: str
    sha256: str


def resolve_jetson_ort_wheel(
    preflight: Mapping[str, object],
    wheels: Sequence[Mapping[str, object]],
) -> ResolvedJetsonOrtWheel:
    arch = "aarch64" if preflight.get("arch") in {"arm64", "aarch64"} else str(preflight.get("arch", ""))
    jetpack = str(preflight.get("jetpack", ""))
    l4t = str(preflight.get("l4t", ""))
    python_abi = str(preflight.get("python_abi", "cp310"))

    for wheel in wheels:
        if str(wheel.get("arch")) != arch:
            continue
        if str(wheel.get("python")) != python_abi:
            continue
        if str(wheel.get("jetpack")) != jetpack:
            continue
        if not l4t.startswith(str(wheel.get("l4t"))):
            continue
        return ResolvedJetsonOrtWheel(
            url=str(wheel["url"]),
            sha256=str(wheel["sha256"]),
        )

    raise ValueError(
        f"No Jetson GPU ONNX Runtime wheel for arch={arch} jetpack={jetpack} l4t={l4t} python={python_abi}."
    )
```

- [ ] **Step 4: Integrate installer**

Modify `installer/linux/install-edge.sh`:

- capture `scripts/jetson-preflight.sh --installer --json` output into a temp file;
- if `JETSON_ORT_WHEEL_URL` is empty and manifest has `jetson_ort_wheels`, call
  `python3 -m installer.vezor_installer.jetson_ort "$MANIFEST" "$PREFLIGHT_JSON"`;
- export both `JETSON_ORT_WHEEL_URL` and `JETSON_ORT_WHEEL_SHA256`;
- fail unless a GPU wheel was resolved or `--allow-cpu-onnx-runtime` was
  explicitly passed.

- [ ] **Step 5: Verify installer tests**

Run:

```bash
python3 -m uv run --project installer pytest installer/tests/test_jetson_ort_resolver.py installer/tests/test_edge_installer_artifacts.py -q
scripts/validate-installers.sh
```

Expected: PASS.

## Task 3: Dockerfile Digest Verification And Provider Probe

- [ ] **Step 1: Write failing Dockerfile tests**

Update `backend/tests/core/test_edge_dockerfile.py`:

```python
def test_edge_dockerfile_verifies_gpu_ort_wheel_digest() -> None:
    dockerfile = EDGE_DOCKERFILE.read_text(encoding="utf-8")

    assert "ARG JETSON_ORT_WHEEL_SHA256" in dockerfile
    assert "sha256sum -c" in dockerfile
    assert "onnxruntime as ort" in dockerfile
    assert "get_available_providers" in dockerfile
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/core/test_edge_dockerfile.py::test_edge_dockerfile_verifies_gpu_ort_wheel_digest -q
```

Expected: FAIL because the Dockerfile does not verify wheel SHA256.

- [ ] **Step 3: Update `backend/Dockerfile.edge`**

Add `ARG JETSON_ORT_WHEEL_SHA256=""`. Replace direct URL install with:

```dockerfile
RUN if [ -n "$JETSON_ORT_WHEEL_URL" ]; then \
        curl -fsSL "$JETSON_ORT_WHEEL_URL" -o /tmp/onnxruntime_gpu.whl; \
        echo "$JETSON_ORT_WHEEL_SHA256  /tmp/onnxruntime_gpu.whl" | sha256sum -c -; \
        "$UV_PROJECT_ENVIRONMENT/bin/pip" install --no-cache-dir /tmp/onnxruntime_gpu.whl; \
        rm -f /tmp/onnxruntime_gpu.whl; \
    elif [ "$ALLOW_CPU_ONNX_RUNTIME" = "1" ]; then \
        "$UV_PROJECT_ENVIRONMENT/bin/pip" install --no-cache-dir "onnxruntime>=1.20"; \
    else \
        echo "A verified Jetson GPU ONNX Runtime wheel is required." >&2; \
        exit 1; \
    fi \
    && "$UV_PROJECT_ENVIRONMENT/bin/python" -c "import onnxruntime as ort; print(ort.__version__, ort.get_available_providers())"
```

- [ ] **Step 4: Run Dockerfile tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/core/test_edge_dockerfile.py -q
```

Expected: PASS.

## Task 4: Runtime Artifact Validation And Reconciliation

- [ ] **Step 1: Write failing supervisor test**

Update `backend/tests/supervisor/test_artifact_build_jobs.py`:

```python
async def test_tensorrt_artifact_build_reports_actual_validated_runtime_path(tmp_path):
    output_dir = tmp_path / "runtime-artifacts"
    source = tmp_path / "yolo26n.onnx"
    source.write_bytes(b"onnx")
    builder = FakeTensorRTBuilder(output_bytes=b"engine")
    job = _artifact_job(
        payload={
            "job_type": "artifact_build",
            "model_id": str(uuid4()),
            "source_model_path": str(source),
            "source_model_sha256": hashlib.sha256(b"onnx").hexdigest(),
            "output_dir": str(output_dir),
            "build_format": "tensorrt_engine",
            "target_profile": "linux-aarch64-nvidia-jetson",
        }
    )

    executor = SupervisorModelJobExecutor(
        client=FakeOperationsClient(),
        tensorrt_engine_builder=builder,
        artifact_store_path=output_dir,
    )
    completed = await executor.execute_runtime_artifact_build(job)

    artifact = completed.payload["artifact"]
    assert artifact["path"].endswith("/yolo26n.engine")
    assert artifact["validation_status"] == "valid"
    assert artifact["sha256"] == hashlib.sha256(b"engine").hexdigest()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/supervisor/test_artifact_build_jobs.py::test_tensorrt_artifact_build_reports_actual_validated_runtime_path -q
```

Expected: FAIL because fixed-vocab artifacts are currently reported as unvalidated.

- [ ] **Step 3: Implement local validation**

Update `backend/src/argus/supervisor/model_jobs.py` so fixed-vocab TensorRT
artifact payloads are marked `valid` only when:

- the output file exists;
- the file size is greater than zero;
- the computed SHA256 equals the payload SHA256;
- target profile and source model SHA256 are present.

- [ ] **Step 4: Add master reconciliation test**

Add to `backend/tests/api/test_runtime_artifact_routes.py`:

```python
async def test_artifact_completion_reconciles_actual_edge_inventory_path(client, edge_node, model):
    completion = {
        "artifact": {
            "model_id": str(model.id),
            "kind": "tensorrt_engine",
            "path": "/models/runtime-artifacts/model/yolo26n.engine",
            "target_profile": "linux-aarch64-nvidia-jetson",
            "sha256": "c" * 64,
            "size_bytes": 8327412,
            "validation_status": "valid",
        }
    }

    response = await client.post(
        f"/api/v1/deployment/model-sync-jobs/{edge_node.id}/complete",
        json=completion,
    )

    assert response.status_code == 200
    artifacts = await client.get(f"/api/v1/models/{model.id}/runtime-artifacts")
    assert artifacts.json()[0]["path"] == "/models/runtime-artifacts/model/yolo26n.engine"
    assert artifacts.json()[0]["validation_status"] == "valid"
```

- [ ] **Step 5: Run backend artifact tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/supervisor/test_artifact_build_jobs.py backend/tests/api/test_runtime_artifact_routes.py -q
```

Expected: PASS.

## Task 5: Models UI Artifact State

- [ ] **Step 1: Write failing UI test**

Update `frontend/src/pages/Models.test.tsx`:

```tsx
test("shows actual validated edge-built TensorRT artifact instead of stale static engine path", async () => {
  server.use(
    http.get("/api/v1/models", () =>
      HttpResponse.json([
        {
          id: "model-1",
          name: "YOLO26n COCO",
          path: "models/yolo26n.onnx",
          runtime_artifacts: [
            {
              id: "artifact-1",
              kind: "tensorrt_engine",
              path: "/models/runtime-artifacts/model-1/yolo26n.engine",
              target_profile: "linux-aarch64-nvidia-jetson",
              validation_status: "valid",
            },
          ],
        },
      ]),
    ),
  );

  renderWithProviders(<ModelsPage />);

  await screen.findByText("Runtime artifact ready");
  expect(screen.getByText("/models/runtime-artifacts/model-1/yolo26n.engine")).toBeInTheDocument();
  expect(screen.queryByText("models/yolo26n.engine")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
corepack pnpm --dir frontend test src/pages/Models.test.tsx -t "actual validated edge-built TensorRT"
```

Expected: FAIL if the UI still renders static engine catalog rows.

- [ ] **Step 3: Update Models UI**

Change `frontend/src/pages/Models.tsx` so the runtime-artifacts panel:

- derives TensorRT readiness from `model.runtime_artifacts`;
- labels `unvalidated` as "Built on edge, awaiting validation";
- labels `valid` as "Runtime artifact ready";
- hides static engine catalog rows when the canonical ONNX model has a matching
  runtime artifact for the same target profile.

- [ ] **Step 4: Run frontend tests**

Run:

```bash
corepack pnpm --dir frontend test src/pages/Models.test.tsx
corepack pnpm --dir frontend exec tsc -b
```

Expected: PASS.

## Task 6: Installed Jetson Smoke

- [ ] **Step 1: Rebuild edge image without manual wheel URL**

Run the edge installer on Jetson without `--jetson-ort-wheel-url` and without
`--allow-cpu-onnx-runtime`.

Expected: installer resolves the GPU ORT wheel from the manifest and edge image
build succeeds.

- [ ] **Step 2: Verify providers**

Run:

```bash
ssh ai-user@JETSON 'docker run --rm vezor/edge-worker:portable-demo /app/.venv/bin/python -c "import onnxruntime as ort; print(ort.get_available_providers())"'
```

Expected: output includes accelerated Jetson providers and not only
`CPUExecutionProvider`.

- [ ] **Step 3: Build and validate TensorRT artifact**

Trigger a YOLO26n TensorRT build from Models -> Runtime artifacts.

Expected:

- `/var/lib/vezor/models/runtime-artifacts/.../yolo26n.engine` exists on Jetson;
- master DB artifact row has `validation_status=valid`;
- Models UI shows the actual runtime-artifacts path as ready;
- no static `models/yolo26n.engine` missing-artifact row is displayed.
