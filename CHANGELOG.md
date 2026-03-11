# Changelog

## 1.4.7 - 2026-03-11

### Added
- `arapy-install-manpage` helper command to install the bundled `arapy(1)` page into a local `man1` directory after package installation
- packaged copy of the man page under `arapy/data/man/arapy.1` so the helper works from installed wheels and editable installs
- package metadata for classifiers, project URLs, and explicit license handling
- `LICENSE` file and `MANIFEST.in` for cleaner source and binary distributions
- GitHub Actions workflow to run tests and validate built distributions
- `build` and `twine` in the `.[dev]` extra for local release validation

### Changed
- README now documents the helper-based `man arapy` setup path
- README now documents local build and package validation commands

## 1.4.6 - 2026-03-11

### Added
- static `arapy(1)` man page at `man/arapy.1` for users who prefer standard Unix CLI documentation

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
- direct token authentication via `ARAPY_API_TOKEN` / `--api-token=...`
- token-file authentication via `ARAPY_API_TOKEN_FILE` / `--token-file=...`
- binary response awareness for dynamically discovered download/export endpoints, including raw output auto-selection and filename inference from response headers

### Changed
- `list` is once again exposed in completion/help output alongside `get`
- raw output now writes binary payloads as bytes instead of forcing text decoding
- API catalog cache format bumped to v3 while keeping v2 cache loading compatibility

## 1.4.1 - 2026-03-09

### Changed
- removed transitional top-level compatibility wrapper modules
- moved command handlers into `arapy.cli.commands` so the package layout is now fully aligned with the `cli/core/io/logging` split
- cleaned the source release to exclude `.git`, `.env`, cache directories, Python bytecode, and `*.egg-info` artifacts
- updated tests and documentation to target only the v1.4.x module layout

## 1.4.0 - 2026-03-09

### Added
- environment-driven settings loader with XDG-style cache/state/output directories
- new package structure under `cli`, `core`, `io`, and `logging`
- `.env.example` for local configuration
- Ruff linting and formatting baseline in `pyproject.toml`

### Changed
- entrypoint now lives in `arapy.cli.main`
- help rendering moved to `arapy.cli.help`
- completion logic moved to `arapy.cli.completion`
- resolver and request/payload building moved into `arapy.core.resolver`
- response output and file loading split into `arapy.io.output` and `arapy.io.files`
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
