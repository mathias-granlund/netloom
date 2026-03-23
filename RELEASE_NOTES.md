# netloom v1.9.2

This release builds on the recent service-level `diff` work by making large
terminal reviews easier. The main focus is expanding console previews on demand
without changing the JSON report format or the underlying comparison logic.

## Highlights

- added `--show-all` so `diff` can print every listed changed item and changed
  field in the console when a full interactive review is needed
- added `--max-items=N` so operators can raise or lower the console preview cap
  without having to open the JSON artifact
- updated action help, README examples, and ClearPass manpages so the new diff
  display controls are documented consistently
- aligned release metadata and checked-in manpage headers with version `1.9.2`

## Examples

```bash
netloom policyelements role diff --from=lab --to=prod --all
netloom policyelements role diff --from=lab --to=prod --all --max-items=25
netloom policyelements role diff --from=lab --to=prod --all --show-all
netloom policyelements role diff --from=lab --to=prod --name=Guest --fields=description,attributes.role
```

## Notes

- `diff` is still available as a service action only; there is no built-in
  `netloom diff ...` alias
- the default console view still caps long sections for readability unless
  `--show-all` or `--max-items=N` is used
- existing `copy` behavior is unchanged
