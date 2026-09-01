# Netloom 2.0 Migration Plan

This plan keeps the migration behavior-preserving until the internal contracts are
ready to carry more of the runtime flow.

## Step 1: Define Internal Contracts

Status: implemented.

The first contract types live in `netloom.contracts`:

- `NetloomRequest`
- `ExecutionOptions`
- `NetloomResult`
- `HttpRequest`
- `HttpResponse`
- `PluginExecutionContext`
- `Plugin`
- `ExecutablePlugin`
- `PluginDefinition`

`PluginDefinition` mirrors the current runtime plugin surface so existing code can
adopt the contract without changing command behavior.

## Step 2: Extract Generic HTTP Transport

Status: implemented.

Move raw HTTP behavior out of vendor plugins and into `netloom.http`.

Target responsibilities:

- `netloom.http.client` executes `HttpRequest` objects.
- `netloom.http.client` returns `HttpResponse` objects.
- HTTP transport handles generic concerns only: method, URL, headers, params, body,
  TLS verification, timeout, response metadata, binary/text/JSON detection, and
  generic HTTP errors.
- HTTP transport must not know about modules, services, actions, catalogs, plugins,
  profiles, or CLI arguments.

ClearPass-specific path resolution, catalog lookup, authentication choices, request
payload construction, and response normalization stay in the ClearPass plugin.

Current implementation:

- `netloom.http.client.RequestsHttpClient` executes `HttpRequest` objects.
- `RequestsHttpClient.execute()` returns `HttpResponse` objects.
- Generic content-type, filename, and binary-response metadata handling lives in
  `netloom.http.metadata`.
- `netloom.core.resolver` now uses the shared metadata helpers for raw-output
  decisions instead of carrying duplicate content-type logic.
- `ClearPassClient.request_path()` now builds an `HttpRequest`, delegates transport
  to `RequestsHttpClient`, stores generic response metadata, and keeps ClearPass
  response interpretation/error logging at the plugin boundary.
- `ClearPassClient.raw_get_text()` provides a transport-backed path for ClearPass
  catalog documentation fetches while preserving the catalog builder fallback used
  by existing tests/fakes.

## Step 3: Move Execution Orchestration Into Core

Status: implemented.

Move generic execution flow out of `netloom.cli` while keeping vendor execution in
plugins.

Core responsibilities:

- Load and apply settings.
- Validate neutral `NetloomRequest` shape.
- Resolve the active plugin.
- Decide whether capability/catalog data is needed.
- Ask the active plugin for normalized capabilities/catalog data.
- Coordinate cross-plugin workflows such as copy, diff, import, and running-config
  export through plugin contracts.
- Return `NetloomResult` to the caller.

Plugin responsibilities:

- Authenticate using plugin/vendor rules.
- Fetch, load, cache, and normalize vendor catalog data.
- Resolve Netloom module/service/action intent to vendor API endpoints.
- Build `HttpRequest` objects.
- Call generic HTTP transport.
- Interpret vendor responses and errors.
- Return Netloom-level data to core.

CLI responsibilities after this step:

- Parse command-line syntax into `NetloomRequest` and `ExecutionOptions`.
- Call core.
- Render or write `NetloomResult` for terminal users.

Current implementation:

- `netloom.core.runtime.run_request()` accepts `NetloomRequest` plus
  `ExecutionOptions` and now owns plugin-backed execution orchestration:
  settings loading, CLI/API override application, logging setup, plugin
  resolution, plugin builtin dispatch, copy/diff dispatch, generic action
  lookup, client/auth/catalog setup, and `NetloomResult` wrapping.
- `netloom.cli.runtime.run_cli()` keeps lightweight CLI concerns such as version,
  help, and syntax-only builtins, then delegates plugin-backed execution to core.
- The command/action flow is implemented in `netloom.core.actions`, and the old
  CLI alias layer was intentionally retired during the Step 5 cleanup once the
  import points were redirected to the real owner module.
