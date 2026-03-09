# arapy

[![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS-lightgrey.svg)]()
[![License](https://img.shields.io/badge/license-Internal-orange.svg)]()

A modern, modular CLI toolkit for interacting with  
**Aruba ClearPass Policy Manager REST API**.

------------------------------------------------------------------------

## 🚀 Overview

**arapy** is designed for operators and automation engineers who need:

- A powerful, script-friendly CLI
- A clean, extensible architecture
- Clear, structured logging
- Reliable error diagnostics
- Native tab completion support
- API discovery that adapts to ClearPass upgrades

Version: **1.3.0**

------------------------------------------------------------------------

## ✨ Key Features

- ✅ Dynamic API discovery via `/api-docs`
- ✅ Swagger 1.2 / Apigility documentation parsing
- ✅ Action-aware endpoint cache in `cache/api_endpoints_cache.json`
- ✅ Preserved parameterized paths with CLI placeholder expansion
- ✅ `get`, `add`, `delete`, `update`, and `replace` action mapping
- ✅ `list` alias for `get --all`
- ✅ Dynamic service and action help
- ✅ Bash tab-completion driven by the discovered API catalog
- ✅ Structured logging with configurable levels
- ✅ Pagination, filtering, and sorting support
- ✅ CSV import/export and bulk operations

------------------------------------------------------------------------

## 🆕 What's New in 1.3.0

- The cached API catalog now stores actions as `module -> service -> action -> {method, paths, params}`
- Parameterized Swagger endpoints are kept instead of discarded
- Single `*_id` path placeholders are normalized to `{id}`
- `ClearPassClient._help()` now renders compact service help and action-specific help blocks
- `list` is available as a direct alias for `get --all`
- `arapy cache update` logging now reports discovered modules and total services

If you are upgrading from an older cache format, run:

```bash
arapy cache clear
arapy cache update
```

------------------------------------------------------------------------

# 🛠 Installation

## Install (Development)

```bash
pip install -e .
```

## Install (Standard)

```bash
pip install .
```

------------------------------------------------------------------------

# ⚡ Enable Tab Completion (Bash)

Run once per session:

```bash
source /path/to/your/repo/scripts/arapy-completion.bash
```

To enable permanently, add to `~/.bashrc` then reload terminal:

```bash
for f in ~/.bash_completion.d/*; do
  [ -r "$f" ] && source "$f"
done
```

### Zsh Support

Add to `~/.zshrc`:

```zsh
autoload -Uz bashcompinit
bashcompinit
source /path/to/your/repo/scripts/arapy-completion.bash
```

------------------------------------------------------------------------

# 🖥 CLI Syntax

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
arapy policyelements network-device update --id=1001 --description='Core switch'
```

------------------------------------------------------------------------

## 🌍 Global Options

| Option                         | Description                     |
|--------------------------------|---------------------------------|
| `--log_level=LEVEL`            | Set logging level               |
| `--console`                    | Print API response to terminal  |
| `--limit=N`                    | Limit results (1–1000)          |
| `--offset=N`                   | Pagination offset               |
| `--sort=±field`                | Sort results                    |
| `--filter=JSON`                | Server-side filter              |
| `--calculate_count=true/false` | Request total count             |
| `--csv_fieldnames=a,b,c`       | Fields and order for CSV output |
| `--file=FILE`                  | Bulk import JSON/CSV            |
| `--out=FILE`                   | Override output file            |
| `--help`                       | Context-aware help              |
| `--version`                    | Show version                    |

------------------------------------------------------------------------

# 📂 Logging & Error Handling

- All responses are written to file by default
- Logging level is controlled via `--log_level`
- Debug mode provides structured, line-by-line HTTP diagnostics
- Sensitive fields are automatically masked

------------------------------------------------------------------------

## 🔍 Dynamic API Discovery

Starting with **v1.2.4**, arapy discovers available ClearPass API modules and services at runtime using the ClearPass API explorer:

- `/api-docs`
- `/api/apigility/documentation/<Module-v1>`

This removes the need for hardcoded endpoint maps and makes arapy version agnostic so it can adapt to ClearPass upgrades automatically.

In **v1.3.0**, the generated cache became action-aware and now stores discovered methods, paths, and parameters per service action.

------------------------------------------------------------------------

## 🗂 Endpoint Cache

Discovered endpoints are cached locally for faster startup:

```text
cache/api_endpoints_cache.json
```

To clear the cache run:

```bash
arapy cache clear
```

To update the cache run:

```bash
arapy cache update
```

------------------------------------------------------------------------

# 🏗 Architecture

```text
arapy/
├── api_catalog.py               # Dynamic API discovery and cache builder
├── clearpass.py                 # REST client and dynamic help renderer
├── commands.py                  # CLI command routing
├── config.py                    # Default configuration
├── io_utils.py                  # File input / output
├── logger.py                    # Terminal logs
├── main.py                      # CLI entrypoint
├── scripts/
│   └── arapy-completion.bash    # Command tab-completion
├── cache/
│   └── api_endpoints_cache.json # Endpoint cache
├── logs/                        # API response logs
└── tests/                       # Unit tests
```

------------------------------------------------------------------------

# 📄 License

Internal / Custom Use  
© Mathias Granlund

------------------------------------------------------------------------
