```text
 _   _      _   _
| \ | | ___| |_| | ___   ___  _ __ ___
|  \| |/ _ \ __| |/ _ \ / _ \| '_ ` _ \
| |\  |  __/ |_| | (_) | (_) | | | | | |
|_| \_|\___|\__|_|\___/ \___/|_| |_| |_|
```

**A CLI for working with network APIs — easy, consistent, safe, and fast.**

[![Version](https://img.shields.io/badge/version-1.9.9-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS-lightgrey.svg)]()

## About
`netloom` is a plugin-backed network API CLI for operators and automation
engineers. It lets you interact with network APIs through a consistent CLI
with a shared command model, context-aware help and tab completion. 
It keeps server profiles and discovery data organized locally, and supports 
day-to-day tasks such as list, create, update or delete objects as well as 
compare and copy configuration between servers.

**HPE Aruba ClearPass** is a bundled plugin with netloom.

## Installation

Install from PyPI:

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

Example templates are included as [defaults.env.example](defaults.env.example),
[profiles.env.example](profiles.env.example), and
[credentials.env.example](credentials.env.example).

For ClearPass, the minimal layout is:

```text
~/.config/netloom/config.env
~/.config/netloom/plugins/clearpass/defaults.env
~/.config/netloom/plugins/clearpass/profiles/<profile>.env
~/.config/netloom/plugins/clearpass/credentials/<profile>.env
```

Required profile connection settings in `profiles/<profile>.env`:

```bash
NETLOOM_SERVER="server.example.com:443"
```

Required credentials in `credentials/<profile>.env`:

```bash
NETLOOM_CLIENT_ID="your-client-id"
NETLOOM_CLIENT_SECRET_REF="<profile>/client-secret"
# Optional plaintext fallback:
# NETLOOM_CLIENT_SECRET="your-client-secret"
```

If you use an OS keychain, store the referenced secret with:

```bash
python -m keyring set netloom/clearpass <profile>/client-secret
```

## First Run / Quick Start

```bash
netloom load clearpass
netloom server use <profile>
netloom cache update
netloom identities endpoint list --limit=10
```

That initial `cache update` is what enables richer help, completion, and live
module/service discovery for the active server.

## CLI Examples

List a few endpoints from the active profile:

```bash
netloom identities endpoint list --limit=10
```

Filter a list request with shorthand syntax:

```bash
netloom identities endpoint list --filter=name:contains:guest
```

Fetch one object and print it to the terminal:

```bash
netloom policyelements network-device get --id=1001 --console
```

Compare the same service between two profiles:

```bash
netloom policyelements network-device diff --from=dev --to=prod --all --max-items=25
```

Preview a cross-profile copy without writing changes:

```bash
netloom policyelements network-device copy --from=dev --to=prod --all --dry-run
```

## Feature Roadmap

- Multi-service copy workflows
- Extended validation and dry-run features
- Version tracking for config changes
- Low-priority CLI semantics and naming cleanup
- GUI on top of CLI

## Deeper Docs

For full command reference and plugin-specific details:

- Shared CLI reference: `man netloom` or [man/netloom.md](man/netloom.md)
- ClearPass plugin reference: `man netloom-clearpass` or [man/netloom-clearpass.md](man/netloom-clearpass.md)
- Shell completion setup and generic `--filter=` syntax: `man netloom`
- ClearPass-oriented filter and workflow examples: `man netloom-clearpass`
- Live action help from your current cache: `netloom <module> <service> ?`

Detailed release history is in [CHANGELOG.md](CHANGELOG.md).

## Development
```
pip install -e .[dev]
pytest -q
ruff check .
ruff format .
python -m build
python -m twine check dist/*
```

## License

Proprietary / Internal Use  
See [LICENSE](LICENSE).
