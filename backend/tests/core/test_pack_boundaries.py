from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

CORE_FILES = [
    REPO_ROOT / "backend/src/argus/api/contracts.py",
    REPO_ROOT / "backend/src/argus/services/app.py",
    REPO_ROOT / "backend/src/argus/models/tables.py",
]

PACK_RUNTIME_MODULE_PATHS = [
    REPO_ROOT / "backend/src/argus/maritime",
    REPO_ROOT / "backend/src/argus/traffic_public_space",
]

FORBIDDEN_VERTICAL_NOUNS = [
    "Vessel",
    "Voyage",
    "PortCall",
    "AISPosition",
    "NMEAReading",
    "CarrierTerminal",
    "Intersection",
    "Approach",
    "Movement",
    "CurbZone",
    "SignalPhase",
    "TrafficStudy",
    "ConflictEvent",
]


def test_core_contracts_do_not_define_pack_vertical_nouns() -> None:
    offenders: list[str] = []
    for path in CORE_FILES:
        text = path.read_text(encoding="utf-8")
        for noun in FORBIDDEN_VERTICAL_NOUNS:
            if noun in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)} contains {noun}")

    assert offenders == []


def test_phase_one_does_not_create_vertical_pack_runtime_modules() -> None:
    existing_modules = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in PACK_RUNTIME_MODULE_PATHS
        if path.exists()
    ]

    assert existing_modules == []
