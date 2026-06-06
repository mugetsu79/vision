from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import SecretStr

from argus.core.config import Settings
from argus.main import create_app


def export_openapi_schema(output_path: Path | str) -> None:
    path = Path(output_path)
    app = create_app(
        Settings.model_validate(
            {
                "enable_startup_services": False,
                "enable_nats": False,
                "enable_tracing": False,
                "rtsp_encryption_key": SecretStr("argus-dev-rtsp-key"),
            }
        )
    )
    schema = app.openapi()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the FastAPI OpenAPI schema.")
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args(argv)
    export_openapi_schema(args.output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
