# netloom v1.6.4

This release starts the move from the old `arapy`-centered layout to a real modular `netloom` architecture.

## Highlights

- introduced a new shared `netloom/` runtime package
- added plugin support under `netloom/plugins/<plugin>`
- added the first plugin at `netloom/plugins/clearpass`
- added `netloom load <plugin>` to select the active plugin before using the normal CLI flow
- switched the primary `netloom` entrypoint to the modular runtime
- added support for preferred `NETLOOM_*` config and environment names
- kept legacy `arapy` / `ARAPY_*` compatibility during the transition

## What changed

The CLI is now split into:

- shared CLI/core logic in `netloom/cli`, `netloom/core`, `netloom/io`, and `netloom/logging`
- plugin-specific behavior in `netloom/plugins/clearpass`

That means the common command flow is now shared, while vendor-specific client behavior and endpoint handling can live behind plugins.

A new workflow is now supported:

```bash
netloom load clearpass
netloom cache update
netloom <module> <service> <action>
```

## Compatibility

This release keeps the transition smooth:

- `arapy` still works as a compatibility command
- legacy `ARAPY_*` environment variables are still accepted
- legacy `~/.config/arapy/` config can still be used
- `netloom` now prefers `NETLOOM_*` and `~/.config/netloom/`

## Docs and packaging

- updated README for the new plugin-based workflow
- updated architecture documentation to reflect the current repo layout
- bumped package version to `1.6.4`
- kept both `netloom` and `arapy` entrypoints available during the migration

## Upgrade notes

Recommended new setup:

```bash
netloom load clearpass
netloom cache update
```

If you already use existing `ARAPY_*` variables or `~/.config/arapy/`, you do not need to migrate immediately. They still work in this release.
