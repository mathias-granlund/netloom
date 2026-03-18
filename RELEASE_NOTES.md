# netloom v1.7.6

This release splits the static manual into a shared `netloom(1)` reference and
a dedicated `netloom-clearpass(7)` plugin guide so the ClearPass workflow can be
documented in much more depth without overloading the main CLI manual.

## Highlights

- added a new `netloom-clearpass(7)` manual with ClearPass-specific
  configuration, auth, discovery, filtering, copy, and example guidance
- trimmed `netloom(1)` back to the shared CLI surface: plugin selection,
  profiles, cache, global options, output behavior, and shared paths
- updated `netloom-install-manpage` so it installs both manuals into the
  correct man sections
- copy source, payload, and plan artifacts now default into `NETLOOM_OUT_DIR`
  with generated JSON filenames unless you override them explicitly

## Examples

```bash
netloom-install-manpage
man netloom
man netloom-clearpass
```

## Notes

- `netloom(1)` remains the right place for the shared command model and
  built-in commands
- plugin-specific depth should now move into plugin manuals as more plugins are
  added
