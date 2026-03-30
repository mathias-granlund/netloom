# netloom v1.9.13

This release continues the ClearPass privilege-mapping work and promotes the
latest live-verified platform certificate and Insight action mappings into the
enforced rule set.

## Highlights

- promoted `platformcertificates/self-signed-cert` as privilege-gated with
  `cppm_certificates` using a live verified POST payload
- promoted `insight/alert-disable`, `alert-enable`, `alert-mute`,
  `alert-unmute`, `report-disable`, `report-enable`, and `report-run` into
  the enforced mapping set
- hardened the write-probe payload builder so reversible discovery probes can
  use minimal synthetic required values instead of placeholder-heavy swagger
  examples
- updated `PLANNED_FEATURES.md` coverage to `87` privilege-gated verified,
  `5` baseline verified, and `100` unresolved retained services

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
