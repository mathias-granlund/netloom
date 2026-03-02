# config.py
"""
Configuration for ClearPass API tool
Keep secrets out of git in real environments (env vars / vault / local override file).
"""

from pathlib import Path
import os

# Package root directory (arapy/)
PACKAGE_DIR = Path(__file__).resolve().parent

# Logs directory; allow override via ARAPY_OUT_DIR env var.
# By default we now log to "<current working dir>/logs" so that running
# "arapy ..." in a project will drop files into ./logs/ next to your command.
_env_out = os.environ.get("ARAPY_OUT_DIR")
if _env_out:
    LOG_DIR = Path(_env_out)
else:
    LOG_DIR = Path.cwd() / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

PROFILES = {
    "lab": {
        "SERVER": "192.168.100.30:443",
        "VERIFY_SSL": False},
    "prod": {
        "SERVER": "clearpass.company.com:443",
        "VERIFY_SSL": True},
}
ACTIVE_PROFILE = "lab"

# ClearPass connection
SERVER = "192.168.100.30:443"
HTTPS = "https://"
VERIFY_SSL = False
DEFAULT_TIMEOUT = 15
CONSOLE = False
RESERVED = {"help", "version", "verbose", "debug", "console", "module", "service", "action", "out", "file", "csv_fieldnames"}
SECRETS = ("client_secret", "radius_secret", "tacacs_secret", "password", "enable_password")

# OAuth client credentials
CREDENTIALS = {
    "grant_type": "client_credentials",
    "client_id": "Client2",
    "client_secret": "h6jXPUUZh/GzktMFw0Sr/Is1WeISEwAQF+k7bTFH7393"
}

# Default CSV behaviour
DEFAULT_CSV_FIELDNAMES = None
DEFAULT_FORMAT = "json"

