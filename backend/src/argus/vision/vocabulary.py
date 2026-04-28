from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable


def normalize_vocabulary_terms(terms: Iterable[object]) -> list[str]:
    normalized: list[str] = []
    for term in terms:
        value = str(term).strip()
        if value:
            normalized.append(value)
    return normalized


def hash_vocabulary(terms: Iterable[object]) -> str:
    payload = json.dumps(
        normalize_vocabulary_terms(terms),
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
