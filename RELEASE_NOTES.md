# netloom v1.8.0

This release makes the ClearPass cache privilege-aware. `netloom cache update`
now reads the active API client's effective privileges from
`/api/oauth/privileges`, normalizes the access prefixes returned by ClearPass,
and filters verified services directly in the cached catalog.

## Highlights

- `netloom cache update` now integrates ClearPass privilege filtering directly
  into the normal catalog build instead of relying on a separate discovery
  command
- added verified live mappings for `endpoint`, `local-user`, `network-device`,
  `network-device-group`, and `admin-privilege`
- cache metadata now records the effective privileges seen during the build and
  which mapped services were filtered out
- documented the initial verified ClearPass mapping table for follow-up
  expansion in the next patch release

## Examples

```bash
netloom server use discovery
netloom cache update
netloom identities endpoint list --limit=10
```

## Notes

- only services with verified mappings are filtered automatically in `1.8.0`
- unmapped services are still preserved in the cache until more live mappings
  are confirmed
