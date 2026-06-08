# Finalize Whole-Product Smoke Gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining whole-product smoke gaps: bundled YOLO26n/YOLO26s models, deterministic detection/evidence generation, optional real RTSP validation, and billing usage generated from evidence export.

**Architecture:** Treat bundled models as release artifacts with manifest and installer checks, not ad-hoc files copied during smoke. Use a deterministic RTSP fixture from the Ultralytics sample image for repeatable detections, and keep the operator-provided camera as an optional real-source lane controlled only by local env vars. Record maritime billing usage when a maritime evidence export is created, then make the smoke harness assert History, Incidents, Evidence, Billing, and FleetOps all show real records.

**Tech Stack:** Python, pytest, FastAPI/httpx APIs, Docker Compose, MediaMTX, ffmpeg, Ultralytics sample assets, ONNXRuntime, Vezor installer shell scripts.

---

## Scope And Secret Rules

- Do not commit RTSP credentials. The operator-provided 720p and 1296p camera URLs must be passed through local env vars only:
  - `VEZOR_SMOKE_REAL_RTSP_720P_URL`
  - `VEZOR_SMOKE_REAL_RTSP_1296P_URL`
- Do not print RTSP URLs in logs. Redact values with `rtsp://***`.
- Do not call the real camera lane PASS unless the harness has actually reached the camera and completed source probe plus live stream checks.
- Do not call model bundling PASS unless both `yolo26n.onnx` and `yolo26s.onnx` are present in the release bundle and copied into the installed data model directory.

## File Map

- Create `.gitattributes`: mark bundled ONNX files for Git LFS or equivalent binary-safe tracking.
- Create `installer/assets/models/`: release-bundled model artifact directory.
- Create `installer/assets/models/manifest.json`: model names, catalog ids, relative paths, sizes, and sha256 hashes.
- Create `installer/vezor_installer/model_bundle.py`: manifest loading and bundle verification.
- Modify `installer/linux/install-master.sh`: copy bundled YOLO26 models into `$DATA_DIR/models`.
- Modify `installer/tests/test_linux_master_artifacts.py`: installer script assertions.
- Create `installer/tests/test_model_bundle.py`: release gate for model bundle presence and manifest integrity.
- Modify `installer/tests/test_release_gate.py`: include model bundle files in required product artifacts.
- Create `scripts/validation/start_detection_fixture.sh`: publish deterministic RTSP from Ultralytics `bus.jpg`.
- Create `scripts/validation/whole_product_live_smoke.py`: reusable whole-product smoke harness.
- Create `scripts/validation/README.md`: env vars, secret handling, and PASS/BLOCKED semantics.
- Modify `backend/src/argus/maritime/evidence.py`: optionally record billing usage for evidence exports.
- Modify `backend/src/argus/maritime/api.py`: pass billing service into `MaritimeEvidenceService`.
- Modify `backend/tests/maritime/test_evidence.py`: assert maritime evidence export creates billing usage.
- Modify `docs/product-installer-and-first-run-guide.md`, `docs/runbook.md`, and `docs/model-loading-and-configuration-guide.md`: document bundled YOLO26n/s and real-source smoke env vars.

---

## Task 1: Bundle YOLO26n And YOLO26s As Release Artifacts

**Files:**
- Create: `.gitattributes`
- Create: `installer/assets/models/.gitkeep`
- Create: `installer/assets/models/manifest.json`
- Create: `installer/vezor_installer/model_bundle.py`
- Test: `installer/tests/test_model_bundle.py`

- [ ] **Step 1: Add failing model bundle tests**

Create `installer/tests/test_model_bundle.py`:

