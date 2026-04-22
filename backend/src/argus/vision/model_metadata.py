from __future__ import annotations

import ast
import json
from typing import Any

from fastapi import HTTPException, status

from argus.models.enums import ModelFormat
from argus.vision.runtime import import_onnxruntime

HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


def extract_onnx_classes(path: str, runtime: Any | None = None) -> list[str] | None:
    ort = runtime or import_onnxruntime()
    try:
        session = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    except Exception as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail=(
                f"Unable to read ONNX model metadata from '{path}'. "
                "Ensure the file exists and is readable from the backend runtime."
            ),
        ) from exc
    raw_names = session.get_modelmeta().custom_metadata_map.get("names")
    if not raw_names:
        return None

    parsed = _parse_names(raw_names)
    if isinstance(parsed, dict):
        return [str(value) for _, value in sorted(parsed.items(), key=_dict_item_order)]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return None


def resolve_model_classes(
    path: str,
    format: ModelFormat,
    declared_classes: list[str] | None,
    runtime: Any | None = None,
) -> tuple[list[str], str]:
    if format is not ModelFormat.ONNX:
        if declared_classes is not None:
            return list(declared_classes), "declared"
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="classes are required for non-ONNX models.",
        )

    embedded_classes = extract_onnx_classes(path, runtime=runtime)
    if embedded_classes is None:
        if declared_classes is not None:
            return list(declared_classes), "declared"
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail=(
                "classes are required because this ONNX model does not expose "
                "embedded class metadata."
            ),
        )

    if declared_classes is None:
        return embedded_classes, "embedded"
    if list(declared_classes) != embedded_classes:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Declared classes do not match the embedded ONNX class metadata.",
        )
    return embedded_classes, "embedded"


def _parse_names(raw_names: str) -> object:
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(raw_names)
        except Exception:
            continue
    return raw_names


def _dict_item_order(item: tuple[object, object]) -> tuple[int, int | str]:
    key = item[0]
    try:
        return (0, int(str(key)))
    except ValueError:
        return (1, str(key))