- Copy and diff workflow implementations now live in `netloom.core.copy` and
  `netloom.core.diff`; legacy CLI alias files for those flows were removed during
  Step 5 once the remaining tests/imports were updated.
- Running-config show command orchestration now lives in `netloom.core.show`; the
  legacy CLI alias was removed during Step 5 to keep the package layout obvious.
- Stale imports from the removed CLI compatibility modules were redirected to the
  owning core modules, with the remaining test suite updated to target those
  canonical locations.

## Step 4: Move To `src/` Layout And Finalize Boundaries

Status: implemented.

After contracts, HTTP transport, and execution ownership are stable, move the package
and tests into the final layout.

Target layout:

```text
src/netloom/
  __init__.py
  __main__.py
  contracts.py
  cli/
  core/
  http/
  io/
  logging/
  plugins/
    clearpass/
      plugin.py
      api.py
      catalog.py
      workflow_hooks.py
      swagger/
docs/
  index.html
  man/
tests/
  cli/
  core/
  http/
  io/
  logging/
  packaging/
  plugins/
    clearpass/
```

Boundary rule:

- `cli -> core`
- `core -> plugins`
- `plugins -> http`
- `http` imports no Netloom domain or plugin code
- Generic `io` and `logging` modules avoid CLI-specific behavior

Validation for the final step:

- Update `pyproject.toml` for `src` package discovery.
- Move tests into matching directories.
- Run the full test suite.
- Run lint/format checks.
- Build the package.
- Verify console scripts: `netloom`, `netloom-generate-manpages`, and
  `netloom-install-manpage`.

Current implementation:

- Package discovery uses the `src/` layout via `pyproject.toml`.
- Pytest discovery now points at the top-level `tests/` tree.
- `MANIFEST.in` includes the top-level tests and the real `examples/*.env.example`
  paths for source distributions.
- Runtime package boundaries are in place under `src/netloom`.
- Tests now live under a top-level grouped `tests/` tree that mirrors the package
  boundaries, with extra `logging` and `packaging` groups for support modules and
  distribution tooling.

## Step 5: Consolidate The Layout And Remove Stale Redundancy

Status: implemented.

Once the architecture is stable, reduce the number of small, low-value modules and
remove stale compatibility layers that no longer carry real behavior. The goal is to
improve navigability without crossing responsibility boundaries or hiding the actual
package structure.

Current cleanup decisions:

- Removed the stale compatibility aliases in `src/netloom/cli` that only re-exported
  functionality from the canonical `core` modules: `commands.py`, `copy.py`,
  `diff.py`, `import_config.py`, `show.py`, and `telemetry.py`.
- Removed `src/netloom/core/cache.py`, which was only a compatibility facade over
  `netloom.core.interactive_cache`, and redirected internal imports to the owning
  module.
- Renamed `src/netloom/core/plugin.py` to `src/netloom/core/plugin_registry.py`
  because it owns plugin discovery and registry behavior, not a plugin definition.
- Renamed `src/netloom/core/interactive.py` to
  `src/netloom/core/interactive_settings.py` because it owns the lightweight
  settings, profile, plugin, and path lookup used by cached help/completion paths,
  not an interactive runtime.
- Renamed `src/netloom/plugins/clearpass/client.py` to
  `src/netloom/plugins/clearpass/api.py` to make the ClearPass API adapter distinct
  from the generic HTTP transport in `netloom.http.client`.
- Renamed `src/netloom/plugins/clearpass/copy_hooks.py` to
  `src/netloom/plugins/clearpass/workflow_hooks.py` because it now contains
  ClearPass hooks for copy, diff, write payload preparation, and preflight checks.
