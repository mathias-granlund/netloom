# netloom v1.7.1

This release makes `copy` available as a normal service action while keeping
the old top-level syntax as a compatibility alias.

## Highlights

- preferred syntax is now `netloom <module> <service> copy ...`
- legacy alias `netloom copy <module> <service> ...` still works
- help and completion now present `copy` beside the normal service actions

## Examples

```bash
netloom policyelements network-device copy --from=dev --to=prod --all --dry-run
netloom copy policyelements network-device --from=dev --to=prod --all --dry-run
```

## Notes

The action-style form is now the recommended syntax because it lets users stay
in the same module/service path while moving from inspection commands like
`get`, `list`, and `?` into copy workflows.
