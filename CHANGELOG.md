# Changelog

## 1.7.3 - 2026-03-18

### Changed
- split shared help rendering into a thinner `netloom.cli.help` orchestrator and a generic `netloom.core.help` formatter layer
- moved ClearPass-specific help examples, options, flags, and notes fully behind the plugin help context
- trimmed the no-plugin `netloom --help` path so it only shows the shared banner, version, usage, and available built-in modules
- kept shared help exports stable and restored copy syntax guidance in the generic usage block

## 1.7.2 - 2026-03-18

### Changed
- moved plugin-specific profile files to `~/.config/netloom/plugins/<plugin>/profiles.env` and `credentials.env`
- `netloom load <plugin>` now owns the global `~/.config/netloom/config.env` plugin selector, while `netloom server use <profile>` updates the active profile inside the selected plugin directory
- updated the README, examples, and help-adjacent tests to match the new plugin-scoped config layout

## 1.7.1 - 2026-03-16

### Changed
- `copy` can now be used as a normal action with `netloom <module> <service> copy ...`, which lines it up with the rest of the command model
- the legacy `netloom copy <module> <service> ...` form is still accepted as a compatibility alias for this release
- help text, completion, and tests now treat `copy` as a first-class action on services

## 1.7.0 - 2026-03-16

### Added
- new modular `netloom/` package with shared CLI, config, logging, I/O, and command layers separated from vendor-specific plugin code
- `netloom load <plugin>` built-in command for persisting the active plugin before using the normal `netloom <module> <service> <action>` workflow
- initial `netloom/plugins/clearpass` plugin boundary for the ClearPass runtime path, including plugin-specific client and copy hooks

### Changed
- the primary `netloom` console entrypoint now runs through the modular `netloom.cli.main` runtime
- configuration now uses `NETLOOM_*` names and `~/.config/netloom/` paths consistently across the runtime
- README now documents the plugin-loading workflow, modular package layout, the `NETLOOM_*` configuration examples, and the netloom-only repository structure

### Removed
- the legacy compatibility package and command surface have been removed from the repository and packaging
- completion, manpage, tests, and packaged assets now target only `netloom`

## 1.6.3 - 2026-03-14

### Changed
- added concise inline comments across the CLI, client, catalog, config, pagination, resolver, and output modules to clarify non-obvious control flow without cluttering self-explanatory code

## 1.6.2 - 2026-03-14

### Fixed
- hardened shell completion so `netloom` can resolve completions through whichever installed backend executable is actually available, instead of assuming the typed command name is always directly executable
- fixed profile-name round-tripping for hyphenated profiles such as `qa-edge` so profile-scoped keys like `NETLOOM_SERVER_QA_EDGE` can be discovered and reselected correctly
- stopped logging bearer session tokens in debug output

### Changed
- cleaned remaining Ruff and PEP 8 issues across the Python package and tests, and added Ruff checks to the packaging workflow so import-order and formatting regressions are caught in CI

## 1.6.1 - 2026-03-14

### Changed
- added the `netloom-install-manpage` helper command
- GitHub packaging workflow now smoke-tests both `netloom` and `netloom-install-manpage` before tagged releases
- package metadata now uses modern `license` and `license-files` fields for cleaner PyPI builds
- added `RELEASING.md` with a Trusted Publishing setup and release checklist for `netloom-tool`

## 1.6.0 - 2026-03-14

### Changed
- project branding now uses `netloom` as the primary name, with `netloom-tool` as the Python package distribution name
- added the `netloom` CLI entrypoint
- documentation and project metadata now point to `https://netloom.se` and `https://github.com/mathias-granlund/netloom`
- automatic collection paging now respects explicit `--limit` values for `list`, `get --all`, and `copy` instead of overriding them
- the bundled Bash completion script now supports the `netloom` executable

## 1.5.3 - 2026-03-13