```python
from __future__ import annotations

from pathlib import Path

from vezor_installer.model_bundle import verify_model_bundle

REPO_ROOT = Path(__file__).parents[2]
BUNDLE_DIR = REPO_ROOT / "installer" / "assets" / "models"


def test_bundled_yolo26_models_are_present_and_manifested() -> None:
    result = verify_model_bundle(BUNDLE_DIR)

    assert result.required_catalog_ids == {
        "yolo26n-coco-onnx",
        "yolo26s-coco-onnx",
    }
    assert result.missing_files == []
    assert result.hash_mismatches == []
    assert result.files_by_catalog_id["yolo26n-coco-onnx"].name == "yolo26n.onnx"
    assert result.files_by_catalog_id["yolo26s-coco-onnx"].name == "yolo26s.onnx"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/yann.moren/vision/installer
./.venv/bin/pytest tests/test_model_bundle.py -q
```

Expected: FAIL because `vezor_installer.model_bundle` does not exist yet.

- [ ] **Step 3: Add binary tracking and verifier implementation**

Create `.gitattributes` with:

```gitattributes
installer/assets/models/*.onnx filter=lfs diff=lfs merge=lfs -text
```

Create `installer/assets/models/.gitkeep` as an empty file.

Create `installer/vezor_installer/model_bundle.py`:

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_CATALOG_IDS = frozenset({"yolo26n-coco-onnx", "yolo26s-coco-onnx"})


@dataclass(frozen=True, slots=True)
class ModelBundleVerification:
    required_catalog_ids: set[str]
    files_by_catalog_id: dict[str, Path]
    missing_files: list[str]
    hash_mismatches: list[str]


def verify_model_bundle(bundle_dir: Path) -> ModelBundleVerification:
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("models", [])
    files_by_catalog_id: dict[str, Path] = {}
    missing_files: list[str] = []
    hash_mismatches: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        catalog_id = str(entry.get("catalog_id", ""))
        relative_path = str(entry.get("path", ""))
        if catalog_id not in REQUIRED_CATALOG_IDS:
            continue
        model_path = bundle_dir / relative_path
        files_by_catalog_id[catalog_id] = model_path
        if not model_path.exists():
            missing_files.append(relative_path)
            continue
        actual_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
        expected_sha = str(entry.get("sha256", ""))
        if actual_sha != expected_sha:
            hash_mismatches.append(relative_path)
    for catalog_id in sorted(REQUIRED_CATALOG_IDS - set(files_by_catalog_id)):
        missing_files.append(f"{catalog_id}:manifest-entry")
    return ModelBundleVerification(
        required_catalog_ids=set(REQUIRED_CATALOG_IDS),
        files_by_catalog_id=files_by_catalog_id,
        missing_files=missing_files,
        hash_mismatches=hash_mismatches,
    )


def build_manifest_entry(*, catalog_id: str, file_path: Path) -> dict[str, Any]:
    data = file_path.read_bytes()
    return {
        "catalog_id": catalog_id,
        "path": file_path.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }
```

- [ ] **Step 4: Add the model files and manifest**

Place the bundled artifacts at:

```text
installer/assets/models/yolo26n.onnx
installer/assets/models/yolo26s.onnx
```

Generate `installer/assets/models/manifest.json`:

```bash
cd /Users/yann.moren/vision
PYTHONPATH=installer installer/.venv/bin/python - <<'PY'
import json
from pathlib import Path
from vezor_installer.model_bundle import build_manifest_entry

