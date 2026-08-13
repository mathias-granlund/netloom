# netloom v1.11.2

This release adds quieter automation output controls and a replayable
`netloom` command export format for normal read workflows.

## Highlights

- added `--log-level=none` and `NETLOOM_LOG_LEVEL=NONE` to suppress runtime log
  messages
- added `--format=netloom` for `get`, `get --all`, and `list` to render
  replayable `netloom ... add|replace|update --payload-json=...` commands
- added `--format=FORMAT` as the preferred output-format flag while preserving
  `--data-format=FORMAT` as a compatibility alias
- kept `netloom` output secret masking aligned with existing CLI behavior:
  values are masked by default and visible with `--decrypt`
- removed the tracked `NETLOOM_CONTEXT_PROMPT.md` context prompt file

## Examples

```bash
netloom identities endpoint get --id=1001 --format=netloom
netloom policyelements network-device list --format=netloom --out=network-devices.netloom
NETLOOM_LOG_LEVEL=NONE netloom identities endpoint list --limit=10
```

## Notes

- `--format=netloom` is intentionally limited to read workflows and is rejected
  before mutating commands run
- `--data-format=FORMAT` remains accepted for existing scripts
