# netloom v1.9.14

This release adds a disciplined ClearPass brute-force candidate workflow,
promotes a new batch of live-verified mappings, and upgrades several retained
services from unresolved to baseline-verified.

## Highlights

- added `netloom.plugins.clearpass.privilege_bruteforce` to build ordered
  candidate privilege batches from the unresolved backlog plus a real admin
  privilege dump
- taught the discovery runner to accept mixed single-key and combo candidates
  from one candidate file
- promoted eight new live-verified mappings, including
  `endpointvisibility/global-settings`, `settings`, `subnet-mapping`,
  `windows-hotfix`, `guestconfiguration/authentication`, `guestmanager`,
  `print`, and `sessioncontrol/session`
- promoted `globalserverconfiguration/all-privileges` and
  `localserverconfiguration/cppm-version`, `version`, and `fips` as baseline
  verified services
- updated `PLANNED_FEATURES.md` coverage to `95` privilege-gated verified,
  `9` baseline verified, and `88` unresolved retained services

## Examples

```bash
python -m netloom.plugins.clearpass.privilege_discovery --out=clearpass_privilege_discovery.json
netloom --catalog-view=full globalserverconfiguration operator-profile list --limit=1 --console
```

## Notes

- installable man pages still come from `netloom/data/man/`
- `PLANNED_FEATURES.md` tracks both the completed interactive performance
  work and the remaining ClearPass privilege-mapping backlog
- `globalserverconfiguration/messaging-setup`, `guestconfiguration/pass`, and
  `guestconfiguration/weblogin` remain unpromoted because the latest focused
  probes still return baseline `403`
- many remaining unresolved services still expose only parameterized paths,
  so a future probe improvement is needed to test them safely
