# arapy

[![Version](https://img.shields.io/badge/version-1.2.3-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS-lightgrey.svg)]()
[![License](https://img.shields.io/badge/license-Internal-orange.svg)]()

A modern, modular CLI toolkit for interacting with  
**Aruba ClearPass Policy Manager REST API**.

------------------------------------------------------------------------

## 🚀 Overview

**arapy** is designed for operators and automation engineers who need:

- A powerful, script-friendly CLI
- Dynamic ClearPass API discovery
- Structured logging & diagnostics
- Clean, extensible architecture
- Native tab completion support

Version: **1.2.3**

------------------------------------------------------------------------

## ✨ Key Features

- ✅ Dynamic API discovery via `/api-docs`
- ✅ Automatic Swagger 1.2 (Apigility) parsing
- ✅ No static endpoint mapping required
- ✅ Endpoint caching for performance
- ✅ `arapy cache clear` command
- ✅ Modular command architecture
- ✅ Full CRUD support across services
- ✅ Pagination, filtering & sorting
- ✅ CSV import/export
- ✅ Bulk operations
- ✅ Structured logging with configurable levels
- ✅ Context-aware help system
- ✅ Bash tab-completion

------------------------------------------------------------------------


# 🔍 Dynamic API Discovery

Starting from **v1.2.3**, arapy automatically discovers all available
ClearPass API endpoints at runtime using:
/api-docs
/api/apigility/documentation/<Module-v1>

This means:

- No more hardcoded endpoint mappings
- Full compatibility with ClearPass API updates
- Automatic support for new modules/services

------------------------------------------------------------------------

# 🗂 Endpoint Cache

Discovered endpoints are cached locally:
cache/api_endpoints_cache.json

To clear the cache manually:

```bash
arapy cache clear
```
The next command run will rebuild the cache automatically.
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

  Option                           Description
  -------------------------------- --------------------------------
  `--log_level=LEVEL`              Set logging level
  `--console`                      Print API response to terminal
  `--limit=N`                      Limit results (1--1000)
  `--offset=N`                     Pagination offset
  `--sort=±field`                  Sort results
  `--filter=JSON`                  Server-side filter
  `--calculate_count=true/false`   Request total count
  `--csv_fieldnames=a,b,c`         CSV column selection
  `--file=FILE`                    Bulk import JSON/CSV
  `--out=FILE`                     Override output file
  `--help`                         Context-aware help
  `--version`                      Show version

------------------------------------------------------------------------

# 📂 Logging & Error Handling

-   All responses are written to file by default.
-   Logging level controlled via `--log_level`.
-   Debug mode provides structured, line-by-line HTTP diagnostics.
-   Sensitive fields are automatically masked.

------------------------------------------------------------------------

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

**arapy v1.2.3**
Dynamic. Modular. Self-discovering ClearPass automation.
