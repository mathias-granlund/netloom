# netloom v1.11.1

This release adds the first interactive shell workflow and introduces Delinea
Secret Server as a shared read-only keystore backend for ClearPass secrets.

## Highlights

- added `netloom shell`, an interactive mode with context navigation,
  context-aware help, history, completion, `show context`, `top`, `exit`,
  `quit`, and `do <command>` for root-level commands
- added `secretserver://<profile>/<path>?field=<slug>` support for
  `NETLOOM_CLIENT_SECRET_REF`, while preserving keychain and plaintext fallback
  behavior
- added a shared Secret Server provider under
  `~/.config/netloom/keystores/secretserver/` with defaults, profile, and
  credential files
- taught ClearPass `policyelements network-device` add, update, replace, and
  copy workflows to backfill missing or masked `radius_secret` and
  `tacacs_secret` values from Secret Server by device name
- added plugin write-payload hooks so providers can prepare outgoing write
  payloads consistently across normal write commands and copy workflows

## Examples

```bash
netloom shell
NETLOOM_CLIENT_SECRET_REF="secretserver://prod/Shared/ClearPass/API?field=password"
netloom policyelements network-device copy --from=<source-profile> --to=<target-profile> --all --dry-run
```

## Notes

- the Secret Server integration is read-only in this release
- no standalone `secretserver` runtime plugin is introduced; Secret Server is a
  shared keystore backend used by existing runtime plugins
