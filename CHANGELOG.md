# Changelog

## 1.10.2 - 2026-03-31

### Changed
- added short vendor-style descriptions for the ClearPass API modules in both
  normal `--help` output and the cached interactive help path, so top-level
  module listings now read more like traditional network vendor CLIs
- made the markdown manpages under `man/` the authoring source of truth and
  added `python -m netloom.generate_manpages` plus
  `python -m netloom.generate_manpages --check` to generate and verify the
  installable manpages under `netloom/data/man/`
- refreshed the shared and ClearPass manpage content to document canonical
  full service names, vendor-style `?` help behavior, and privilege-aware
  command visibility
- replaced hard-coded example profile names in the manpages and README with
  generic placeholders such as `<profile>`, `<source-profile>`, and
  `<target-profile>`
- aligned package metadata, release notes, README badge, and checked-in
  manpage version headers for the `1.10.2` release

## 1.10.1 - 2026-03-31

### Changed
- added vendor-style Bash `?` help for the current command context so inline
  help can be shown without pressing `Enter`, while keeping the existing
  `?` + `Enter` flow available
- taught the ClearPass catalog builder to capture service descriptions and
  canonical service names from `/api-docs`, which now lets module help and
  completion show names such as `certificate-chain`,
  `certificate-export`, `certificate-sign-request`, and `onboard-device`
- unified normal help, cached interactive help, runtime service resolution,
  and Bash completion around the same canonical ClearPass service naming so
  `netloom <module>`, `--help`, `?`, and command execution stay consistent
- restored privilege-aware visibility for user-facing command lists so only
  baseline-accessible or privilege-verified ClearPass services are shown,
  while canonical names still resolve correctly behind the scenes
- aligned package metadata, release notes, README badge, and checked-in
  manpage version headers for the `1.10.1` release

## 1.9.15 - 2026-03-31

### Changed
- continued the ClearPass privilege-mapping work and promoted
  `globalserverconfiguration/attribute-name -> cppm_attributes` and
  `globalserverconfiguration/messaging-setup -> cppm_admin_user_pass_policy`
- taught both normal help and cached interactive help to show multi-part path
  selectors correctly, including `attribute-name` routes that require both
  `--entity-name` and `--name`
- clarified the ClearPass attribute endpoint notes so the default per-entity
  attributes and support for custom attributes are both documented
- updated `PLANNED_FEATURES.md` coverage to `125` privilege-gated verified,
  `10` baseline verified, and `57` unresolved retained services, with
  `certificateauthority` now effectively the only remaining higher-priority
  mapping area
- aligned package metadata, release notes, README badge, and checked-in
  manpage version headers for the `1.9.15` release

## 1.9.14 - 2026-03-31

### Added
- added `netloom.plugins.clearpass.privilege_bruteforce` to turn unresolved
  retained services plus a real admin privilege dump into ordered
  brute-force candidate batches

### Changed
- updated the ClearPass discovery runner so candidate files can mix single-key
  and combo guesses in one ordered list
- continued the ClearPass privilege-mapping work and promoted
  `endpointvisibility/global-settings`, `settings`, `subnet-mapping`,
  `windows-hotfix`, `guestconfiguration/authentication`, `guestmanager`,
  `print`, and `sessioncontrol/session`
- promoted `globalserverconfiguration/all-privileges` and
  `localserverconfiguration/cppm-version`, `version`, and `fips` as
  baseline-verified services
- updated `PLANNED_FEATURES.md` coverage to `95` privilege-gated verified,
  `9` baseline verified, and `88` unresolved retained services
- aligned package metadata, release notes, README badge, and checked-in
  manpage version headers for the `1.9.14` release

## 1.9.13 - 2026-03-30

### Changed
- continued the ClearPass privilege-mapping work and promoted `platformcertificates/self-signed-cert -> cppm_certificates`
- promoted the remaining live-verified Insight action aliases, including `alert-disable`, `alert-enable`, `alert-mute`, `alert-unmute`, `report-disable`, `report-enable`, and `report-run`
- hardened the ClearPass write-probe payload builder so reversible probes can synthesize minimal required values for services whose swagger examples use empty placeholders
- updated `PLANNED_FEATURES.md` coverage to `87` privilege-gated verified, `5` baseline verified, and `100` unresolved retained services
- aligned package metadata, release notes, README badge, and checked-in manpage version headers for the `1.9.13` release

