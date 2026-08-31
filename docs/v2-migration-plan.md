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
- `netloom.cli.commands` is a compatibility alias for `netloom.core.actions` so
  existing imports and monkeypatch-based tests keep targeting the actual action
  implementation.
- Copy and diff workflow implementations now live in `netloom.core.copy` and
  `netloom.core.diff`; the old `netloom.cli.copy` and `netloom.cli.diff` modules
  are compatibility aliases.
- Running-config show command orchestration now lives in `netloom.core.show`; the
  old `netloom.cli.show` module is a compatibility alias.
- Stale imports from the removed `netloom.cli.commands` module were redirected to
  `netloom.core.actions`, and running-config helper imports were redirected to
  `netloom.core.running_config`.

## Step 4: Move To `src/` Layout And Finalize Boundaries

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
      resolver.py
      catalog.py
      client.py
      swagger/
docs/
  index.html
  man/
tests/
  cli/
  core/
  http/
  io/
  plugins/
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