### Changed
- `list`, `get --all`, and `copy` source reads now iterate through paged ClearPass collection responses until all matching entries are fetched instead of stopping after the first page
- `--filter` now applies across the full paged result set, and `--limit` acts as the per-request page size for paged collection reads
- built-in help and README guidance now explain the filtered paging behavior explicitly

## 1.5.2 - 2026-03-13

### Fixed
- `netloom copy` now omits blank `radius_secret` and `tacacs_secret` values from generated payloads so hidden source credentials are not replayed as empty strings on target updates or replacements
- `policyelements network-device` copy creates now fail before the API call with a clearer message when the source response does not include usable RADIUS, TACACS+, or SNMP credentials
- copy summaries now print item-level failure reasons directly in terminal output to make validation issues easier to diagnose without debug logging

## 1.5.1 - 2026-03-13

### Fixed
- `netloom copy` now uses the normal cached API catalog path for both source and target profiles instead of forcing a fresh `/api-docs` discovery on every run
- added regression coverage to keep the copy workflow aligned with the cache behavior used by the rest of the CLI

## 1.5.0 - 2026-03-13

### Added
- built-in `netloom copy <module> <service> --from=SOURCE --to=TARGET` workflow for copying resources between ClearPass profiles without shell-chaining separate export and import commands
- copy workflow support for `--dry-run`, `--match-by=auto|name|id`, `--on-conflict=fail|skip|update|replace`, and optional report artifacts via `--save-source`, `--save-payload`, and `--save-plan`
- parser, help text, completion, and integration coverage for the new `copy` built-in command

### Changed
- copy execution now fetches source objects, normalizes them against the destination write schema, strips response-only metadata, and reuses destination profile settings within a single command run

## 1.4.11 - 2026-03-13

### Fixed
- path override settings such as `NETLOOM_OUT_DIR`, `NETLOOM_STATE_DIR`, `NETLOOM_CACHE_DIR`, and `NETLOOM_APP_LOG_DIR` now resolve through the same config/profile loading path as the rest of the runtime settings
- profile-scoped path overrides such as `NETLOOM_OUT_DIR_PROD` are now respected
- `~` is now expanded in configured path overrides so values like `NETLOOM_OUT_DIR=~/responses` resolve to the user home directory as expected

## 1.4.10 - 2026-03-13

### Fixed
- saved ClearPass `list` responses can now be reused as `--file` input for write actions by unwrapping `_embedded.items` and dropping response `_links`
- file-backed `add`, `update`, and `replace` requests now filter response-only fields such as `id` out of the JSON body while still allowing path fields to resolve update/replace URLs
- empty optional container values from exported responses, such as `attributes: {}`, are now omitted from replayed write payloads when ClearPass expects the field to be absent instead of empty
- `--decrypt` now also disables secret masking in HTTP request debug logs so troubleshooting output matches the requested secret visibility
- client construction remains compatible with older test doubles and call sites that do not accept the new secret-masking parameter

## 1.4.9 - 2026-03-12

### Fixed
- `/api-docs` help notes now strip embedded HTML more cleanly instead of dumping raw tags into `--help` output
- list-action help notes now preserve multiline structure for filter documentation and similar table-style notes

## 1.4.8 - 2026-03-12

### Added
- `netloom server list`, `netloom server show`, and `netloom server use <profile>` built-in commands for switching between named ClearPass environments
- profile-aware configuration loading from `~/.config/netloom/profiles.env` and `~/.config/netloom/credentials.env`
- packaged `profiles.env.example` and `credentials.env.example` templates for per-user profile setup

### Changed
- environment loading now resolves profile-scoped keys such as `NETLOOM_SERVER_PROD` and `NETLOOM_CLIENT_SECRET_DEV` based on `NETLOOM_ACTIVE_PROFILE`
- shell completion and built-in help now include the `server` command surface and discovered profile names
- README now documents the profile-based configuration model and the replacement example files

## 1.4.7 - 2026-03-11