## 1.9.12 - 2026-03-29

### Changed
- continued the ClearPass privilege-mapping work and promoted the `policyelements` action aliases for `radius-dictionary-*` and `service-*` as privilege-gated mappings under `cppm_radius_dict` and `cppm_services`
- tightened the verification standard for future write-action privilege mappings so weak `404`/`422`/fake-target results are no longer treated as sufficient proof
- updated `PLANNED_FEATURES.md` coverage to `79` privilege-gated verified, `5` baseline verified, and `108` unresolved retained services
- aligned package metadata, release notes, README badge, and checked-in manpage version headers for the `1.9.12` release

## 1.9.11 - 2026-03-27

### Added
- added `CLEARPASS_PRIVILEGE_MAPPING_PROMPT.md` with a reusable prompt for future live ClearPass privilege-discovery rounds

### Changed
- renamed the old `CACHE_PERFORMANCE_PLAN.md` roadmap into `PLANNED_FEATURES.md` and broadened it into a general planning document
- moved ClearPass privilege coverage to the top priority, including a current coverage summary and the grouped list of the remaining `156` unmapped retained services
- verified and promoted `globalserverconfiguration/operator-profile -> auth_profiles`
- verified and promoted `policyelements/radius-dictionary -> cppm_radius_dict`
- hardened the ClearPass discovery runner so operator-profile lookup/update works even when the ClearPass server does not support the old name-based profile endpoint cleanly
- aligned package metadata, release notes, README badge, and checked-in manpage version headers for the `1.9.11` release

## 1.9.10 - 2026-03-26

### Changed
- completed Phase 1.7 by adding timing instrumentation for `netloom cache update`, including buckets for authentication, `/api-docs`, privileges, module listings, subdocuments, catalog build, and cache/index writes
- added lightweight user-facing cache-update progress reporting so long refresh runs show visible forward movement instead of looking hung
- confirmed from live timing data that cache rebuild is network-bound, with subdocument fetches dominating the total runtime
- updated `PLANNED_FEATURES.md` to mark Phase 1.7 complete, defer parallel rebuild work for now, and prefer progress UX over deeper rebuild optimization
- aligned package metadata, release notes, README badge, and checked-in manpage version headers for the `1.9.10` release

## 1.9.9 - 2026-03-26

### Changed
- continued Phase 1.6 startup work by moving cached help and completion onto lighter interactive help/cache/config layers with separate timing buckets for import cost and actual work
- added a dedicated `NETLOOM_COMPLETION_TIMING=1` switch so shell-completion profiling can be enabled without turning on help timing output
- updated the Bash completion wrapper so real `<TAB>` completion can surface `[netloom timing]` lines while still suppressing unrelated stderr noise
- reduced measured cached completion latency to roughly `26-33 ms`, with `load_core_cached_catalog` around `3.7-4.8 ms`
- reduced measured cached help latency to roughly `43-44 ms`, with `load_core_cached_catalog` around `4.1-4.7 ms`
- added lightweight-vs-full help parity tests and shared help primitives to reduce future drift risk between the fast path and the general runtime path
- refreshed `PLANNED_FEATURES.md`, release notes, and versioned metadata for the `1.9.9` release

## 1.9.8 - 2026-03-26

### Changed
- completed the completion-first Phase 1.5 follow-up by moving interactive cached catalog reads into a core lightweight loader that avoids plugin catalog imports on normal cached runs
- routed completion and compact help through the new core cache loader while preserving plugin/runtime fallback behavior on cache misses
- delayed more runtime setup for trivial help and version paths so interactive latency is now largely startup-bound instead of plugin-import-bound
- reduced cached interactive help latency from roughly `155-195 ms` in the hot path to roughly `15-20 ms` total in measured live runs
- reduced cached catalog load time for interactive help from roughly `143-189 ms` on the old plugin-import-heavy path to roughly `2.9-3.3 ms` with `load_core_cached_catalog`
- updated `PLANNED_FEATURES.md` with the new measured timings, completed Phase 1.5 status, and reordered next steps
- aligned package metadata, README badge, release notes, and checked-in manpage version headers for the `1.9.8` release

