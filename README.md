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

At the moment ClearPass is the only supported plugin but the runtime is now organized so shared
CLI logic lives in `netloom/` and vendor-specific behavior lives under
`netloom/plugins/<plugin>/`. More vendor support is planed for the future.

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

Standard install:

```bash
pip install netloom-tool
```

Install directly from GitHub:

```bash
pip install git+https://github.com/mathias-granlund/netloom
```

Install the bundled man page:

```bash
netloom-install-manpage
man netloom
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
  netloom load [list | show | <plugin>]
  netloom server [list | show | [use <profile>]]
  netloom cache [clear | update]
  netloom <module> <service> <action> [options] [flags]
  netloom --version
```

Examples:

```bash
netloom load clearpass
netloom server use dev
netloom identities endpoint list --limit=10
netloom policyelements network-device get --id=1337 --console
netloom policyelements network-device update --id=1337 --description="Core switch"
netloom policyelements network-device copy --from=dev --to=prod --filter='{"name":{"$contains":"VLAN10"}}' --dry-run

```

Command-line token overrides are supported:

```bash
netloom identities endpoint list --api-token=your-token
netloom identities endpoint list --token-file=./token.json
```

When `--filter=` is used, the following operators and syntax is available:
```bash
  Key is equal to 'value'                  '{"key":{"$eq":"value"}}'
  Key is one of a list of values           '{"key":{"$in":["value1", "value2"]}}'
  Key is not one of a list of values       '{"key":{"$nin":["value1", "value2"]}}'
  Key contains a substring 'value'         '{"key":{"$contains":"value"}}'
  key is not equal to 'value'              '{"key":{"$ne":"value"}}'
  Key is greater than 'value'              '{"key":{"$gt":"value"}}'
  Key is greater than or equal to 'value'  '{"key":{"$gte":"value"}}'
  Key is less than 'value'                 '{"key":{"$lt":"value"}}'
  Key is less than or equal to 'value'     '{"key":{"$lte":"value"}}'
  Key matches a regex (case-sensitive)     '{"key":{"$regex":"regex"}}'
  Key exists (not null value)              '{"key":{"$exists":true}}'
  Key is NULL                              '{"key":{"$exists":false}}'
  Combining filter expressions with AND    '{"$and":[filter1, filter2,...]}'
  Combining filter expressions with OR     '{"$or":[filter1, filter2,...]}'
  Inverting a filter expression            '{"$not":{filter}}'
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

cp /path/to/your/repo/scripts/netloom-completion.bash ~/.bash_completion.d

cat >> ~/.bashcr <<'EOF'
if [ -d "$HOME/.bash_completion.d" ]; then
  for f in "$HOME"/.bash_completion.d/*; do
    [ -r "$f" ] && source "$f"
  done
fi
EOF
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
|-- man/
|   `-- netloom.1
|-- scripts/
|   `-- netloom-completion.bash
|-- tests/
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

Development install:

```bash
pip install -e .[dev]
```

Run tests:

```bash
pytest -q
```

Run lint and formatting:

```bash
ruff check .
ruff format .
```

Build release artifacts locally:

```bash
python -m build
python -m twine check dist/*
```

Release guidance is documented in [RELEASING.md](RELEASING.md).

## License

Proprietary / Internal Use  
See [LICENSE](LICENSE).
