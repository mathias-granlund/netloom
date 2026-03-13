# arapy

[![Version](https://img.shields.io/badge/version-1.5.2-blue.svg)]()
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

Version: **1.5.2**

---

## What changed in 1.5.2

- `arapy copy` now drops blank secret fields from generated payloads so hidden source credentials do not get replayed as empty strings on updates or replacements
- `network-device` creates now fail locally with a clear copy-specific error when the source response does not include usable RADIUS, TACACS+, or SNMP credentials
- copy summaries now print per-item failure reasons directly in the terminal for faster troubleshooting

## What changed in 1.5.1

- fixed `arapy copy` so it now reuses the cached API catalog for both source and target profiles instead of refetching `/api-docs` on every run
- added regression coverage for the copy catalog-loading path so normal copy operations stay aligned with the rest of the CLI cache behavior

## What changed in 1.5.0

- added built-in `arapy copy <module> <service> --from=... --to=...` support for cross-profile resource migration workflows
- copy mode supports `--dry-run`, `--match-by`, `--on-conflict`, `--decrypt`, and report artifact options like `--save-source`, `--save-payload`, and `--save-plan`
- copy mode normalizes source responses into writable target payloads, strips response-only fields, preserves requested secret visibility, and applies creates or updates against the destination profile
- path overrides such as `ARAPY_OUT_DIR` now resolve through the same config and profile loading path as the other settings
- profile-scoped path settings like `ARAPY_OUT_DIR_PROD` are now respected
- `~` is now expanded correctly in path override settings such as `ARAPY_OUT_DIR=~/responses`

---

## Installation

### Development install

```bash
pip install -e .[dev]
```

If `pip` performs a user install on Linux or macOS, the `arapy` and
`arapy-install-manpage` commands are typically written to `~/.local/bin`.
Make sure that directory is on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Standard install

```bash
pip install git+https://github.com/mg-aranya/arapy
```

To build release artifacts locally:

```bash
python -m build
python -m twine check dist/*
```

---

## Required environment variables

Use per-user profile files under `~/.config/arapy/`, or export environment
variables directly in your shell.

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

Example files are included as `profiles.env.example` and
`credentials.env.example`.

Per-user profile files under `~/.config/arapy/` are the recommended way to
switch between environments like `prod` and `dev` without re-exporting shell
variables on each run.

Example `~/.config/arapy/profiles.env`:

```bash
ARAPY_ACTIVE_PROFILE=prod
ARAPY_SERVER_PROD="clearpass-prod.example.com:443"
ARAPY_SERVER_DEV="clearpass-dev.example.com:443"
```

Example `~/.config/arapy/credentials.env`:

```bash
ARAPY_CLIENT_ID_PROD="prod-client-id"
ARAPY_CLIENT_SECRET_PROD="prod-client-secret"
ARAPY_CLIENT_ID_DEV="dev-client-id"
ARAPY_CLIENT_SECRET_DEV="dev-client-secret"
```

Direct environment variables such as `ARAPY_SERVER` and `ARAPY_CLIENT_ID` still
override the profile files when they are set in the current shell.

---

## CLI syntax

```bash
arapy <module> <service> list [--key=value] [options]
arapy <module> <service> get [--all] [--key=value] [options]
arapy <module> <service> add|delete|update|replace [--key=value] [options]
arapy copy <module> <service> --from=<profile> --to=<profile> [options]
arapy cache clear|update
arapy server list|show
arapy server use <profile>
```

Examples:

```bash
arapy identities endpoint list --limit=10
arapy policyelements network-device get --all --limit=25
arapy policyelements network-device get --id=1001
arapy policyelements network-device delete --name=switch-01
arapy policyelements network-device update --id=1001 --description="Core switch"
arapy copy policyelements network-device --from=dev --to=prod --all --dry-run
arapy server use prod
arapy server show
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
| `--limit=N` | Limit results (1-1000) |
| `--offset=N` | Pagination offset |
| `--sort=+field` | Sort results |
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
|-- __init__.py
|-- __main__.py
|-- cli/
|   |-- commands.py
|   |-- completion.py
|   |-- help.py
|   |-- main.py
|   `-- parser.py
|-- core/
|   |-- catalog.py
|   |-- client.py
|   |-- config.py
|   `-- resolver.py
|-- io/
|   |-- files.py
|   `-- output.py
|-- logging/
|   `-- setup.py
|-- scripts/
|   `-- arapy-completion.bash
`-- tests/
```

---

## Development

Run tests:

```bash
pytest -q
```

Property-based fuzz tests are included in the pytest suite via `hypothesis`,
which is installed as part of:

```bash
pip install -e '.[dev]'
```

Static operator documentation is also available as a bundled man page:

```bash
man -l man/arapy.1
```

To install the bundled man page for normal `man arapy` usage:

```bash
arapy-install-manpage
man arapy
```

If your system does not already search `~/.local/share/man`, add it to `MANPATH`.

## Server profiles

Use the built-in server profile commands to inspect and switch the active
ClearPass target:

```bash
arapy server list
arapy server show
arapy server use prod
arapy server use dev
```

`arapy server use <profile>` updates `ARAPY_ACTIVE_PROFILE` in
`~/.config/arapy/profiles.env`. The next `arapy` command resolves
profile-scoped values such as `ARAPY_SERVER_PROD` and
`ARAPY_CLIENT_SECRET_PROD` automatically.

---

## Packaging

`arapy` now includes the baseline pieces expected from a releasable Python package:

- explicit project metadata, classifiers, and project URLs in `pyproject.toml`
- a packaged license file
- wheel and sdist support for the bundled man page
- a `MANIFEST.in` for predictable source distributions
- build validation via `python -m build` and `python -m twine check`
- CI coverage for tests and distribution validation on supported Python versions

Run lint and formatting:

```bash
ruff check .
ruff format .
```

---

## License

Proprietary / Internal Use  
See `LICENSE`.