## 1.9.7 - 2026-03-24

### Added
- added `PLANNED_FEATURES.md` in the project root to track the cache-performance work, current measurements, and next optimization step

### Changed
- compact cache/index Phase 1 is now documented as complete, with the next focus set to bypassing plugin loading for fast help/completion paths
- CLI timing now uses only `NETLOOM_CLI_TIMING`
- aligned package metadata, README badge, and release notes for the `1.9.7` release

## 1.9.6 - 2026-03-24

### Changed
- migrated CLI parsing to a hybrid model with `argparse` handling stable built-ins and shared global flags while the dynamic plugin command surface remains custom
- removed the remaining parser special-casing for the old top-level `netloom copy <module> <service> ...` alias
- simplified top-level, module, and service help output so it is smaller and more context-focused
- redesigned `list`, `get`, `add`, `update`, `replace`, and `delete` action help into compact task-oriented layouts that emphasize selectors, required fields, and common options
- updated the compact sort hint to show the actual `--sort=+FIELD|-FIELD` form

## 1.9.5 - 2026-03-24

### Changed
- updated the package workflow from `actions/checkout@v4` to `@v5`, `actions/setup-python@v5` to `@v6`, and artifact transfer steps to `@v6` for the Node 24 transition path
- updated the Pages workflow checkout step from `actions/checkout@v4` to `@v5`
- aligned package metadata, release notes, README badge, and checked-in manpage version headers for the `1.9.5` release

## 1.9.4 - 2026-03-24

### Changed
- rewrote the README into a shorter quick-start guide focused on overview, install, minimal configuration, first run, practical examples, and links to deeper docs
- moved the repository documentation split toward a single manpage source of truth under `netloom/data/man/`, while turning the top-level `man/` directory into GitHub-friendly Markdown references
- restored detailed shell completion and `--filter=` guidance in the shared and ClearPass manpage references
- aligned release metadata and checked-in manpage version headers for the `1.9.4` release

## 1.9.3 - 2026-03-24

### Added
- added secure runtime client-secret resolution through OS keychains via `NETLOOM_CLIENT_SECRET_REF`, using the fixed service namespace `netloom/<plugin>`
- added a shared secret loader and regression coverage for missing `keyring`, missing backend, missing keychain entry, and plaintext fallback behavior

### Changed
- ClearPass login now resolves client secrets lazily at runtime while keeping existing `api_token` and `api_token_file` bypass behavior unchanged
- `netloom server show`, README guidance, example env files, and the ClearPass manpage now distinguish keychain-backed secrets from plaintext configuration and document WSL/headless Linux setup
- aligned release metadata and checked-in manpage version headers for the `1.9.3` release

## 1.9.2 - 2026-03-23

### Added
- added `--show-all` and `--max-items=N` to the service-level `diff` workflow so console previews can expand beyond the default summary cap

### Changed
- updated `diff` help text, README examples, and ClearPass manpages to document the new console expansion options
- aligned checked-in release metadata and manpage version headers for the `1.9.2` release
- removed the legacy top-level `netloom copy <module> <service> ...` alias in favor of the service-level `netloom <module> <service> copy ...` form
- updated help, completion, and roadmap text to reflect Phase 1 closure and the next Phase 2 focus

## 1.9.1 - 2026-03-20

### Changed
- refined the service-level `diff` workflow with nested `changed_fields` paths, richer before/after JSON detail, explicit ambiguous-match reporting, and new `--fields` / `--ignore-fields` comparison filters
- improved ClearPass diff normalization so more response-only metadata, masked secret placeholders, and empty noise are ignored before comparison
- tightened the `diff` action help text so only real flags are listed as options and the reporting behavior is explained more clearly

## 1.9.0 - 2026-03-20

### Added
- added a service-level `diff` action with `netloom <module> <service> diff --from=SOURCE --to=TARGET` for profile-to-profile comparison
- added timestamped JSON diff reports with summary counts for `same`, `different`, `only_in_source`, and `only_in_target`
- added plugin-level diff normalization hooks so providers can ignore noisy response-only fields before comparison

### Changed
- service help, completion, and dispatch now expose `diff` alongside the existing action surface
- shared comparison validation and match-resolution helpers are now reused between `copy` and `diff`
- ClearPass now normalizes diff inputs conservatively to reduce false positives from ids, links, timestamps, and similar response metadata

