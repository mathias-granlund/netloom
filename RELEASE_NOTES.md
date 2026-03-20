# netloom v1.9.1

This release refines the new service-level `diff` workflow so it is easier to
trust and easier to read in day-to-day operator use. The main focus is better
field-level visibility, less noisy comparison input, and clearer reporting when
matching gets ambiguous.

## Highlights

- `diff` now reports nested `changed_fields` paths where possible instead of
  only top-level keys
- added `--fields=...` and `--ignore-fields=...` so comparisons can be focused
  on the parts of an object that actually matter
- console summaries now show before/after values for changed fields instead of
  only listing object names
- ambiguous target matches are now reported explicitly instead of being picked
  silently
- ClearPass diff normalization now ignores more response-only metadata, masked
  secret placeholders, and empty noise fields before comparison

## Examples

```bash
netloom policyelements role diff --from=lab --to=prod --all
netloom policyelements role diff --from=lab --to=prod --name=Guest --fields=description,attributes.role
netloom policyelements role diff --from=lab --to=prod --all --ignore-fields=updated_at,id
```

## Notes

- `diff` is still available as a service action only; there is no built-in
  `netloom diff ...` alias
- the console view still caps long sections for readability; a follow-up
  roadmap item is to add `--show-all` or `--max-items=N` for expanded terminal
  output
- existing `copy` behavior is unchanged
