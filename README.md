```text
 _   _      _   _
| \ | | ___| |_| | ___   ___  _ __ ___
|  \| |/ _ \ __| |/ _ \ / _ \| '_ ` _ \
| |\  |  __/ |_| | (_) | (_) | | | | | |
|_| \_|\___|\__|_|\___/ \___/|_| |_| |_|
```

**Weave your network APIs into one CLI.**

[![Version](https://img.shields.io/badge/version-1.7.1-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS-lightgrey.svg)]()

## About

`netloom` is a spec-driven network API CLI for operators and automation engineers.
It discovers available API actions from vendor documentation, turns them into a
consistent command surface, and keeps the workflow centered around operational
tasks like listing objects, replaying payloads, refreshing API caches, and
copying configuration between environments.

Today the first plugin is ClearPass, but the runtime is now organized so shared
CLI logic lives in `netloom/` and vendor-specific behavior lives under
`netloom/plugins/<plugin>/`.

Version: **1.7.1**

## Highlights

- shared modular runtime under `netloom/`
- plugin-specific code under `netloom/plugins/<plugin>/`
- built-in `load`, `server`, `cache`, and `copy` workflows
- profile-aware configuration through `~/.config/netloom/`
- dynamic API discovery from live vendor documentation
- structured JSON, CSV, and raw output
- shell completion and context-aware help

## Installation

Development install:

```bash
pip install -e .[dev]
```

Standard install:

```bash
pip install netloom-tool
```

Install directly from GitHub:

```bash
pip install git+https://github.com/mathias-granlund/netloom
```

Build release artifacts locally:

```bash
python -m build
python -m twine check dist/*
```

## Configuration

Use per-user profile files under `~/.config/netloom/`, or export environment
variables directly in your shell.

Required values:

```bash
export NETLOOM_SERVER="clearpass.example.com:443"
export NETLOOM_CLIENT_ID="your-client-id"
export NETLOOM_CLIENT_SECRET="your-client-secret"
```

Optional values:

```bash
export NETLOOM_VERIFY_SSL="true"
export NETLOOM_TIMEOUT="30"
export NETLOOM_LOG_LEVEL="INFO"
export NETLOOM_ENCRYPT_SECRETS="true"
export NETLOOM_API_TOKEN="optional-access-token"
export NETLOOM_API_TOKEN_FILE="/path/to/token.json"
```

Recommended profile files:

`~/.config/netloom/profiles.env`

```bash
NETLOOM_ACTIVE_PLUGIN=clearpass
NETLOOM_ACTIVE_PROFILE=prod
NETLOOM_PLUGIN_PROD=clearpass
NETLOOM_PLUGIN_DEV=clearpass
NETLOOM_SERVER_PROD="clearpass-prod.example.com:443"
NETLOOM_SERVER_DEV="clearpass-dev.example.com:443"
NETLOOM_VERIFY_SSL_PROD=true
NETLOOM_VERIFY_SSL_DEV=false
```

`~/.config/netloom/credentials.env`

```bash
NETLOOM_CLIENT_ID_PROD="prod-client-id"
NETLOOM_CLIENT_SECRET_PROD="prod-client-secret"
NETLOOM_CLIENT_ID_DEV="dev-client-id"
NETLOOM_CLIENT_SECRET_DEV="dev-client-secret"
```

Direct environment variables still override profile files when they are set in
the current shell.

Example templates are included as [profiles.env.example](profiles.env.example)
and [credentials.env.example](credentials.env.example).

## CLI syntax

```bash
netloom load <plugin>
netloom cache clear|update
netloom server list|show
netloom server use <profile>
netloom <module> <service> list [--key=value] [options]
netloom <module> <service> get [--all] [--key=value] [options]
netloom <module> <service> add|copy|delete|update|replace [--key=value] [options]
netloom copy <module> <service> --from=<profile> --to=<profile> [options]  # compatibility alias
```

Recommended first run:

```bash
netloom load clearpass
netloom cache update
```

Examples:

```bash
netloom load clearpass
netloom identities endpoint list --limit=10
netloom policyelements network-device get --id=1001
netloom policyelements network-device update --id=1001 --description="Core switch"
netloom policyelements network-device copy --from=dev --to=prod --all --dry-run
netloom server use prod
netloom server show
```

Command-line token overrides are supported:

```bash
netloom identities endpoint list --api-token=your-token
netloom identities endpoint list --token-file=./token.json
```

## Global options

| Option | Description |
|---|---|
| `--log-level=LEVEL` | Set logging level |
| `--console` | Print API response to terminal |
| `--limit=N` | Page size for list/get --all requests |
| `--offset=N` | Pagination offset |
| `--sort=+field` | Sort results |
| `--filter=JSON` | Server-side filter applied across all fetched pages |
| `--calculate-count=true/false` | Request total count |
| `--csv-fieldnames=a,b,c` | Fields and order for CSV output |
| `--file=FILE` | Bulk import JSON/CSV |
| `--out=FILE` | Override output file |
| `--api-token=TOKEN` | Use an existing bearer token instead of logging in |
| `--token-file=FILE` | Load a bearer token from JSON or plain text |
| `--help` | Context-aware help |
| `--version` | Show version |
| `--encrypt=enable/disable` | Mask or show secret fields |
| `--decrypt` | Shortcut for showing secrets |

## Discovery and cache

The active plugin discovers modules and services at runtime. The current
ClearPass plugin uses live vendor docs such as:

- `/api-docs`
- `/api/apigility/documentation/<Module-v1>`

The generated cache stores actions as:

```text
module -> service -> action -> {method, paths, params, response metadata, body hints}
```

Refresh the cache:

```bash
netloom cache clear
netloom cache update
```

## Default paths

On Linux and macOS the defaults are:

```text
cache:     ~/.cache/netloom/
state:     ~/.local/state/netloom/
responses: ~/.local/state/netloom/responses/
app logs:  ~/.local/state/netloom/logs/
config:    ~/.config/netloom/
```

These can be overridden with:

- `NETLOOM_CACHE_DIR`
- `NETLOOM_STATE_DIR`
- `NETLOOM_OUT_DIR`
- `NETLOOM_APP_LOG_DIR`
- `NETLOOM_CONFIG_DIR`

## Bash completion

Run once per session:

```bash
source /path/to/your/repo/scripts/netloom-completion.bash
```

Permanent Bash setup:

```bash
mkdir -p ~/.bash_completion.d
cat > ~/.bash_completion.d/netloom <<'EOF'
#!/usr/bin/env bash
source "$HOME/Desktop/Scripts/netloom-main/scripts/netloom-completion.bash"
EOF
```

For zsh:

```zsh
autoload -Uz bashcompinit
bashcompinit
source /path/to/your/repo/scripts/netloom-completion.bash
```

## Architecture

The repository layout is now centered on a shared `netloom/` runtime and
plugin-specific folders under `netloom/plugins/`.

```text
.
|-- CHANGELOG.md
|-- README.md
|-- RELEASING.md
|-- RELEASE_NOTES.md
|-- pyproject.toml
|-- profiles.env.example
|-- credentials.env.example
|-- examples/
|   |-- network_device_groups_import.json
|   |-- network_devices_import.csv
|   `-- network_devices_import.json
|-- man/
|   `-- netloom.1
|-- scripts/
|   `-- netloom-completion.bash
|-- tests/
|   |-- conftest.py
|   |-- test_catalog.py
|   |-- test_clearpass.py
|   |-- test_commands.py
|   |-- test_copy.py
|   |-- test_fuzz.py
|   |-- test_help.py
|   |-- test_integration_cli.py
|   |-- test_io_utils.py
|   |-- test_list_endpoints.py
|   |-- test_logger.py
|   |-- test_main.py
|   |-- test_manpage.py
|   `-- test_profiles.py
`-- netloom/
    |-- __init__.py
    |-- __main__.py
    |-- install_manpage.py
    |-- cli/
    |   |-- commands.py
    |   |-- completion.py
    |   |-- copy.py
    |   |-- help.py
    |   |-- load.py
    |   |-- main.py
    |   |-- parser.py
    |   `-- server.py
    |-- core/
    |   |-- config.py
    |   |-- pagination.py
    |   |-- plugin.py
    |   `-- resolver.py
    |-- io/
    |   |-- files.py
    |   `-- output.py
    |-- logging/
    |   `-- setup.py
    |-- data/
    |   `-- man/
    |       `-- netloom.1
    `-- plugins/
        `-- clearpass/
            |-- catalog.py
            |-- client.py
            |-- copy_hooks.py
            `-- plugin.py
```

## Development

Run tests:

```bash
pytest -q
```

Run lint and formatting:

```bash
ruff check .
ruff format .
```

View the static man page locally:

```bash
man -l man/netloom.1
```

Install the bundled man page:

```bash
netloom-install-manpage
man netloom
```

Release guidance is documented in [RELEASING.md](RELEASING.md).

## License

Proprietary / Internal Use  
See [LICENSE](LICENSE).
