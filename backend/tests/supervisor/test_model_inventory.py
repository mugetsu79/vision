from __future__ import annotations

import hashlib
from datetime import datetime
from uuid import uuid4

from argus.compat import UTC
from argus.supervisor.model_inventory import InventoryScanner


def test_inventory_scanner_reports_hash_size_and_path(tmp_path) -> None:
    model_path = tmp_path / "yolo26n.onnx"
    model_bytes = b"deterministic model bytes"
    model_path.write_bytes(model_bytes)
    asset_id = uuid4()
    scanner = InventoryScanner(
        reported_at=lambda: datetime(2026, 6, 8, 9, 0, tzinfo=UTC),
        target_profile="linux-aarch64-nvidia-jetson",
        runtime_versions={"onnxruntime": "1.20.0"},
    )

    items = scanner.scan_models([{"asset_id": asset_id, "local_path": model_path}])

    assert len(items) == 1
    assert items[0].asset_kind == "model"
    assert items[0].asset_id == asset_id
    assert items[0].local_path == str(model_path)
    assert items[0].sha256 == hashlib.sha256(model_bytes).hexdigest()
    assert items[0].size_bytes == len(model_bytes)
    assert items[0].target_profile == "linux-aarch64-nvidia-jetson"
    assert items[0].runtime_versions == {"onnxruntime": "1.20.0"}
    assert items[0].reported_at == datetime(2026, 6, 8, 9, 0, tzinfo=UTC)


def test_inventory_scanner_skips_missing_paths(tmp_path) -> None:
    scanner = InventoryScanner(reported_at=lambda: datetime(2026, 6, 8, 9, 0, tzinfo=UTC))

    items = scanner.scan_models([{"asset_id": uuid4(), "local_path": tmp_path / "missing.onnx"}])

    assert items == []
