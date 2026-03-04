# Changelog

All notable changes to this project will be documented in this file.

The format loosely follows Keep a Changelog and Semantic Versioning
principles.
------------------------------------------------------------------------

## [1.2.5] - 2026-03-04

### Changed
- Help and bash completion now rely exclusively on dynamically discovered ClearPass API data (`/api-docs`)
- Removed fallback to static `commands.DISPATCH` when the API catalog cache is missing

### Notes
- If the API cache is missing, run any authenticated command to build it (for example: `arapy identities endpoint list`)
- You can clear the cache with: `arapy cache clear`

------------------------------------------------------------------------

## [1.2.4] - 2026-03-04

### Added
- Dynamic ClearPass API discovery via `/api-docs` (Swagger 1.2 / Apigility documentation)
- Endpoint catalog caching in `cache/api_endpoints_cache.json`
- Namespaced endpoint keys (`<module>:<service>`) to avoid collisions across modules
- Dynamic `--help` and bash completion driven by the cached API catalog
- `arapy cache clear` command to remove the endpoint cache

### Changed
- Removed reliance on static endpoint tables for help and completion
- Endpoint resolution now prefers `<module>:<service>` and falls back to `<service>` for compatibility

### Fixed
- Prevented endpoint key collisions (e.g. `endpoint`) that could route to the wrong module and cause HTTP 405 errors

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
