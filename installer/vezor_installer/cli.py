from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from vezor_installer.http import InstallerHttpClient, InstallerHttpError
from vezor_installer.paths import SUPERVISOR_CONFIG, SUPERVISOR_CREDENTIAL

SECRET_KEYS = (
    "authorization",
    "bearer",
    "credential",
    "jwt",
    "password",
    "secret",
    "token",
)
BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
CREDENTIAL_RE = re.compile(r"\bvzcred_[A-Za-z0-9._~+/=-]+")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except InstallerHttpError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except LocalCliError as exc:
        print(str(exc), file=sys.stderr)
        return exc.exit_code


class LocalCliError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vezorctl")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Report local appliance status.")
    status.add_argument("--config", type=Path, default=SUPERVISOR_CONFIG)
    status.add_argument("--service-state-file", type=Path)
    status.add_argument("--service", default="vezor-edge.service")
    status.add_argument("--json", action="store_true")
    status.set_defaults(handler=_cmd_status)

    pair = subparsers.add_parser("pair", help="Claim a node pairing session.")
    pair.add_argument("--api-url", required=True)
    pair.add_argument("--session-id", required=True)
    pair.add_argument("--pairing-code", required=True)
    pair.add_argument("--supervisor-id")
    pair.add_argument("--hostname")
    pair.add_argument("--config", type=Path)
    pair.add_argument("--credential-path", type=Path, default=SUPERVISOR_CREDENTIAL)
    pair.set_defaults(handler=_cmd_pair)

    bootstrap = subparsers.add_parser(
        "bootstrap-master",
        help="Inspect or rotate local master bootstrap material.",
    )
    bootstrap.add_argument("--api-url", required=True)
    bootstrap.add_argument("--rotate-local-token", action="store_true")
    bootstrap.add_argument("--json", action="store_true")
    bootstrap.set_defaults(handler=_cmd_bootstrap_master)

    support = subparsers.add_parser("support-bundle", help="Print a local support bundle.")
    support.add_argument("--input", type=Path, required=True)
    support.add_argument("--redact", action="store_true")
    support.add_argument("--json", action="store_true")
    support.set_defaults(handler=_cmd_support_bundle)

    doctor = subparsers.add_parser("doctor", help="Run local installer diagnostics.")
    doctor.add_argument("--config", type=Path, default=SUPERVISOR_CONFIG)
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(handler=_cmd_doctor)

    return parser


def _cmd_status(args: argparse.Namespace) -> int:
    config = _read_json_file(args.config, missing_default={})
    service_state = _service_state(args.service, args.service_state_file)
    output = {
        "supervisor_id": config.get("supervisor_id", "unknown"),
        "role": config.get("role", "unknown"),
        "api_base_url": config.get("api_base_url", "unknown"),
        "credential_store_path": "[configured]"
        if config.get("credential_store_path")
        else "[missing]",
        "service": service_state,
        "local_only": True,
    }
    _print_payload(output, as_json=args.json)
    return 0


def _cmd_pair(args: argparse.Namespace) -> int:
    config = _read_json_file(args.config, missing_default={}) if args.config else {}
    supervisor_id = args.supervisor_id or config.get("supervisor_id")
    hostname = args.hostname or config.get("hostname") or supervisor_id
    if not supervisor_id:
        raise LocalCliError(
            "Pairing requires --supervisor-id or config supervisor id.",
            exit_code=2,
        )
    if not hostname:
        raise LocalCliError("Pairing requires --hostname or config hostname.", exit_code=2)

    client = InstallerHttpClient(args.api_url)
    response = client.claim_pairing_session(
        session_id=args.session_id,
        pairing_code=args.pairing_code,
        supervisor_id=str(supervisor_id),
        hostname=str(hostname),
    )
    credential_material = response.get("credential_material")
    if not isinstance(credential_material, str) or not credential_material:
        raise LocalCliError("Pairing response did not include credential material.")
    _write_credential(
        args.credential_path,
        {
            "credential_material": credential_material,
            "credential_id": response.get("credential_id"),
            "credential_hash": response.get("credential_hash"),
            "credential_version": response.get("credential_version"),
            "node": response.get("node"),
        },
    )
    print(f"Credential written to {args.credential_path}.")
    return 0


def _cmd_bootstrap_master(args: argparse.Namespace) -> int:
    client = InstallerHttpClient(args.api_url)
    payload = (
        client.rotate_local_bootstrap_token()
        if args.rotate_local_token
        else client.bootstrap_status()
    )
    _print_payload(payload, as_json=args.json)
    return 0


def _cmd_support_bundle(args: argparse.Namespace) -> int:
    payload = _read_json_file(args.input, missing_default={})
    if args.redact:
        payload = redact(payload)
    _print_payload(payload, as_json=args.json)
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    payload = {
        "config_exists": args.config.exists(),
        "credential_path": "[configured]" if SUPERVISOR_CREDENTIAL.exists() else "[missing]",
        "local_only": True,
    }
    _print_payload(payload, as_json=args.json)
    return 0


def _read_json_file(path: Path | None, *, missing_default: dict[str, Any]) -> dict[str, Any]:
    if path is None or not path.exists():
        return dict(missing_default)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise LocalCliError(f"{path} must contain a JSON object.")
    return payload


def _service_state(service: str, state_file: Path | None) -> dict[str, Any]:
    if state_file is not None:
        payload = _read_json_file(state_file, missing_default={})
        return {
            "service": payload.get("service", service),
            "active": bool(payload.get("active", False)),
            "status": payload.get("status", "unknown"),
        }
    result = subprocess.run(
        ["systemctl", "is-active", service],
        check=False,
        capture_output=True,
        text=True,
    )
    status = result.stdout.strip() or "unknown"
    return {
        "service": service,
        "active": result.returncode == 0,
        "status": status,
    }


def _write_credential(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as credential_file:
        json.dump(payload, credential_file, indent=2, sort_keys=True)
        credential_file.write("\n")
    path.chmod(0o600)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if _is_secret_key(key):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = redact(item)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return CREDENTIAL_RE.sub("[redacted]", BEARER_RE.sub("Bearer [redacted]", value))
    return value


def _is_secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in SECRET_KEYS)


def _print_payload(payload: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