bundle = Path("installer/assets/models")
manifest = {
    "schema_version": 1,
    "models": [
        build_manifest_entry(
            catalog_id="yolo26n-coco-onnx",
            file_path=bundle / "yolo26n.onnx",
        ),
        build_manifest_entry(
            catalog_id="yolo26s-coco-onnx",
            file_path=bundle / "yolo26s.onnx",
        ),
    ],
}
(bundle / "manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
```

If the files are not already available, export them before this step using the accepted model build process in `docs/product-installer-and-first-run-guide.md`; do not continue with fallback YOLO11 artifacts.

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
cd /Users/yann.moren/vision/installer
./.venv/bin/pytest tests/test_model_bundle.py -q
```

Expected: PASS.

---

## Task 2: Install Bundled Models Into Product Data Directory

**Files:**
- Modify: `installer/linux/install-master.sh`
- Modify: `installer/tests/test_linux_master_artifacts.py`
- Modify: `installer/tests/test_release_gate.py`

- [ ] **Step 1: Add failing installer assertions**

Append to `installer/tests/test_linux_master_artifacts.py`:

```python
def test_linux_master_installs_bundled_yolo26_models() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "install_bundled_models" in script
    assert "/opt/vezor/current/installer/assets/models" in script
    assert "$DATA_DIR/models/yolo26n.onnx" in script
    assert "$DATA_DIR/models/yolo26s.onnx" in script
    assert "sha256 mismatch for bundled model" in script
```

Add model bundle files to `REQUIRED_FILES` in `installer/tests/test_release_gate.py`:

```python
    REPO_ROOT / "installer" / "assets" / "models" / "manifest.json",
    REPO_ROOT / "installer" / "assets" / "models" / "yolo26n.onnx",
    REPO_ROOT / "installer" / "assets" / "models" / "yolo26s.onnx",
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/yann.moren/vision/installer
./.venv/bin/pytest \
  tests/test_linux_master_artifacts.py::test_linux_master_installs_bundled_yolo26_models \
  tests/test_release_gate.py::test_release_gate_required_files_exist_without_deepstream_dependency \
  -q
```

Expected: FAIL because `install-master.sh` does not copy bundled models yet.

- [ ] **Step 3: Add installer copy and sha256 verification**

In `installer/linux/install-master.sh`, after `write_backend_db_url_secret`, add:

```bash
install_bundled_models() {
  local bundle_dir="/opt/vezor/current/installer/assets/models"
  local manifest="$bundle_dir/manifest.json"

  if [[ ! -f "$manifest" ]]; then
    echo "Bundled model manifest not found: $manifest" >&2
    exit 1
  fi

  run install -d -m 0755 "$DATA_DIR/models"
  run install -m 0644 "$bundle_dir/yolo26n.onnx" "$DATA_DIR/models/yolo26n.onnx"
  run install -m 0644 "$bundle_dir/yolo26s.onnx" "$DATA_DIR/models/yolo26s.onnx"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] verify bundled YOLO26 model checksums"
    return 0
  fi

  python3 - "$bundle_dir" "$manifest" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

bundle_dir = Path(sys.argv[1])
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
for entry in manifest["models"]:
    path = bundle_dir / entry["path"]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = entry["sha256"]
    if actual != expected:
        raise SystemExit(f"sha256 mismatch for bundled model: {path.name}")
PY
}
```

Call `install_bundled_models` immediately after the existing `run install -d ... "$DATA_DIR/models" ...` directory creation block.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd /Users/yann.moren/vision/installer
./.venv/bin/pytest \
  tests/test_model_bundle.py \
  tests/test_linux_master_artifacts.py::test_linux_master_installs_bundled_yolo26_models \
  tests/test_release_gate.py::test_release_gate_required_files_exist_without_deepstream_dependency \
  -q
```

Expected: PASS.

---

## Task 3: Add Deterministic RTSP Detection Fixture

**Files:**
- Create: `scripts/validation/start_detection_fixture.sh`
- Create: `scripts/validation/README.md`
- Test: `backend/tests/scripts/test_validation_scripts.py`

- [ ] **Step 1: Add failing script tests**

Create `backend/tests/scripts/test_validation_scripts.py`:

```python
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "validation" / "start_detection_fixture.sh"


def test_detection_fixture_uses_ultralytics_sample_and_redacts_publish_url() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "ultralytics/assets/bus.jpg" in text
    assert "VEZOR_SMOKE_FIXTURE_PUBLISH_URL" in text
    assert "rtsp://***" in text
    assert "$VEZOR_SMOKE_FIXTURE_PUBLISH_URL" in text
    assert "ffmpeg" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/yann.moren/vision/backend
./.venv/bin/pytest tests/scripts/test_validation_scripts.py -q
```

Expected: FAIL because the script does not exist.

- [ ] **Step 3: Create deterministic fixture script**

Create `scripts/validation/start_detection_fixture.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${VEZOR_SMOKE_FIXTURE_PUBLISH_URL:?set the authenticated MediaMTX RTSP publish URL}"

IMAGE_PATH="$(
  "${VEZOR_SMOKE_PYTHON:-python3}" - <<'PY'
from pathlib import Path
import ultralytics

path = Path(ultralytics.__file__).resolve().parent / "assets" / "bus.jpg"
print(path)
PY
)"

