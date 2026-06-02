#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

REQUIRED_LIST_KEYS = (
    "apiAllowOrigins",
    "webrtcAllowOrigins",
    "hlsAllowOrigins",
    "webrtcAdditionalHosts",
)


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        stripped = value.strip()
        if not stripped or stripped in seen:
            continue
        seen.add(stripped)
        result.append(stripped)
    return result


def normalize_origin(value: str) -> str:
    stripped = value.strip()
    if stripped.endswith("/") and "://" in stripped:
        return stripped.rstrip("/")
    return stripped


def replace_scalar(text: str, key: str, value: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            lines[index] = f"{key}: {value}"
            return "\n".join(lines) + "\n"
    raise SystemExit(f"MediaMTX template is missing required key: {key}")


def replace_list_block(text: str, key: str, values: list[str]) -> str:
    if not values:
        raise SystemExit(f"MediaMTX rendered list cannot be empty: {key}")

    lines = text.splitlines()
    for start, line in enumerate(lines):
        if line == f"{key}:":
            end = start + 1
            while end < len(lines) and lines[end].startswith("  - "):
                end += 1
            replacement = [f"{key}:"] + [f"  - {value}" for value in values]
            return "\n".join(lines[:start] + replacement + lines[end:]) + "\n"
    raise SystemExit(f"MediaMTX template is missing required key: {key}")


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            dir=path.parent,
            encoding="utf-8",
            delete=False,
        ) as handle:
            temp_path = handle.name
            handle.write(content)
        os.chmod(temp_path, 0o644)
        os.replace(temp_path, path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def render_config(
    *,
    source: Path,
    dest: Path,
    frontend_origins: list[str],
    webrtc_hosts: list[str],
    jwks_url: str | None,
) -> None:
    origins = dedupe_preserve_order(normalize_origin(origin) for origin in frontend_origins)
    hosts = dedupe_preserve_order(webrtc_hosts)

    text = source.read_text(encoding="utf-8")
    for key in REQUIRED_LIST_KEYS:
        values = hosts if key == "webrtcAdditionalHosts" else origins
        text = replace_list_block(text, key, values)

    if jwks_url:
        text = replace_scalar(text, "authJWTJWKS", jwks_url.rstrip("/"))

    write_atomic(dest, text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render installed MediaMTX config from network install inputs."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--frontend-origin", action="append", default=[])
    parser.add_argument("--webrtc-host", action="append", default=[])
    parser.add_argument("--jwks-url")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    render_config(
        source=args.source,
        dest=args.dest,
        frontend_origins=args.frontend_origin,
        webrtc_hosts=args.webrtc_host,
        jwks_url=args.jwks_url,
    )


if __name__ == "__main__":
    main()
