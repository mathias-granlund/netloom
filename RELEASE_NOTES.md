# netloom v1.9.6

This release focuses on making the CLI help output easier to scan, especially
for dynamic actions discovered from the API catalog.

## Highlights

- migrated the CLI to a hybrid parser model with `argparse` handling stable
  built-ins and shared global flags while keeping dynamic plugin actions
  flexible
- simplified top-level, module, and service `--help` output and removed the
  remaining legacy top-level `copy` parser special-casing
- redesigned `list`, `get`, `add`, `update`, `replace`, and `delete` action
  help into a more compact, operator-focused format that still highlights
  selectors and required fields

## Examples

```bash
netloom policyelements network-device get ?
netloom policyelements network-device add ?
netloom logs system-event list ?
```

## Notes

- installable man pages still come from `netloom/data/man/`
- dynamic plugin command flags continue to be parsed permissively after the
  stable outer CLI layer