if [[ ! -f "$IMAGE_PATH" ]]; then
  echo "Ultralytics detection fixture image not found: $IMAGE_PATH" >&2
  exit 1
fi

echo "Publishing deterministic detection fixture from ultralytics/assets/bus.jpg to rtsp://***"
exec ffmpeg \
  -hide_banner \
  -loglevel warning \
  -re \
  -loop 1 \
  -i "$IMAGE_PATH" \
  -vf "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2" \
  -r 10 \
  -c:v libx264 \
  -preset veryfast \
  -tune zerolatency \
  -pix_fmt yuv420p \
  -f rtsp \
  "$VEZOR_SMOKE_FIXTURE_PUBLISH_URL"
```

Run:

```bash
chmod +x /Users/yann.moren/vision/scripts/validation/start_detection_fixture.sh
```

Create `scripts/validation/README.md`:

```markdown
# Validation Scripts

`start_detection_fixture.sh` publishes a deterministic RTSP stream from the
Ultralytics `bus.jpg` sample image. It expects an authenticated MediaMTX publish
URL in `VEZOR_SMOKE_FIXTURE_PUBLISH_URL` and redacts the URL in logs.

Real camera validation is optional and uses local-only env vars:

- `VEZOR_SMOKE_REAL_RTSP_720P_URL`
- `VEZOR_SMOKE_REAL_RTSP_1296P_URL`

Never commit those values.
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/yann.moren/vision/backend
./.venv/bin/pytest tests/scripts/test_validation_scripts.py -q
```

Expected: PASS.

---

## Task 4: Record Billing Usage When Maritime Evidence Is Exported

**Files:**
- Modify: `backend/src/argus/maritime/evidence.py`
- Modify: `backend/src/argus/maritime/api.py`
- Modify: `backend/tests/maritime/test_evidence.py`

- [ ] **Step 1: Add failing evidence export billing test**

Add to `backend/tests/maritime/test_evidence.py`:

```python
from argus.billing.service import BillingService
```

Add this test:

```python
@pytest.mark.asyncio
async def test_maritime_evidence_export_records_pack_billing_usage(
    evidence_service: MaritimeEvidenceService,
) -> None:
    billing = BillingService()
    evidence_service.billing_service = billing

    export = await evidence_service.create_export(incident_id=INCIDENT_ID)

    usage = billing.list_usage(tenant_id=TENANT_ID, pack_id="maritime-fleet")
    assert len(usage) == 1
    assert usage[0].meter_key == "evidence_pack_export"
    assert usage[0].quantity == 1
    assert usage[0].source_object_type == "maritime_evidence_export"
    assert usage[0].source_object_id == export.id
    assert usage[0].metadata["incident_id"] == str(INCIDENT_ID)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/yann.moren/vision/backend
./.venv/bin/pytest tests/maritime/test_evidence.py::test_maritime_evidence_export_records_pack_billing_usage -q
```

Expected: FAIL because `MaritimeEvidenceService` has no billing hook.

- [ ] **Step 3: Add optional billing hook to evidence service**

In `backend/src/argus/maritime/evidence.py`, add a protocol near the other service classes:

```python
from typing import Protocol


class BillingUsageRecorder(Protocol):
    def record_usage(self, **kwargs: object) -> object: ...
    async def arecord_usage(self, **kwargs: object) -> object: ...
```

Extend `MaritimeEvidenceService.__init__`:

```python
        billing_service: BillingUsageRecorder | None = None,
