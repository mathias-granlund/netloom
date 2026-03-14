```text
 _   _      _   _
| \ | | ___| |_| | ___   ___  _ __ ___
|  \| |/ _ \ __| |/ _ \ / _ \| '_ ` _ \
| |\  |  __/ |_| | (_) | (_) | | | | | |
|_| \_|\___|\__|_|\___/ \___/|_| |_| |_|
```

**Weave your network APIs into one CLI.**

[![Version](https://img.shields.io/badge/version-1.6.3-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS-lightgrey.svg)]()

---

## About netloom

**netloom** is a spec-driven network API CLI for operators and automation engineers. It discovers available API actions from vendor documentation, turns them into a practical command-line interface, and keeps the workflow centered around real operational tasks like listing objects, exporting data, replaying payloads, and copying configuration between environments.

Today, netloom is built first and foremost for **HPE Aruba ClearPass Policy Manager**, with strong support for dynamic API discovery, context-aware help, structured output, profile-based server switching, and cross-environment copy workflows. The longer-term direction is broader: a reusable, spec-driven network API CLI that can grow beyond a single vendor without losing the operator-friendly UX that makes it useful day to day.

## Highlights

- dynamic API discovery through ClearPass `/api-docs`
- a script-friendly CLI for `get`, `list`, `add`, `delete`, `update`, and `replace`
- built-in cross-profile `copy` workflows for migration and dry-run planning
- structured file output for JSON, CSV, or raw responses
- safe handling of secrets in output and logs
- shell completion and context-aware help
- profile-based switching between environments like `dev` and `prod`

Version: **1.6.3**

---

## Recent changes

- added concise inline comments around the less obvious request resolution, catalog discovery, copy planning, and output-handling code paths to make maintenance easier without adding noise to straightforward code
- shell completion now falls back cleanly between `netloom` and `arapy`, which fixes tab completion in setups where only one of the installed executables is directly discoverable by the shell
- hyphenated server profile names such as `qa-edge` now round-trip correctly through profile-scoped config keys like `ARAPY_SERVER_QA_EDGE`
- session tokens are no longer written to debug logs
- Ruff checks now run in CI alongside the existing test/build validation
- `netloom-tool` packaging is now ready for Trusted Publishing to PyPI, including a tagged GitHub Actions publish workflow and an in-repo release checklist
- added the `netloom-install-manpage` helper command while keeping `arapy-install-manpage` available during the transition
- package metadata now uses the modern Python packaging license fields for cleaner builds and PyPI validation
- the project is now branded as `netloom`, with `netloom-tool` as the PyPI package name and `netloom` as the primary CLI command
- the legacy `arapy` command remains available as a compatibility alias during the transition
- the repository and project links now point to `netloom.se` and `github.com/mathias-granlund/netloom`
- explicit `--limit` values on `list`, `get --all`, and `copy` are now honored as requested instead of being overridden by automatic paging
- the bundled Bash completion script now registers completion for both `netloom` and `arapy`

Full release history is kept in [CHANGELOG.md](CHANGELOG.md).

---

## Installation

### Development install

```bash
pip install -e .[dev]
```

If `pip` performs a user install on Linux or macOS, the `netloom` and
`netloom-install-manpage` commands are typically written to `~/.local/bin`.
Make sure that directory is on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Standard install

```bash
pip install netloom-tool
```

Or install directly from GitHub:

```bash
pip install git+https://github.com/mathias-granlund/netloom
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

For this first rename stage, the internal Python package, config directory, and
environment variable names still use the existing `arapy` / `ARAPY_*`
conventions for compatibility.

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
netloom <module> <service> list [--key=value] [options]
netloom <module> <service> get [--all] [--key=value] [options]
netloom <module> <service> add|delete|update|replace [--key=value] [options]
netloom copy <module> <service> --from=<profile> --to=<profile> [options]
netloom cache clear|update
netloom server list|show
netloom server use <profile>
```

Examples:

```bash
netloom identities endpoint list --limit=10
netloom policyelements network-device get --all --limit=25
netloom policyelements network-device get --id=1001
netloom policyelements network-device delete --name=switch-01
netloom policyelements network-device update --id=1001 --description="Core switch"
netloom copy policyelements network-device --from=dev --to=prod --all --dry-run
netloom server use prod
netloom server show
```

Both `--log-level` and the legacy `--log_level` style are accepted. The same applies to flags like `--csv-fieldnames` / `--csv_fieldnames`.

Authentication can also be provided per command with:

```bash
netloom identities endpoint list --api-token=your-token
netloom identities endpoint list --token-file=./token.json
```

The legacy `arapy` command still works during the transition, but new examples
and docs use `netloom`.

---

## Global options

| Option | Description |
|---|---|
| `--log-level=LEVEL` | Set logging level |
| `--console` | Print API response to terminal |
| `--limit=N` | Page size for list/get --all requests (1-1000 per request) |
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

---

## Dynamic API discovery

netloom discovers available ClearPass modules and services at runtime using:

- `/api-docs`
- `/api/apigility/documentation/<Module-v1>`

The generated cache stores actions as:

```text
module -> service -> action -> {method, paths, params, response metadata, body hints}
```

When the ClearPass docs include Swagger model details, `netloom --help` now renders:

- operation summaries and notes
- response-code lists
- response content types
- generated request body examples and top-level body field descriptions

Download-style endpoints that advertise binary response types are written as raw files automatically, and `netloom` will use the server-provided filename when one is supplied.

To refresh the cache:

```bash
netloom cache clear
netloom cache update
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
The bundled completion script currently supports both `netloom` and `arapy`.

Run once per session:

```bash
source /path/to/your/repo/scripts/arapy-completion.bash
```

Or to enable permanently, add to `~/.bashrc` then reload terminal:

```bash
mkdir -p ~/.bash_completion.d
cat > ~/.bash_completion.d/netloom <<'EOF'
#!/usr/bin/env bash
source "$HOME/Desktop/Scripts/netloom-main/scripts/arapy-completion.bash"
EOF

if [ -d "$HOME/.bash_completion.d" ]; then
  for f in "$HOME"/.bash_completion.d/*; do
    [ -r "$f" ] && source "$f"
  done
fi

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
netloom-install-manpage
man arapy
```

The legacy `arapy-install-manpage` helper still works, and the bundled manpage
name remains `arapy` during this first transition stage.

If your system does not already search `~/.local/share/man`, add it to `MANPATH`.

## Server profiles

Use the built-in server profile commands to inspect and switch the active
ClearPass target:

```bash
netloom server list
netloom server show
netloom server use prod
netloom server use dev
```

`netloom server use <profile>` updates `ARAPY_ACTIVE_PROFILE` in
`~/.config/arapy/profiles.env`. The next `netloom` command resolves
profile-scoped values such as `ARAPY_SERVER_PROD` and
`ARAPY_CLIENT_SECRET_PROD` automatically.

---

## Packaging

`netloom` now includes the baseline pieces expected from a releasable Python package:

- explicit project metadata, classifiers, and project URLs in `pyproject.toml`
- a packaged license file
- wheel and sdist support for the bundled man page
- a `MANIFEST.in` for predictable source distributions
- build validation via `python -m build` and `python -m twine check`
- CI coverage for tests and distribution validation on supported Python versions
- Trusted Publishing-ready GitHub Actions for tagged PyPI releases

Run lint and formatting:

```bash
ruff check .
ruff format .
```

For the release checklist and Trusted Publishing setup steps, see
[RELEASING.md](RELEASING.md).

---

## License

Proprietary / Internal Use  
See [LICENSE](LICENSE).
