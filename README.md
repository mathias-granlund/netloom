# arapy

[![Version](https://img.shields.io/badge/version-1.4.4-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS-lightgrey.svg)]()

A modular CLI toolkit for interacting with **HPE Aruba ClearPass Policy Manager**.

---

## Overview

**arapy** is aimed at operators and automation engineers who need:

- dynamic API discovery through ClearPass `/api-docs`
- a script-friendly CLI for `get`, `list`, `add`, `delete`, `update`, and `replace`
- structured file output for JSON, CSV, or raw responses
- safe handling of secrets in output and logs
- shell completion and context-aware help

Version: **1.4.4**

---

## What changed in 1.4.4

- cleaned up `--help` output so write-style actions no longer show redundant `params:` blocks when richer `body fields:` metadata is available
- kept `params:` output for query/path-driven actions that do not have request-body metadata

---

## Installation

### Development install

```bash
pip install -e .[dev]
```

### Standard install

```bash
pip install git+https://github.com/mg-aranya/arapy
```

---

## Required environment variables

Create a local `.env` or export the variables in your shell.

```bash
export ARAPY_SERVER="clearpass.example.com:443"
export ARAPY_CLIENT_ID="your-client-id"
export ARAPY_CLIENT_SECRET="your-client-secret"
```

Optional settings:

```bash
export ARAPY_VERIFY_SSL="true"
export ARAPY_TIMEOUT="30"
export ARAPY_LOG_LEVEL="INFO"
export ARAPY_ENCRYPT_SECRETS="true"
export ARAPY_API_TOKEN="optional-access-token"
export ARAPY_API_TOKEN_FILE="/path/to/token.json"
```

An example file is included as `.env.example`.

---

## CLI syntax

```bash
arapy <module> <service> list [--key=value] [options]
arapy <module> <service> get [--all] [--key=value] [options]
arapy <module> <service> add|delete|update|replace [--key=value] [options]
arapy cache clear|update
```

Examples:

```bash
arapy identities endpoint list --limit=10
arapy policyelements network-device get --all --limit=25
arapy policyelements network-device get --id=1001
arapy policyelements network-device delete --name=switch-01
arapy policyelements network-device update --id=1001 --description="Core switch"
```

Both `--log-level` and the legacy `--log_level` style are accepted. The same applies to flags like `--csv-fieldnames` / `--csv_fieldnames`.

Authentication can also be provided per command with:

```bash
arapy identities endpoint list --api-token=your-token
arapy identities endpoint list --token-file=./token.json
```

---

## Global options

| Option | Description |
|---|---|
| `--log-level=LEVEL` | Set logging level |
| `--console` | Print API response to terminal |
| `--limit=N` | Limit results (1–1000) |
| `--offset=N` | Pagination offset |
| `--sort=±field` | Sort results |
| `--filter=JSON` | Server-side filter |
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

---

## Dynamic API discovery

arapy discovers available ClearPass modules and services at runtime using:

- `/api-docs`
- `/api/apigility/documentation/<Module-v1>`

The generated cache stores actions as:

```text
module -> service -> action -> {method, paths, params, response metadata, body hints}
```

When the ClearPass docs include Swagger model details, `arapy --help` now renders:

- operation summaries and notes
- response-code lists
- response content types
- generated request body examples and top-level body field descriptions

Download-style endpoints that advertise binary response types are written as raw files automatically, and `arapy` will use the server-provided filename when one is supplied.

To refresh the cache:

```bash
arapy cache clear
arapy cache update
```

---

## Default cache and output locations

v1.4.0 no longer writes cache and response files into the project tree by default.

On Linux/macOS the defaults are:

```text
cache:     ~/.cache/arapy/
state:     ~/.local/state/arapy/
responses: ~/.local/state/arapy/responses/
app logs:  ~/.local/state/arapy/logs/
```

These can be overridden with environment variables such as `ARAPY_CACHE_DIR`, `ARAPY_STATE_DIR`, `ARAPY_OUT_DIR`, and `ARAPY_APP_LOG_DIR`.

---

## Enable tab completion (Bash)

Run once per session:

```bash
source /path/to/your/repo/scripts/arapy-completion.bash
```

Or to enable permanently, add to `~/.bashrc` then reload terminal:

```bash
for f in ~/.bash_completion.d/*; do
  [ -r "$f" ] && source "$f"
done

```

For zsh:

```zsh
autoload -Uz bashcompinit
bashcompinit
source /path/to/your/repo/scripts/arapy-completion.bash
```

---

## Architecture

```text
arapy/
├── __init__.py
├── __main__.py
├── cli/
│   ├── commands.py
│   ├── completion.py
│   ├── help.py
│   ├── main.py
│   └── parser.py
├── core/
│   ├── catalog.py
│   ├── client.py
│   ├── config.py
│   └── resolver.py
├── io/
│   ├── files.py
│   └── output.py
├── logging/
│   └── setup.py
├── scripts/
│   └── arapy-completion.bash
└── tests/
```

---

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

---

## License

Internal / Custom Use  
© Mathias Granlund