- Follow-up module-name audit:
  - Worth renaming now:
    - `core/plugin.py` -> `core/plugin_registry.py`: registry/discovery ownership,
      not plugin contract ownership.
    - `plugins/clearpass/client.py` -> `plugins/clearpass/api.py`: ClearPass API
      adapter ownership, distinct from generic HTTP transport.
    - `plugins/clearpass/copy_hooks.py` -> `plugins/clearpass/workflow_hooks.py`:
      copy, diff, write payload, and preflight hooks now share the file.
    - `core/interactive.py` -> `core/interactive_settings.py`: lightweight
      settings ownership, not an interactive loop or shell.
  - Possible but not worth the churn now:
    - `core/actions.py`: broad, but it owns the `ACTIONS` map and generic CRUD
      handlers; `copy`, `diff`, `show`, and `import` are already split out.
    - `core/resolver.py`: broad, but its functions all resolve parsed command
      state into query params, payloads, output paths, and output format choices.
      A better name would need a real responsibility split.
    - `core/help.py`, `core/interactive_help.py`, and `core/help_shared.py`: the
      names are imperfect, but the current split still tracks regular help
      rendering, cached interactive/describe help, and shared catalog display
      helpers. A pure rename would not reduce the duplicated rendering logic.
    - `core/interactive_cache.py`: it could be called a catalog-cache loader, but
      that risks implying ownership of plugin cache building/writing; today it is
      specifically the cached-help/completion reader and projector.
    - `cli/catalog_runtime.py` and `core/catalog_runtime.py`: both names are broad,
      but the caller boundary is explicit enough and a rename would mostly churn
      tests and compatibility surfaces.
    - `core/import_config.py`, `core/running_config.py`, and `core/show.py`: these
      names follow the user-facing commands and exported format closely enough.
- Updated the affected tests to import directly from the owning `netloom.core.*`
  modules so the package boundary remains explicit.
- Kept the structural boundaries intact: CLI remains command parsing/rendering,
  while orchestration and workflow logic stay in `core`.

Design goal:

- Prefer one cohesive module per responsibility cluster.
- Merge helper modules only when they are tightly coupled and not independently
imported or externally documented.
- Keep domain boundaries large enough that the package remains easy to navigate.
- Avoid the false economy of making a single file "do everything" for a given
subsystem.

Recommended trade-off:

- Keep the current package boundaries (`cli`, `core`, `http`, `io`, `logging`,
`plugins`).
- Collapse files that are only thin compatibility shims, legacy wrappers, or tiny
helper-only modules when their purpose is no longer meaningful.
- Keep parser logic, runtime orchestration, transport code, and plugin-specific code
in separate modules even if a few small utility functions move together.

Likely cleanup targets:

- Remove stale compatibility alias modules that only exist for older imports when
the runtime no longer relies on them.
- Merge tiny helper utilities into the closest owning module when they are not
public API or independently meaningful.
- Consolidate command/flag normalization helpers that are used in only one command
flow.
- Remove redundant or duplicate wrapper files left behind by the Step 3/4
restructuring.
- Re-name or regroup files that still read as legacy CLI-only code even though their
logic is now core-owned.

Boundaries to retain:

- `cli` surfaces command parsing and terminal rendering only.
- `core` owns orchestration, runtime flow, and generic workflows.
- `plugins` owns vendor/auth/catalog behavior.
- `http` stays transport-only and generic.
- `io`/`logging` stay generic runtime support code.

Validation for this step:

- Audit imports and usage before deleting anything.
- Remove only files that are dead weight or clear compatibility leftovers.
- Run the focused tests for the affected area after each cleanup pass.
- Run the full test suite once the consolidation is stable.
- Re-check package build and console entry points after the final cleanup.

Validation completed for the current cleanup pass:

- Focused cleanup tests: 127 passed.
- Focused rename tests: 110 passed.
- Full test suite: 363 passed, 1 skipped.
- `ruff check .`: passed.
- `ruff format --check .`: passed.
- `python -m build`: passed.
- Console entry point metadata includes `netloom`, `netloom-generate-manpages`,
  and `netloom-install-manpage`.
- Smoke-tested `netloom --version`, `netloom-generate-manpages --check`, and
  `netloom-install-manpage --help` through their source entry point targets.
