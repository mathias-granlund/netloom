# arapy

[![Version](https://img.shields.io/badge/version-1.2.4-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS-lightgrey.svg)]()
[![License](https://img.shields.io/badge/license-Internal-orange.svg)]()

A modern, modular CLI toolkit for interacting with\
**Aruba ClearPass Policy Manager REST API**.

------------------------------------------------------------------------

## 🚀 Overview

**arapy** is designed for operators and automation engineers who need:

-   A powerful, script-friendly CLI
-   A clean, extensible architecture
-   Clear, structured logging
-   Reliable error diagnostics
-   Native tab completion support

Version: **1.2.4**

------------------------------------------------------------------------

## ✨ Key Features

-   ✅ Dynamic API discovery via `/api-docs`
-   ✅ Swagger 1.2 / Apigility documentation parsing
-   ✅ Endpoint cache (`cache/api_endpoints_cache.json`)
-   ✅ `arapy cache clear` for cache invalidation
-   ✅ Modular command architecture
-   ✅ Full CRUD support across services
-   ✅ Pagination, filtering & sorting
-   ✅ CSV import/export
-   ✅ Bulk operations
-   ✅ Structured logging with configurable levels
-   ✅ Context-aware help system
-   ✅ Bash tab-completion

------------------------------------------------------------------------

# 🛠 Installation

## Install (Development)

``` bash
pip install -e .
```

## Install (Standard)

``` bash
pip install .
```

------------------------------------------------------------------------

# ⚡ Enable Tab Completion (Bash)

Run once per session:

``` bash
source /path/to/your/repo/scripts/arapy-completion.bash
```

To enable permanently, add to `~/.bashrc`:

``` bash
source /path/to/your/repo/scripts/arapy-completion.bash
```

Reload:

``` bash
source ~/.bashrc
```

### Zsh Support

Add to `~/.zshrc`:

``` zsh
autoload -Uz bashcompinit
bashcompinit
source /path/to/your/repo/scripts/arapy-completion.bash
```

------------------------------------------------------------------------

# 🖥 CLI Syntax

``` bash
arapy <module> <service> <action> [--key=value] [options]
```

Example:

``` bash
arapy identities endpoint list --limit=10
arapy policy-elements network-device get --id=1001
```

------------------------------------------------------------------------

# ⚙️ Global Options

| Option                             | Description                          |
|------------------------------------|--------------------------------------|
| `--log_level=LEVEL`               | Set logging level                   |
| `--console`                       | Print API response to terminal      |
| `--limit=N`                       | Limit results (1–1000)              |
| `--offset=N`                      | Pagination offset                   |
| `--sort=±field`                   | Sort results                        |
| `--filter=JSON`                   | Server-side filter                  |
| `--calculate_count=true/false`    | Request total count                 |
| `--csv_fieldnames=a,b,c`          | CSV column selection                |
| `--file=FILE`                     | Bulk import JSON/CSV                |
| `--out=FILE`                      | Override output file                |
| `--help`                          | Context-aware help                  |
| `--version`                       | Show version                        |

------------------------------------------------------------------------

# 📂 Logging & Error Handling

-   All responses are written to file by default.
-   Logging level controlled via `--log_level`.
-   Debug mode provides structured, line-by-line HTTP diagnostics.
-   Sensitive fields are automatically masked.

------------------------------------------------------------------------

## 🔍 Dynamic API Discovery

Starting with **v1.2.4**, arapy discovers available ClearPass API modules and services at runtime using the ClearPass API explorer:

- `/api-docs`
- `/api/apigility/documentation/<Module-v1>`

This removes the need for hardcoded endpoint maps and makes arapy more resilient to ClearPass upgrades.

------------------------------------------------------------------------

## 🗂 Endpoint Cache

Discovered endpoints are cached locally for faster startup:

```
cache/api_endpoints_cache.json
```

To clear the cache manually:

```bash
arapy cache clear
```

The next authenticated command will rebuild the cache automatically.


# 🏗 Architecture

    arapy/
    ├── api_catalog.py        # Dynamic API discovery & caching
    ├── clearpass.py          # REST client
    ├── commands.py           # CLI command routing
    ├── config.py             # Configuration
    ├── io_utils.py
    ├── logger.py
    ├── main.py               # CLI entrypoint
    ├── scripts/
    │   └── arapy-completion.bash
    ├── cache/                # Endpoint cache
    ├── logs/
    └── tests/

------------------------------------------------------------------------

# 📄 License

Internal / Custom Use\
© Mathias Granlund

------------------------------------------------------------------------

**arapy v1.2.0**\
Clean. Modular. Production-ready ClearPass automation.
