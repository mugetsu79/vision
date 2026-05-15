from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from vezor_installer import cli


def test_status_json_reads_local_config_and_service_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "supervisor.json"
    state_path = tmp_path / "service-state.json"
    config_path.write_text(
        json.dumps(
            {
                "supervisor_id": "edge-orin-1",
                "role": "edge",
                "api_base_url": "https://master.example",
                "credential_store_path": "/run/vezor/credentials/supervisor.credential",
            }
        ),
        encoding="utf-8",
    )
    state_path.write_text(
        json.dumps(
            {
                "service": "vezor-edge.service",
                "active": True,
                "status": "running",
            }
        ),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "status",
            "--config",
            str(config_path),
            "--service-state-file",
            str(state_path),
            "--json",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["supervisor_id"] == "edge-orin-1"
    assert output["role"] == "edge"
    assert output["service"]["status"] == "running"
    assert output["credential_store_path"] == "[configured]"
    assert "supervisor.credential" not in json.dumps(output)


def test_pair_claims_session_writes_credential_0600_without_printing_material(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, str]] = []

    class FakeClient:
        def __init__(self, api_url: str) -> None:
            self.api_url = api_url

        def claim_pairing_session(
            self,
            *,
            session_id: str,
            pairing_code: str,
            supervisor_id: str,
            hostname: str,
        ) -> dict[str, object]:
            calls.append(
                {
                    "api_url": self.api_url,
                    "session_id": session_id,
                    "pairing_code": pairing_code,
                    "supervisor_id": supervisor_id,
                    "hostname": hostname,
                }
            )
            return {
                "credential_id": "00000000-0000-0000-0000-000000000901",
                "credential_material": "vzcred_should_not_print",
                "credential_hash": "a" * 64,
                "credential_version": 1,
                "node": {"id": "00000000-0000-0000-0000-000000000902"},
            }

    monkeypatch.setattr(cli, "InstallerHttpClient", FakeClient)
    credential_path = tmp_path / "supervisor.credential"

    exit_code = cli.main(
        [
            "pair",
            "--api-url",
            "https://master.example",
            "--session-id",
            "00000000-0000-0000-0000-000000000111",
            "--pairing-code",
            "123456",
            "--supervisor-id",
            "edge-orin-1",
            "--hostname",
            "orin-nano-01",
            "--credential-path",
            str(credential_path),
        ]
    )

    captured = capsys.readouterr()
    stored = credential_path.read_text(encoding="utf-8").strip()
    assert exit_code == 0
    assert calls == [
        {
            "api_url": "https://master.example",
            "session_id": "00000000-0000-0000-0000-000000000111",
            "pairing_code": "123456",
            "supervisor_id": "edge-orin-1",
            "hostname": "orin-nano-01",
        }
    ]
    assert stored == "vzcred_should_not_print"
    assert "credential_material" not in credential_path.read_text(encoding="utf-8")
    assert stat.S_IMODE(credential_path.stat().st_mode) == 0o600
    assert "vzcred_should_not_print" not in captured.out
    assert "credential written" in captured.out.lower()


def test_pair_updates_local_config_supervisor_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        def __init__(self, api_url: str) -> None:
            self.api_url = api_url

        def claim_pairing_session(
            self,
            *,
            session_id: str,
            pairing_code: str,
            supervisor_id: str,
            hostname: str,
        ) -> dict[str, object]:
            return {
                "credential_id": "00000000-0000-0000-0000-000000000901",
                "credential_material": "vzcred_should_not_print",
                "credential_hash": "a" * 64,
                "credential_version": 1,
                "node": {"id": "00000000-0000-0000-0000-000000000902"},
            }

    monkeypatch.setattr(cli, "InstallerHttpClient", FakeClient)
    config_path = tmp_path / "supervisor.json"
    config_path.write_text(
        json.dumps(
            {
                "supervisor_id": "central-master-1",
                "role": "central",
                "api_base_url": "http://backend:8000",
            }
        ),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "pair",
            "--api-url",
            "https://master.example",
            "--session-id",
            "00000000-0000-0000-0000-000000000111",
            "--pairing-code",
            "123456",
            "--supervisor-id",
            "100",
            "--hostname",
            "portable-master",
            "--config",
            str(config_path),
            "--credential-path",
            str(tmp_path / "supervisor.credential"),
        ]
    )

    stored_config = json.loads(config_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert stored_config["supervisor_id"] == "100"
    assert stored_config["role"] == "central"
    assert stored_config["api_base_url"] == "http://backend:8000"


def test_pair_updates_edge_config_with_claimed_edge_node_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    edge_node_id = "00000000-0000-0000-0000-000000000909"

    class FakeClient:
        def __init__(self, api_url: str) -> None:
            self.api_url = api_url

        def claim_pairing_session(
            self,
            *,
            session_id: str,
            pairing_code: str,
            supervisor_id: str,
            hostname: str,
        ) -> dict[str, object]:
            return {
                "credential_id": "00000000-0000-0000-0000-000000000901",
                "credential_material": "vzcred_should_not_print",
                "credential_hash": "a" * 64,
                "credential_version": 1,
                "node": {
                    "id": "00000000-0000-0000-0000-000000000902",
                    "node_kind": "edge",
                    "edge_node_id": edge_node_id,
                },
            }

    monkeypatch.setattr(cli, "InstallerHttpClient", FakeClient)
    config_path = tmp_path / "supervisor.json"
    config_path.write_text(
        json.dumps(
            {
                "supervisor_id": "jetson-portable-1",
                "role": "edge",
                "api_base_url": "http://192.168.1.166:8000",
                "credential_store_path": "/run/vezor/credentials/supervisor.credential",
            }
        ),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "pair",
            "--api-url",
            "https://master.example",
            "--session-id",
            "00000000-0000-0000-0000-000000000111",
            "--pairing-code",
            "123456",
            "--supervisor-id",
            "jetson-portable-1",
            "--hostname",
            "orin1",
            "--config",
            str(config_path),
            "--credential-path",
            str(tmp_path / "supervisor.credential"),
        ]
    )

    stored_config = json.loads(config_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert stored_config["supervisor_id"] == "jetson-portable-1"
    assert stored_config["edge_node_id"] == edge_node_id


def test_support_bundle_redacts_token_like_values(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(
        json.dumps(
            {
                "token": "raw-token",
                "authorization": "Bearer raw-token",
                "nested": {"credential": "vzcred_raw-secret", "status": "ok"},
                "items": [{"password": "raw-password"}, {"service": "ready"}],
            }
        ),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "support-bundle",
            "--input",
            str(bundle_path),
            "--redact",
            "--json",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "raw-token" not in output
    assert "vzcred_raw-secret" not in output
    assert "raw-password" not in output
    assert output.count("[redacted]") >= 3


def test_pair_requires_explicit_supervisor_identity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(
        [
            "pair",
            "--api-url",
            "https://master.example",
            "--session-id",
            "00000000-0000-0000-0000-000000000111",
            "--pairing-code",
            "123456",
            "--credential-path",
            str(tmp_path / "supervisor.credential"),
        ]
    )

    assert exit_code == 2
    assert "supervisor id" in capsys.readouterr().err.lower()
