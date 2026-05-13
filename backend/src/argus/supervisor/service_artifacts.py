from __future__ import annotations

from dataclasses import dataclass

_FORBIDDEN_SECRET_MARKERS = (
    "Bearer ",
    "ARGUS_API_BEARER_TOKEN=",
    "token-password",
)


@dataclass(frozen=True, slots=True)
class ServiceArtifactConfig:
    supervisor_id: str
    python_executable: str = "/opt/vezor/venv/bin/python"
    supervisor_config_path: str = "/etc/vezor/supervisor.json"
    credential_path: str = "/etc/vezor/supervisor.credential"
    working_directory: str = "/opt/vezor/app"
    image: str = "ghcr.io/vezor/supervisor:latest"


def render_systemd_unit(config: ServiceArtifactConfig) -> str:
    exec_start = (
        f"{config.python_executable} -m argus.supervisor.runner "
        f"--config {config.supervisor_config_path}"
    )
    text = f"""[Unit]
Description=Vezor Supervisor Agent ({config.supervisor_id})
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=vezor
Group=vezor
WorkingDirectory={config.working_directory}
Environment=VEZOR_SUPERVISOR_CONFIG={config.supervisor_config_path}
LoadCredential=supervisor-credential:{config.credential_path}
ExecStart={exec_start}
Restart=on-failure
RestartSec=5s
StateDirectory=vezor
LogsDirectory=vezor
RuntimeDirectory=vezor
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/vezor /var/log/vezor /run/vezor

[Install]
WantedBy=multi-user.target
"""
    assert_no_embedded_long_lived_secret(text)
    return text


def render_launchd_plist(config: ServiceArtifactConfig) -> str:
    text = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.vezor.supervisor</string>
  <key>ProgramArguments</key>
  <array>
    <string>{config.python_executable}</string>
    <string>-m</string>
    <string>argus.supervisor.runner</string>
    <string>--config</string>
    <string>{config.supervisor_config_path}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>{config.working_directory}</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/var/log/vezor/supervisor.log</string>
  <key>StandardErrorPath</key>
  <string>/var/log/vezor/supervisor.err.log</string>
</dict>
</plist>
"""
    assert_no_embedded_long_lived_secret(text)
    return text


def render_compose_service(config: ServiceArtifactConfig) -> str:
    healthcheck = (
        '["CMD", "python", "-m", "argus.supervisor.runner", '
        f'"--healthcheck", "--config", "{config.supervisor_config_path}"]'
    )
    text = f"""services:
  vezor-supervisor:
    image: {config.image}
    container_name: vezor-supervisor
    restart: unless-stopped
    command:
      - python
      - -m
      - argus.supervisor.runner
      - --config
      - {config.supervisor_config_path}
    volumes:
      - {config.supervisor_config_path}:{config.supervisor_config_path}:ro
      - /run/vezor/credentials:/run/vezor/credentials:ro
      - /var/lib/vezor:/var/lib/vezor
      - /var/log/vezor:/var/log/vezor
    healthcheck:
      test: {healthcheck}
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s
"""
    assert_no_embedded_long_lived_secret(text)
    return text


def assert_no_embedded_long_lived_secret(text: str) -> None:
    for marker in _FORBIDDEN_SECRET_MARKERS:
        if marker in text:
            msg = f"Service artifact contains long-lived secret marker: {marker}"
            raise ValueError(msg)
