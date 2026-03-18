```text
 _   _      _   _
| \ | | ___| |_| | ___   ___  _ __ ___
|  \| |/ _ \ __| |/ _ \ / _ \| '_ ` _ \
| |\  |  __/ |_| | (_) | (_) | | | | | |
|_| \_|\___|\__|_|\___/ \___/|_| |_| |_|
```

**Weave your network APIs into one CLI.**

[![Version](https://img.shields.io/badge/version-1.7.4-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS-lightgrey.svg)]()

## About

`netloom` is a spec-driven network API CLI for operators and automation engineers.
It discovers available API actions from vendor documentation, turns them into a
consistent command surface, and keeps the workflow centered around operational
tasks like listing objects, replaying payloads, refreshing API caches, and
copying configuration between environments.

> [!NOTE]
> The runtime is organized so shared CLI logic lives in `netloom/` and
> vendor-specific behavior lives under `netloom/plugins/<plugin>/`.
> ClearPass is currently the only bundled plugin. The CLI and repo layout are
> already modular, so adding more plugins does not require changing the shared
> command surface. More vendor support is planned for the future.

Version: **1.7.4**

## Highlights

- shared modular runtime under `netloom/`
- plugin-specific code under `netloom/plugins/<plugin>/`
- built-in `load`, `server`, `cache`, and `copy` workflows
- profile-aware configuration through `~/.config/netloom/plugins/<plugin>/`
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

## First run

> [!NOTE]
> Load a plugin and build the API cache before expecting context-aware help,
> completion, or live module/service discovery to work well.
> This creates the active plugin marker at ~/.config/netloom/config.env

```bash
netloom load clearpass
netloom cache update
netloom server use dev
netloom identities endpoint list --limit=10
```

## Configuration

> [!TIP]
> Example templates are included as [defaults.env.example](defaults.env.example),
> [profiles.env.example](profiles.env.example), and
> [credentials.env.example](credentials.env.example). Copy them into the plugin
> directory ~/.config/netloom/plugins/\<plugin\>/

The runtime separates global plugin selection from plugin-specific profile
settings:

```text
~/.config/netloom/config.env
~/.config/netloom/plugins/<plugin>/defaults.env
~/.config/netloom/plugins/<plugin>/profiles/<profile>.env
~/.config/netloom/plugins/<plugin>/credentials/<profile>.env
```

`config.env` usually only needs the active plugin and is normally managed with:

```bash
netloom load clearpass
```

`defaults.env` holds the active profile and any plugin-wide fallback values:

```bash
NETLOOM_ACTIVE_PROFILE="prod"
NETLOOM_VERIFY_SSL="true"
NETLOOM_TIMEOUT="30"
```

Required per-profile connection settings in `profiles/<profile>.env`:

```bash
NETLOOM_SERVER="clearpass.example.com:443"
```

Required per-profile credentials in `credentials/<profile>.env`:

```bash
NETLOOM_CLIENT_ID="your-client-id"
NETLOOM_CLIENT_SECRET="your-client-secret"
```

> [!IMPORTANT]
> Direct `NETLOOM_*` environment variables still override profile files when
> they are set in the current shell session.

## CLI syntax

```bash
  netloom load [list | show | <plugin>]
  netloom server [list | show | use <profile>]
  netloom cache [clear | update]
  netloom <module> <service> <action> [options] [flags]
  netloom <module> <service> copy --from=SOURCE --to=TARGET [options] [flags]
  netloom [--help | ?]
  netloom --version
```

Examples:

```bash
netloom load clearpass
netloom server use dev
netloom cache update
netloom identities endpoint list --limit=10
netloom policyelements network-device get --id=1337 --console
netloom policyelements network-device update --id=1337 --description="Core switch"
netloom policyelements network-device copy --from=dev --to=prod --filter='{"description":{"$contains":"Core switch"}}' --dry-run
```

Command-line token overrides are supported:

```bash
netloom identities endpoint list --api-token=your-token
netloom identities endpoint list --token-file=./token.json
```

> [!CAUTION]
> `--api-token`, `--token-file`, and especially `--decrypt` together with
> `--console` can expose sensitive data in shell history or terminal output.

When `--filter=` is used, the following operators and syntax are available:

> [!NOTE]
> Filter expressions are passed as JSON strings, so shell quoting matters.

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
  Key is absent / does not exist           '{"key":{"$exists":false}}'
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
| `--sort=+-field` | Sort results |
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
config:    ~/.config/netloom/config.env
plugins:   ~/.config/netloom/plugins/<plugin>/
```

These can be overridden with:

- `NETLOOM_CACHE_DIR`
- `NETLOOM_STATE_DIR`
- `NETLOOM_OUT_DIR`
- `NETLOOM_APP_LOG_DIR`
- `NETLOOM_CONFIG_DIR`

## Bash completion

> [!TIP]
> Completion quality depends on the local API cache. If module or service names
> look incomplete, run `netloom cache update` first.

Run once per session:

```bash
source /path/to/your/repo/scripts/netloom-completion.bash
```

Permanent completion setup:

```bash
mkdir -p ~/.bash_completion.d

cp /path/to/your/repo/netloom-main/scripts/netloom-completion.bash ~/.bash_completion.d

cat >> ~/.bashrc <<'EOF'
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
|-- defaults.env.example
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
    |   |-- help.py
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
            |-- help.py
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
