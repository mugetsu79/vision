from __future__ import annotations

from pathlib import Path

OPT_ROOT = Path("/opt/vezor")
CURRENT_RELEASE = OPT_ROOT / "current"
CONFIG_DIR = Path("/etc/vezor")
DATA_DIR = Path("/var/lib/vezor")
LOG_DIR = Path("/var/log/vezor")
RUNTIME_DIR = Path("/run/vezor")
SYSTEMD_UNIT_DIR = Path("/etc/systemd/system")
LAUNCHD_DAEMON_DIR = Path("/Library/LaunchDaemons")

MASTER_CONFIG = CONFIG_DIR / "master.json"
EDGE_CONFIG = CONFIG_DIR / "edge.json"
SUPERVISOR_CONFIG = CONFIG_DIR / "supervisor.json"
SUPERVISOR_CREDENTIAL = DATA_DIR / "credentials" / "supervisor.credential"
BOOTSTRAP_DIR = DATA_DIR / "bootstrap"
