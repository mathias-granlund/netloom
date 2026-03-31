# netloom v1.9.15

This release continues the ClearPass privilege-mapping work, closes the last
remaining `globalserverconfiguration` gaps, and fixes help output for
multi-part path selectors.

## Highlights

- promoted `globalserverconfiguration/attribute-name` to
  `cppm_attributes` using a real `entity_name=LocalUser`, `name=Title` probe
- promoted `globalserverconfiguration/messaging-setup` to
  `cppm_admin_user_pass_policy` after confirming it flips both `GET` and
  `POST` from baseline `403` to authenticated responses
- fixed CLI help and cached interactive help so routes like
  `attribute-name` show grouped selector requirements such as
  `--entity-name=VALUE --name=VALUE`
- documented that `GET /api/attribute` returns the default available
  attributes per `entity_name`, while custom attributes can also exist
- updated `PLANNED_FEATURES.md` coverage to `125` privilege-gated verified,
  `10` baseline verified, and `57` unresolved retained services

## Examples

```bash
python -m netloom.plugins.clearpass.privilege_discovery --out=clearpass_privilege_discovery.json
netloom globalserverconfiguration attribute-name get --entity_name=LocalUser --name=Title --console
```

## Notes

- installable man pages still come from `netloom/data/man/`
- `PLANNED_FEATURES.md` tracks both the completed interactive performance
  work and the remaining ClearPass privilege-mapping backlog
- `certificateauthority` is now effectively the only remaining
  higher-priority unmapped area in the retained ClearPass catalog
- several lower-value unresolved retained services are candidates to hide from
  the CLI view later if they stay unmapped
