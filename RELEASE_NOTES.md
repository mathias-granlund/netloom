# netloom v1.9.12

This release continues the ClearPass privilege-mapping work and promotes the
latest live-verified policyelements action aliases into the enforced rule set.

## Highlights

- promoted `policyelements/radius-dictionary-disable`,
  `radius-dictionary-enable`, `radius-dictionary-name-disable`, and
  `radius-dictionary-name-enable` as privilege-gated with `cppm_radius_dict`
- promoted `policyelements/service-disable`, `service-enable`,
  `service-name-disable`, `service-name-enable`, and `service-reorder` as
  privilege-gated with `cppm_services`
- tightened the evidence standard for future write-action mappings so weak
  `404`/`422`/fake-target results are no longer treated as sufficient proof
- updated `PLANNED_FEATURES.md` coverage to `79` privilege-gated verified,
  `5` baseline verified, and `108` unresolved retained services

## Examples

```bash
python -m netloom.plugins.clearpass.privilege_discovery --out=clearpass_privilege_discovery.json
netloom --catalog-view=full globalserverconfiguration operator-profile list --limit=1 --console
```

## Notes

- installable man pages still come from `netloom/data/man/`
- `PLANNED_FEATURES.md` tracks both the completed interactive performance
  work and the remaining ClearPass privilege-mapping backlog
- `globalserverconfiguration/messaging-setup` remains unpromoted because the
  latest focused probes still return `403`