## 1.8.3 - 2026-03-20

### Changed
- default runtime log filenames under `NETLOOM_APP_LOG_DIR` now include a timestamp so separate `netloom` command runs do not reuse the same log file
- auto-generated response files under `NETLOOM_OUT_DIR` now include a timestamp so repeated commands do not overwrite default `list/get/write/copy` artifacts
- explicit `NETLOOM_LOG_FILE` overrides still keep their configured filename unchanged

## 1.8.2 - 2026-03-20

### Added
- added a dual-view ClearPass catalog cache that retains the full discovered catalog while exposing a stricter default visible catalog for normal CLI use
- added `--catalog-view=visible|full` so help, completion, and command discovery can switch explicitly between the access-aware catalog and the full retained vendor catalog

### Changed
- `netloom cache update` for ClearPass now stores a default visible module/service view and keeps the full discovered catalog as retained metadata for troubleshooting
- context-aware help, completion, and normal catalog loading now use the visible catalog by default so the active API client only sees verified/baseline-allowed modules and services
- updated README guidance, release notes, and tests to reflect the new access-aware catalog visibility behavior

## 1.8.1 - 2026-03-19

### Added
- added a reusable ClearPass privilege discovery runner under `netloom.plugins.clearpass.privilege_discovery` for future live mapping rounds
- expanded the checked-in ClearPass mapping table with additional verified services and documented the still-accepted-but-unverified candidates separately

### Changed
- expanded the built-in ClearPass privilege rule set substantially so `netloom cache update` can filter more inaccessible services from the cached catalog
- moved the ClearPass privilege mapping document into the plugin folder so the verification notes now live with the ClearPass implementation
- ignored temporary discovery caches and JSON reports so repeated mapping passes do not clutter the working tree

## 1.8.0 - 2026-03-19

### Added
- added built-in ClearPass privilege mapping data and a checked-in verification summary for the services that have been confirmed live so far
- added regression coverage for runtime privilege normalization and privilege-aware catalog filtering

### Changed
- `netloom cache update` for the ClearPass plugin now reads `/api/oauth/privileges`, normalizes `#` and `?` access prefixes, and filters mapped services directly into the cached catalog
- the ClearPass API catalog cache format is now version `4` and stores privilege-filter metadata alongside the generated modules and services
- the temporary standalone privilege-discovery command surface has been removed now that the verified mapping logic is integrated into the normal cache build path

## 1.7.6 - 2026-03-18

### Added
- added a dedicated `netloom-clearpass(7)` plugin manual with detailed ClearPass-specific configuration, authentication, discovery, filtering, copy, and example guidance

### Changed
- refocused `netloom(1)` on the shared CLI surface so plugin-specific behavior can live in separate manuals
- updated `netloom-install-manpage` to install both the shared `netloom(1)` page and the ClearPass plugin guide into their respective man sections
- updated packaged manpage assets, README install guidance, and release metadata for the split manual layout
- copy artifact files now default into `NETLOOM_OUT_DIR` with generated JSON filenames when `--save-source`, `--save-payload`, or `--save-plan` are not provided explicitly

## 1.7.5 - 2026-03-18

### Changed
- added shorthand filter syntax for common cases such as `--filter=name:equals:TEST` while keeping full JSON filter expressions available for advanced usage
- list-style help output now replaces the imported ClearPass filter documentation dump with a compact CLI-focused filter guide
- updated README guidance and examples to reflect the shorthand filter workflow

## 1.7.4 - 2026-03-18

### Changed
- replaced the flat plugin `profiles.env` and `credentials.env` files with a more scalable layout under `profiles/<profile>.env` and `credentials/<profile>.env`
- added plugin-level `defaults.env` fallback support so shared settings can be defined once and overridden only where needed per profile
- updated configuration examples and README guidance to reflect the new per-profile directory structure

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
- the old top-level `netloom copy <module> <service> ...` form remained available temporarily during the `1.7.1` migration period
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
- introduced an initial top-level `netloom copy <module> <service> --from=SOURCE --to=TARGET` workflow for copying resources between ClearPass profiles without shell-chaining separate export and import commands
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
