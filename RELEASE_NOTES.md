# netloom v1.7.5

This release makes filtering easier to use in day-to-day CLI work and trims
the verbose imported filter notes from dynamic terminal help.

## Highlights

- added shorthand filter support such as
  `--filter=name:equals:TEST`
- kept full JSON filters for advanced automation and compound expressions
- replaced the large ClearPass filter note dump in CLI action help with a
  compact operator and example summary
- updated README and help examples to show the new filter shorthand

## Examples

```bash
netloom identities endpoint list --filter=name:equals:TEST
netloom identities endpoint list --filter=id:in:1,2,3
netloom identities endpoint list --filter='{"$and":[{"name":{"$contains":"TEST"}},{"status":{"$eq":"Known"}}]}'
```

## Notes

- shorthand operators: `equals`, `not-equals`, `contains`, `in`, `not-in`,
  `gt`, `gte`, `lt`, `lte`, `exists`
- full JSON remains the recommended path for complex filters like `$and`,
  `$or`, `$not`, and regex