```

Set:

```python
        self.billing_service = billing_service
```

After the export row is created in `create_export`, call a helper:

```python
        await self._record_export_usage(export)
        return export
```

Add helper method:

```python
    async def _record_export_usage(self, export: MaritimeEvidenceExportRecord) -> None:
        if self.billing_service is None:
            return
        recorder = getattr(self.billing_service, "arecord_usage", None)
        if recorder is None:
            self.billing_service.record_usage(
                tenant_id=self.tenant_id,
                meter_key="evidence_pack_export",
                quantity=1,
                source_object_type="maritime_evidence_export",
                source_object_id=export.id,
                pack_id="maritime-fleet",
                metadata={"incident_id": str(export.incident_id)},
            )
            return
        await recorder(
            tenant_id=self.tenant_id,
            meter_key="evidence_pack_export",
            quantity=1,
            source_object_type="maritime_evidence_export",
            source_object_id=export.id,
            pack_id="maritime-fleet",
            metadata={"incident_id": str(export.incident_id)},
        )
```

In `backend/src/argus/maritime/api.py`, pass billing into `_maritime_evidence_service`:

```python
        billing_service=services.billing,
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd /Users/yann.moren/vision/backend
./.venv/bin/pytest \
  tests/maritime/test_evidence.py::test_maritime_evidence_export_records_pack_billing_usage \
  tests/maritime/test_billing_support.py \
  -q
```

Expected: PASS.

---

## Task 5: Build Whole-Product Smoke Harness

**Files:**
- Create: `scripts/validation/whole_product_live_smoke.py`
- Test: `backend/tests/scripts/test_whole_product_live_smoke.py`

- [ ] **Step 1: Add failing harness tests**

Create `backend/tests/scripts/test_whole_product_live_smoke.py`:

```python
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "validation" / "whole_product_live_smoke.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("whole_product_live_smoke", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_status_names_distinguish_blocked_and_not_run() -> None:
    module = _load_module()

    assert [status.value for status in module.SmokeStatus] == [
        "PASS",
        "FAIL",
        "BLOCKED",
        "NOT RUN",
    ]


def test_rtsp_redaction_keeps_credentials_out_of_report() -> None:
    module = _load_module()

    assert module.redact_rtsp_url("rtsp://user:pass@host/ch1") == "rtsp://***@host/ch1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/yann.moren/vision/backend
./.venv/bin/pytest tests/scripts/test_whole_product_live_smoke.py -q
```

Expected: FAIL because the harness does not exist.

- [ ] **Step 3: Create harness skeleton with status model and redaction**

Create `scripts/validation/whole_product_live_smoke.py`:

```python
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import httpx

RTSP_CREDENTIAL_RE = re.compile(r"^(rtsp://)([^/@]+)@(.+)$")


class SmokeStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT RUN"


@dataclass(slots=True)
class SmokeCheck:
    name: str
    status: SmokeStatus
    evidence: list[str] = field(default_factory=list)


def redact_rtsp_url(value: str) -> str:
    return RTSP_CREDENTIAL_RE.sub(r"\1***@\3", value)


