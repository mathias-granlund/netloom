# netloom v1.8.1

This release expands the verified ClearPass privilege mapping table and ships a
reusable in-plugin discovery runner so the mapping can keep growing safely over
time. With the current verified rule set, the same minimal discovery profile
now filters 30 mapped services from the ClearPass catalog cache.

## Highlights

- expanded the verified live mapping set across additional
  `globalserverconfiguration`, `identities`, `localserverconfiguration`,
  `logs`, and `policyelements` services
- refined several earlier broad mappings down to more specific effective
  runtime privilege keys such as `api_clients`, `guest_users`,
  `cppm_licenses`, and `cppm_radius_dyn_autz_template`
- moved the ClearPass mapping notes into the plugin folder and added the
  reusable `python -m netloom.plugins.clearpass.privilege_discovery` workflow
- kept a short list of accepted-but-not-yet-verified privileges documented for
  the next mapping rounds

## Examples

```bash
netloom server use discovery
netloom cache update
python -m netloom.plugins.clearpass.privilege_discovery --limit=10
```

## Notes

- only verified mappings are enforced automatically, so some unmapped services
  are still preserved conservatively in the cache
- the remaining unresolved services are concentrated in a much smaller set of
  harder cases and can now be targeted with the in-plugin discovery runner
