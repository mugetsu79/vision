from __future__ import annotations

from argus.supervisor.credential_store import (
    FileCredentialStore,
    InMemoryCredentialStore,
    redact_credential_material,
)


def test_in_memory_credential_store_saves_loads_rotates_and_deletes() -> None:
    store = InMemoryCredentialStore()

    store.save("node-secret-1")
    assert store.load() == "node-secret-1"

    store.rotate("node-secret-2")
    assert store.load() == "node-secret-2"

    store.delete()
    assert store.load() is None


def test_file_credential_store_uses_owner_only_permissions(tmp_path) -> None:
    path = tmp_path / "supervisor.credential"
    store = FileCredentialStore(path)

    store.save("node-secret-1")

    assert store.load() == "node-secret-1"
    assert oct(path.stat().st_mode & 0o777) == "0o600"

    store.rotate("node-secret-2")
    assert store.load() == "node-secret-2"

    store.delete()
    assert not path.exists()


def test_redaction_masks_credential_material() -> None:
    text = redact_credential_material("failed to use node-secret-1 for request")

    assert "node-secret-1" not in text
    assert "[redacted]" in text