def require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def write_report(path: Path, checks: list[SmokeCheck]) -> None:
    payload = {
        "checks": [
            {"name": check.name, "status": check.status.value, "evidence": check.evidence}
            for check in checks
        ]
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--report", required=True)
    parser.add_argument("--real-rtsp", choices=["none", "720p", "1296p"], default="none")
    args = parser.parse_args(argv)

    checks = [
        SmokeCheck("status taxonomy", SmokeStatus.PASS, ["PASS/FAIL/BLOCKED/NOT RUN active"]),
    ]
    write_report(Path(args.report), checks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd /Users/yann.moren/vision/backend
./.venv/bin/pytest tests/scripts/test_whole_product_live_smoke.py -q
```

Expected: PASS.

- [ ] **Step 5: Extend harness to exercise product paths**

Extend the harness in small TDD slices. Each slice adds one fake-client unit test first, then implementation:

1. Auth and first-run status: assert first-run required before bootstrap and false after.
2. Model bundle registration: register `yolo26n-coco-onnx` and `yolo26s-coco-onnx`; fail if artifact missing.
3. Deterministic fixture: create MediaMTX path, start `start_detection_fixture.sh`, source-probe fixture stream, create camera with YOLO26n.
4. Incident rule: apply maritime template or create a rule for `person`/`bus` detections with `record_clip`.
5. Worker lifecycle: create supervised assignment, start lifecycle, wait for fresh `running` runtime report.
6. Evidence: wait for at least one incident, call `/api/v1/maritime/evidence-exports`, assert export count and artifact hashes.
7. Billing: assert `/api/v1/maritime/billing/usage` contains an `evidence_pack_export` row from the export.
8. Real RTSP optional lane: if `--real-rtsp 720p`, use `VEZOR_SMOKE_REAL_RTSP_720P_URL`; if `--real-rtsp 1296p`, use `VEZOR_SMOKE_REAL_RTSP_1296P_URL`; otherwise record NOT RUN.

---

## Task 6: Real RTSP Camera Validation Lane

**Files:**
- Modify: `scripts/validation/whole_product_live_smoke.py`
- Modify: `scripts/validation/README.md`

- [ ] **Step 1: Add real RTSP BLOCKED/NOT RUN semantics**

Add harness logic:

```python
def real_rtsp_env_name(selection: str) -> str | None:
    if selection == "720p":
        return "VEZOR_SMOKE_REAL_RTSP_720P_URL"
    if selection == "1296p":
        return "VEZOR_SMOKE_REAL_RTSP_1296P_URL"
    return None
```

Expected behavior:

- `--real-rtsp none`: report `Real RTSP source` as NOT RUN.
- `--real-rtsp 720p` with missing env var: report BLOCKED.
- `--real-rtsp 1296p` with missing env var: report BLOCKED.
- Env var present but source probe fails: report FAIL with redacted URL.
- Env var present and source probe/live succeeds: report PASS with resolution/fps/codec.

- [ ] **Step 2: Add unit test for redacted real RTSP report**

Append to `backend/tests/scripts/test_whole_product_live_smoke.py`:

```python
def test_real_rtsp_env_selection_does_not_expose_url() -> None:
    module = _load_module()

    assert module.real_rtsp_env_name("720p") == "VEZOR_SMOKE_REAL_RTSP_720P_URL"
    assert module.real_rtsp_env_name("1296p") == "VEZOR_SMOKE_REAL_RTSP_1296P_URL"
    assert module.real_rtsp_env_name("none") is None
```

- [ ] **Step 3: Run tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
./.venv/bin/pytest tests/scripts/test_whole_product_live_smoke.py -q
```

Expected: PASS.

---

## Task 7: Docs And Final Acceptance Gate

**Files:**
- Modify: `docs/product-installer-and-first-run-guide.md`
- Modify: `docs/runbook.md`
- Modify: `docs/model-loading-and-configuration-guide.md`
- Modify: `docs/superpowers/status/2026-06-08-next-chat-whole-product-live-smoke-handoff.md`

- [ ] **Step 1: Document bundled YOLO26 models**

Add wording:

```markdown
The Linux master appliance bundles `yolo26n.onnx` and `yolo26s.onnx` in
`installer/assets/models/`. During install, the bundle is copied into
`/var/lib/vezor/models/` and mounted into containers at `/models`.
First-run smoke validation must register `/models/yolo26n.onnx` and
`/models/yolo26s.onnx`; falling back to YOLO11 is a BLOCKED result for the
YOLO26 bundle check.
```

- [ ] **Step 2: Document deterministic and real RTSP smoke modes**

Add wording:

~~~markdown
Use deterministic smoke first:

```bash
scripts/validation/whole_product_live_smoke.py \
  --api-url http://127.0.0.1:8000 \
  --report /tmp/vezor-whole-smoke/report.json \
  --real-rtsp none
```

Use real RTSP only after deterministic smoke passes. Store camera URLs in a
local env file outside the repository and source it before running:

```bash
set -a
. /tmp/vezor-real-camera.env
set +a
scripts/validation/whole_product_live_smoke.py \
  --api-url http://127.0.0.1:8000 \
  --report /tmp/vezor-whole-smoke/report-real-720p.json \
  --real-rtsp 720p
```
~~~

- [ ] **Step 3: Run docs consistency checks**

Run:

```bash
cd /Users/yann.moren/vision
rg -n "yolo26n|yolo26s|whole_product_live_smoke|VEZOR_SMOKE_REAL_RTSP" \
  docs/product-installer-and-first-run-guide.md \
  docs/runbook.md \
  docs/model-loading-and-configuration-guide.md
```

Expected: each doc contains the updated bundle/smoke guidance.

---

## Task 8: Final Whole-Product Validation Run

**Files:**
- No source edits unless the validation reveals a confirmed blocker.

- [ ] **Step 1: Run focused automated tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
./.venv/bin/pytest \
  tests/scripts/test_validation_scripts.py \
  tests/scripts/test_whole_product_live_smoke.py \
  tests/maritime/test_evidence.py \
  tests/maritime/test_billing_support.py \
  -q

cd /Users/yann.moren/vision/installer
./.venv/bin/pytest \
  tests/test_model_bundle.py \
  tests/test_linux_master_artifacts.py \
  tests/test_release_gate.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Rebuild and run deterministic smoke**

Run the same targeted destructive reset rules from the existing handoff, rebuild the product images, start the fresh stack, complete first-run, then run:

```bash
cd /Users/yann.moren/vision
backend/.venv/bin/python scripts/validation/whole_product_live_smoke.py \
  --api-url http://127.0.0.1:8000 \
  --report /tmp/vezor-whole-smoke/final-deterministic-smoke.json \
  --real-rtsp none
```

Expected report:

- YOLO26n bundle/register: PASS
- YOLO26s bundle/register: PASS
- deterministic RTSP source: PASS
- worker runtime: PASS
- Live: PASS
- History: PASS
- Incidents: PASS
- Maritime evidence export: PASS
- Maritime billing usage: PASS
- Real RTSP source: NOT RUN

- [ ] **Step 3: Run optional real camera smoke**

Create `/tmp/vezor-real-camera.env` locally with the operator-provided 720p and 1296p camera URLs. Do not commit or print the file.

Run:

```bash
set -a
. /tmp/vezor-real-camera.env
set +a
cd /Users/yann.moren/vision
backend/.venv/bin/python scripts/validation/whole_product_live_smoke.py \
  --api-url http://127.0.0.1:8000 \
  --report /tmp/vezor-whole-smoke/final-real-720p-smoke.json \
  --real-rtsp 720p
```

Expected report:

- Real RTSP source: PASS if reachable and source-probe/live checks succeed.
- Real RTSP source: BLOCKED if network access to the camera is unavailable.
- Real RTSP source: FAIL if reachable but product source-probe/live checks fail.

- [ ] **Step 4: Final diff and verification**

Run:

```bash
cd /Users/yann.moren/vision
git diff --check
git status --short
```

Expected: no whitespace errors; only intended source/doc changes plus existing unrelated untracked files.

## Acceptance Criteria

- `yolo26n.onnx` and `yolo26s.onnx` are physically present in the installer model bundle and copied to installed `/models`.
- The smoke harness never uses YOLO11 as a substitute for YOLO26 bundle validation.
- Deterministic RTSP smoke generates at least one detection-backed incident.
- Maritime evidence export is created from the incident.
- Maritime billing usage contains an `evidence_pack_export` row tied to that export.
- Real RTSP lane reports PASS, FAIL, BLOCKED, or NOT RUN honestly, with RTSP credentials redacted.
- Final whole-product report distinguishes PASS, FAIL, BLOCKED, and NOT RUN.
