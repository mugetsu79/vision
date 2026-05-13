from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol


class SupervisorCredentialStore(Protocol):
    def save(self, credential_material: str) -> None: ...

    def load(self) -> str | None: ...

    def rotate(self, credential_material: str) -> None: ...

    def delete(self) -> None: ...


class InMemoryCredentialStore:
    def __init__(self, credential_material: str | None = None) -> None:
        self.credential_material = credential_material

    def save(self, credential_material: str) -> None:
        self.credential_material = credential_material

    def load(self) -> str | None:
        return self.credential_material

    def rotate(self, credential_material: str) -> None:
        self.save(credential_material)

    def delete(self) -> None:
        self.credential_material = None


class FileCredentialStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save(self, credential_material: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(credential_material, encoding="utf-8")
        self.path.chmod(0o600)

    def load(self) -> str | None:
        if not self.path.exists():
            return None
        value = self.path.read_text(encoding="utf-8").strip()
        return value or None

    def rotate(self, credential_material: str) -> None:
        self.save(credential_material)

    def delete(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            return


def redact_credential_material(text: str) -> str:
    return re.sub(r"\b(?:node|vzcred)[A-Za-z0-9_.-]*\b", "[redacted]", text)
