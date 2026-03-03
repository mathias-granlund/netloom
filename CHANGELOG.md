# Changelog

All notable changes to this project will be documented in this file.

The format loosely follows Keep a Changelog and Semantic Versioning
principles.

------------------------------------------------------------------------

## [1.2.3] - 2026-03-03

### Added

- Dynamic ClearPass API endpoint discovery via `/api-docs`
- Full Swagger 1.2 (Apigility) documentation parsing
- Automatic endpoint mapping (no more static endpoint file)
- Endpoint caching under `cache/api_endpoints_cache.json`
- `arapy cache clear` command for manual cache invalidation
- Improved debug logging for API discovery process

### Changed

- CLI now builds endpoint map dynamically at runtime
- Cache directory moved from `logs/` to dedicated `cache/`
- Improved error visibility during API discovery
- Refactored startup flow to bootstrap OAuth before API discovery

### Removed

- Static `api_endpoints.py`
- GUI mode
- `--refresh-api-cache` flag
- Hardcoded endpoint mappings

------------------------------------------------------------------------
## \[1.2.0\] - 2024-01-Release

### Added

-   Dynamic, data-driven help system (`print_help()` refactor)
-   Bash tab-completion for modules, services, and actions
-   `--log_level` global flag with support for:
    -   debug
    -   info
    -   warning
    -   error
    -   critical
-   Structured, line-by-line debug logging for HTTP errors
-   Cleaner CLI argument handling
-   Context-aware completion engine integrated into CLI

### Changed

-   Removed large static help blocks
-   Standardized logging behavior
-   Improved CLI help formatting
-   Improved internal command routing structure
-   Updated README with installation & completion guide

### Fixed

-   Completion behavior when service names share substrings
-   Logging inconsistencies between console and file output
-   Minor help text formatting issues

------------------------------------------------------------------------

## \[1.1.6\]

### Added

-   Initial dynamic help rendering
-   Improved error handling structure

------------------------------------------------------------------------

## \[1.1.5\]

### Added

-   Extended module/service coverage
-   Improved structured logging
-   Context-aware help support

------------------------------------------------------------------------
