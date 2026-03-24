```text
 _   _      _   _
| \ | | ___| |_| | ___   ___  _ __ ___
|  \| |/ _ \ __| |/ _ \ / _ \| '_ ` _ \
| |\  |  __/ |_| | (_) | (_) | | | | | |
|_| \_|\___|\__|_|\___/ \___/|_| |_| |_|
```

**Weave your network APIs into one CLI.**

[![Version](https://img.shields.io/badge/version-1.9.3-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS-lightgrey.svg)]()

## About

`netloom` is a spec-driven network API CLI for operators and automation engineers.
It discovers available API actions from vendor documentation, turns them into a
consistent command surface, and keeps the workflow centered around operational
tasks like listing objects, replaying payloads, refreshing API caches, and
copying configuration between environments.

The runtime is organized so shared CLI logic lives in `netloom/` and
vendor-specific behavior lives under `netloom/plugins/<plugin>/`.
ClearPass is currently the only bundled plugin. The CLI and repo layout are
already modular, so adding more plugins does not require changing the shared
command surface. More vendor support is planned for the future.

Version: **1.9.3**

Detailed changelog documented in [CHANGELOG.md](CHANGELOG.md).

## Highlights

- shared modular runtime under `netloom/`
- plugin-specific code under `netloom/plugins/<plugin>/`
- built-in `load`, `server`, and `cache` commands plus service-level `copy` and `diff` workflows
- profile-aware configuration through `~/.config/netloom/plugins/<plugin>/`
- dynamic API discovery from live vendor documentation
- structured JSON, CSV, and raw output
- shell completion and context-aware help

## Planned features

The roadmap is focused on improving the core CLI first, then expanding
automation workflows, and finally adding broader user-experience features.

ClearPass privilege-aware cache filtering, the default visible/full catalog
split, the Phase 1 comparison foundation, and secure keychain-backed runtime
secret resolution are now in place through `v1.9.3`. The next active focus is
Phase 2 safe multi-service workflows.

### Phase 1: Completed

- access-aware visible/full catalog behavior is in place
- service-level `diff` is in place with filtering, normalization, ambiguity reporting, and expanded console output
- ClearPass privilege-aware discovery is integrated into the current CLI flow

### Phase 2: Safe multi-service workflows

- implement `netloom <module> copy --from=X --to=Y` to copy all config from all `<services>` within a `<module>`
- extend structured copy and diff plans with broader automation and review workflows across multiple services
- extend validation and dry-run helpers beyond the current service-level copy workflow so more write actions can be previewed safely

### Phase 3: Change tracking and UX expansion

- add version control support for exported configs, plans, and environment comparisons
- add a GUI on top of the stabilized CLI workflows

## Installation

Standard install:

```bash
pip install netloom-tool
```

Install directly from GitHub:

```bash
pip install git+https://github.com/mathias-granlund/netloom
```

Install the bundled man pages:

```bash
netloom-install-manpage
man netloom
man netloom-clearpass
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

Required per-profile connection settings in `profiles/<profile>.env`:

```bash
NETLOOM_SERVER="server.example.com:443"
```

Required per-profile credentials in `credentials/<profile>.env`:

```bash
NETLOOM_CLIENT_ID="your-client-id"
NETLOOM_CLIENT_SECRET_REF="<profile>/client-secret"
# Optional plaintext fallback:
# NETLOOM_CLIENT_SECRET="your-client-secret"
```

For OS keychain-backed secrets, `netloom` looks up:

- service: `netloom/<plugin>`
- username/key: the value of `NETLOOM_CLIENT_SECRET_REF`

ClearPass example:

```bash
python -m keyring set netloom/clearpass prod/client-secret
```

```bash
NETLOOM_CLIENT_ID="your-client-id"
NETLOOM_CLIENT_SECRET_REF="prod/client-secret"
```

Plaintext `NETLOOM_CLIENT_SECRET` is still supported as a fallback. The runtime
uses this order when a login secret is needed:

1. `NETLOOM_API_TOKEN`
2. `NETLOOM_API_TOKEN_FILE`
3. keychain-resolved `NETLOOM_CLIENT_SECRET_REF`
4. plaintext `NETLOOM_CLIENT_SECRET`

### Keyring setup