### Added
- `netloom-install-manpage` helper command to install the bundled `netloom(1)` page into a local `man1` directory after package installation
- packaged copy of the man page under `netloom/data/man/netloom.1` so the helper works from installed wheels and editable installs
- package metadata for classifiers, project URLs, and explicit license handling
- `LICENSE` file and `MANIFEST.in` for cleaner source and binary distributions
- GitHub Actions workflow to run tests and validate built distributions
- `build` and `twine` in the `.[dev]` extra for local release validation

### Changed
- README now documents the helper-based `man netloom` setup path
- README now documents local build and package validation commands

## 1.4.6 - 2026-03-11

### Added
- static `netloom(1)` man page at `man/netloom.1` for users who prefer standard Unix CLI documentation

### Changed
- README now points to the bundled man page and shows how to view it locally with `man -l`

## 1.4.5 - 2026-03-11

### Added
- property-based fuzz coverage with `hypothesis` for CLI parsing, recursive secret masking, and `calculate_count` query serialization

### Changed
- `hypothesis` is now included in the `.[dev]` extra
- local `.hypothesis/` state is ignored by git

## 1.4.4 - 2026-03-11

### Changed
- `--help` output now suppresses redundant `params:` sections for actions that already expose richer `body fields:` metadata
- query/path-oriented actions such as `list` and `get` still show `params:` when no body metadata is available

## 1.4.3 - 2026-03-11

### Fixed
- raw byte output now treats control-heavy byte streams as binary for console display instead of echoing unreadable control characters
- `calculate_count` query values are now serialized as lowercase `true` / `false` strings for ClearPass compatibility
- Swagger GET routes with unresolved placeholder-style base paths are no longer overclassified as `list` actions
- list endpoint smoke coverage now uses safer default query parameters and skips placeholder-dependent list routes

## 1.4.2 - 2026-03-11

### Added
- richer dynamic help metadata from ClearPass docs, including summaries, response codes, response content types, body field lists, and generated body examples when the API docs expose models
- direct token authentication via `NETLOOM_API_TOKEN` / `--api-token=...`
- token-file authentication via `NETLOOM_API_TOKEN_FILE` / `--token-file=...`
- binary response awareness for dynamically discovered download/export endpoints, including raw output auto-selection and filename inference from response headers

### Changed
- `list` is once again exposed in completion/help output alongside `get`
- raw output now writes binary payloads as bytes instead of forcing text decoding
- API catalog cache format bumped to v3 while keeping v2 cache loading compatibility

## 1.4.1 - 2026-03-09

### Changed
- removed transitional top-level compatibility wrapper modules
- moved command handlers into `netloom.cli.commands` so the package layout is now fully aligned with the `cli/core/io/logging` split
- cleaned the source release to exclude `.git`, `.env`, cache directories, Python bytecode, and `*.egg-info` artifacts
- updated tests and documentation to target only the v1.4.x module layout

## 1.4.0 - 2026-03-09

### Added
- environment-driven settings loader with XDG-style cache/state/output directories
- new package structure under `cli`, `core`, `io`, and `logging`
- `.env.example` for local configuration
- Ruff linting and formatting baseline in `pyproject.toml`

### Changed
- entrypoint now lives in `netloom.cli.main`
- help rendering moved to `netloom.cli.help`
- completion logic moved to `netloom.cli.completion`
- resolver and request/payload building moved into `netloom.core.resolver`
- response output and file loading split into `netloom.io.output` and `netloom.io.files`
- logger setup is deterministic and no longer depends on singleton initialization order
- cache and response output defaults moved out of the repository tree
- tests now target the action-aware v1.3.1+ API catalog structure

### Removed
- hardcoded ClearPass server and credential values from source control
- in-tree cache/log directory assumptions as the default runtime behavior

## 1.3.1

- action-aware API catalog cache
- parameterized Swagger endpoints preserved in cache
- normalized single `*_id` placeholders to `{id}`
- dynamic help and `list` alias for `get --all`
- configurable secret masking in output
