# netloom v1.8.3

This release makes the default generated files from normal CLI runs unique by
adding timestamps to their filenames. That covers the optional application log
file under `NETLOOM_APP_LOG_DIR` and the auto-generated response and copy
artifact files under `NETLOOM_OUT_DIR`.

## Highlights

- default runtime log files now use a timestamped filename, which keeps each
  command run in its own log file by default when file logging is enabled
- auto-generated response files now use timestamped filenames instead of fixed
  names like `<service>_<action>.json`, so repeated commands no longer
  overwrite the previous saved output
- explicit `NETLOOM_LOG_FILE` overrides still win, so pinned log paths keep
  working exactly as configured
- the change does not alter explicit user-provided output paths

## Examples

```bash
netloom policyelements role list
ls ~/.local/state/netloom/responses/

export NETLOOM_LOG_TO_FILE=true
netloom server show
ls ~/.local/state/netloom/logs/
```

## Notes

- if you already set `NETLOOM_LOG_FILE`, nothing changes for that workflow
- if you already set `--out`, `--save-source`, `--save-payload`, or `--save-plan`,
  those explicit paths still win unchanged