`netloom` uses Python [`keyring`](https://keyring.readthedocs.io/en/latest/) for
OS-backed secret lookup. If `NETLOOM_CLIENT_SECRET_REF` is configured but no
usable backend is available, `netloom` will fall back to plaintext
`NETLOOM_CLIENT_SECRET` only when that value is also configured.

Basic steps:

1. Install `keyring` in the same Python environment as `netloom`.
2. Check which backend `keyring` sees:

```bash
python -m keyring diagnose
python -m keyring --help
```

3. Store the secret:

```bash
python -m keyring set netloom/clearpass prod/client-secret
```

4. Verify it:

```bash
python -m keyring get netloom/clearpass prod/client-secret
```

Working WSL/headless Linux example:

```bash
sudo apt install -y gnome-keyring
dbus-run-session -- bash
echo 'choose-a-keyring-password' | gnome-keyring-daemon --unlock
python -m keyring set netloom/clearpass prod/client-secret
```

Then configure the matching profile:

```bash
NETLOOM_CLIENT_ID="your-client-id"
NETLOOM_CLIENT_SECRET_REF="prod/client-secret"
```

You can confirm the profile wiring with:

```bash
netloom server show
```

Expected status:

```text
Client secret: keychain ref configured
Client secret ref: prod/client-secret
```

Official docs:

- Install and basic usage:
  [keyring docs](https://keyring.readthedocs.io/en/latest/)
- Backend configuration and `keyringrc.cfg`:
  [Configuring keyring](https://keyring.readthedocs.io/en/latest/#configuring)
- Headless Linux setup:
  [Using Keyring on headless Linux systems](https://keyring.readthedocs.io/en/latest/#using-keyring-on-headless-linux-systems)

Platform notes:

- macOS: `keyring` normally uses the built-in Keychain backend automatically.
- Windows: `keyring` normally uses Windows Credential Locker automatically.
- Linux desktop: `keyring` normally uses Secret Service or KWallet, depending on
  the desktop environment and installed backend packages.
- WSL or other headless Linux environments: this usually behaves like headless
  Linux and may require installing `gnome-keyring`, starting a D-Bus session,
  and unlocking the keyring daemon before storing or reading secrets, as
  described in the official headless Linux docs above.

> [!IMPORTANT]
> Direct `NETLOOM_*` environment variables still override profile files when
> they are set in the current shell session.

## First run

Load a plugin and build the API cache before expecting context-aware help,
completion, or live module/service discovery to work.
This creates the active plugin marker at ~/.config/netloom/config.env

```bash
netloom load clearpass
netloom cache update
netloom server use dev
netloom identities endpoint list --limit=10
```

## CLI syntax

```bash
  netloom load [list | show | <plugin>]
  netloom server [list | show | use <profile>]
  netloom cache [clear | update]
  netloom <module> <service> <action> [options] [flags]
  netloom <module> <service> copy --from=SOURCE --to=TARGET [options] [flags]
  netloom <module> <service> diff --from=SOURCE --to=TARGET [options] [flags]
  netloom [--help | ?]
  netloom --version
```

Examples:

```bash
netloom load clearpass
netloom server use dev
netloom cache update
netloom identities endpoint list --limit=10
netloom identities endpoint list --filter=name:equals:TEST
netloom policyelements network-device get --id=1337 --console
netloom policyelements network-device update --id=1337 --description="Core switch"
netloom policyelements network-device diff --from=dev --to=prod --name="Core switch"
netloom policyelements network-device diff --from=dev --to=prod --all --max-items=25
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

When `--filter=` is used, both shorthand and full JSON syntax are available:

Simple shorthand for common filters:

```bash
--filter=name:equals:TEST
--filter=name:contains:guest
--filter=id:in:1,2,3
--filter=enabled:exists:true
```

Supported shorthand operators:

- `equals`
- `not-equals`
- `contains`
- `in`
- `not-in`
- `gt`
- `gte`
- `lt`
- `lte`
- `exists`

Use full JSON for advanced cases such as `$and`, `$or`, `$not`, regex, or
nested expressions.

> [!IMPORTANT]
> JSON filter expressions are passed as strings, so shell quoting matters.

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

Value options:

| Option | Description |
|---|---|
| `--api-token=TOKEN` | Use an existing bearer token instead of logging in |
| `--calculate-count=true/false` | Request total count |
| `--catalog-view=visible\|full` | Use the filtered catalog or the full discovered catalog |
| `--csv-fieldnames=a,b,c` | Fields and order for CSV output |
| `--data-format=FORMAT` | Set output format (`json`, `csv`, or `raw`) |
| `--encrypt=enable/disable` | Mask or show secret fields |
| `--file=FILE` | Bulk import JSON/CSV |
| `--filter=JSON\|FIELD:OP:VALUE` | Server-side filter applied across all fetched pages |
| `--limit=N` | Page size for list/get --all requests |
| `--log-level=LEVEL` | Set logging level |
| `--offset=N` | Pagination offset |
| `--out=FILE` | Override output file |
| `--sort=+-field` | Sort results |
| `--token-file=FILE` | Load a bearer token from JSON or plain text |

Flags:

| Flag | Description |
|---|---|
| `--console` | Print API response to terminal |
| `--decrypt` | Shortcut for showing secrets |
| `--help` or `?` | Context-aware help |
| `--version` | Show version |

## Discovery and cache

The active plugin discovers modules and services at runtime. The current
ClearPass plugin uses live vendor docs such as:

- `/api-docs`
- `/api/apigility/documentation/<Module-v1>`

The generated cache stores actions as:

```text
module -> service -> action -> {method, paths, params, response metadata, body hints}
```

For ClearPass, `netloom cache update` also checks `/api/oauth/privileges`,
stores the full discovered catalog, and builds a stricter default visible view
from verified privilege mappings so help, completion, and normal command
discovery better match what the active API client can actually use.

By default, the CLI uses the visible catalog view. When you need to troubleshoot
or compare against the raw vendor docs, use the full retained catalog view:

```bash
netloom --catalog-view=full ?
netloom --catalog-view=full <module> <service> <action> --help
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
source /path/to/netloom/scripts/netloom-completion.bash
```

Permanent completion setup:

```bash
mkdir -p ~/.bash_completion.d

cp /path/to/netloom/scripts/netloom-completion.bash ~/.bash_completion.d

cat >> ~/.bashrc <<'EOF'
if [ -d "$HOME/.bash_completion.d" ]; then
  for f in "$HOME"/.bash_completion.d/*; do
    [ -r "$f" ] && source "$f"
  done
fi
EOF
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
