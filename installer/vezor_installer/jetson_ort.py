from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vezor_installer.manifest import Manifest


@dataclass(frozen=True, slots=True)
class ResolvedJetsonOrtWheel:
    url: str
    sha256: str


def resolve_jetson_ort_wheel(
    preflight: Mapping[str, object],
    wheels: Sequence[Mapping[str, object] | object],
) -> ResolvedJetsonOrtWheel:
    arch = _normalize_arch(_string(preflight.get("arch")))
    jetpack = _string(preflight.get("jetpack"))
    l4t = _string(preflight.get("l4t"))
    python_abi = _string(preflight.get("python_abi") or preflight.get("python"))

    for wheel in wheels:
        wheel_mapping = _wheel_mapping(wheel)
        if _normalize_arch(_string(wheel_mapping.get("arch"))) != arch:
            continue
        if _string(wheel_mapping.get("python")) != python_abi:
            continue
        if _string(wheel_mapping.get("jetpack")) != jetpack:
            continue
        wheel_l4t = _string(wheel_mapping.get("l4t"))
        if wheel_l4t and not l4t.startswith(wheel_l4t):
            continue
        url = _string(wheel_mapping.get("url"))
        sha256 = _string(wheel_mapping.get("sha256")).lower()
        if not url or len(sha256) != 64:
            continue
        return ResolvedJetsonOrtWheel(url=url, sha256=sha256)

    raise ValueError(
        "No Jetson GPU ONNX Runtime wheel for "
        f"arch={arch or 'unknown'} jetpack={jetpack or 'unknown'} "
        f"l4t={l4t or 'unknown'} python={python_abi or 'unknown'}."
    )


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if len(args) != 2:
        print("usage: python -m vezor_installer.jetson_ort MANIFEST PREFLIGHT_JSON", file=sys.stderr)
        return 2

    manifest = Manifest.model_validate_json(Path(args[0]).read_text(encoding="utf-8"))
    preflight_raw: Any = json.loads(Path(args[1]).read_text(encoding="utf-8"))
    if not isinstance(preflight_raw, Mapping):
        raise SystemExit("Jetson preflight JSON must be an object.")
    resolved = resolve_jetson_ort_wheel(preflight_raw, manifest.jetson_ort_wheels)
    print(f"JETSON_ORT_WHEEL_URL={json.dumps(resolved.url)}")
    print(f"JETSON_ORT_WHEEL_SHA256={json.dumps(resolved.sha256)}")
    return 0


def _wheel_mapping(wheel: Mapping[str, object] | object) -> Mapping[str, object]:
    if isinstance(wheel, Mapping):
        return wheel
    dump = getattr(wheel, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    raise TypeError(f"Unsupported Jetson ORT wheel entry: {type(wheel)!r}")


def _normalize_arch(value: str) -> str:
    return "aarch64" if value in {"arm64", "aarch64"} else value


def _string(value: object) -> str:
    return str(value).strip() if value is not None else ""


if __name__ == "__main__":
    raise SystemExit(main())
