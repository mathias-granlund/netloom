# netloom v1.10.3

This release refactors the CLI entrypoint into smaller orchestration modules
while keeping the public CLI behavior intact.

## Highlights

- split `netloom.cli.main` into focused runtime, catalog/help, builtin, deps,
  and telemetry modules while preserving existing imports and command behavior
- kept lazy-import boundaries and command-dispatch compatibility intact, so
  completions, help, cache update flow, and plugin-backed commands still work
- removed a small amount of stale code, including dead help helpers and an
  unused config constant

## Examples

```bash
netloom --help
netloom identities endpoint list
```

## Notes

- this release is primarily an internal maintenance release focused on CLI
  structure and cleanup rather than new user-facing features
