# netloom v1.9.11

This release shifts the planning focus from interactive performance to
ClearPass privilege coverage, while also promoting the latest verified live
service mappings into the enforced rule set.

## Highlights

- renamed the old performance-only roadmap into `PLANNED_FEATURES.md` and
  moved ClearPass privilege coverage to the top priority
- added a current coverage summary for the retained full ClearPass catalog:
  `35` verified mappings and `156` remaining unmapped retained services
- verified and promoted `globalserverconfiguration/operator-profile ->
  auth_profiles`
- verified and promoted `policyelements/radius-dictionary ->
  cppm_radius_dict`
- improved the live discovery runner so it can fall back when
  `/api/operator-profile/name/<name>` is not supported cleanly by the target
  ClearPass server
- added a reusable `CLEARPASS_PRIVILEGE_MAPPING_PROMPT.md` prompt for future
  live mapping rounds

## Examples

```bash
python -m netloom.plugins.clearpass.privilege_discovery --out=clearpass_privilege_discovery.json
netloom --catalog-view=full globalserverconfiguration operator-profile list --limit=1 --console
```

## Notes

- installable man pages still come from `netloom/data/man/`
- `PLANNED_FEATURES.md` now tracks both the completed interactive performance
  work and the remaining ClearPass privilege-mapping backlog
- `globalserverconfiguration/messaging-setup` remains unpromoted because it
  still returns `404` even for admin on the current ClearPass server
