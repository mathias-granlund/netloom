# Planned Features

## Current Priorities

### 1. ClearPass privilege coverage for the full retained catalog

Lower priority for now.

Current measured coverage against the retained full ClearPass catalog:
- full retained services: `192`
- privilege-gated verified services: `127`
- baseline verified services: `11`
- unresolved services: `54`

Current stance:
- the current verified mapping coverage is good enough for now
- stop treating `certificateauthority` as a special high-priority mapping
  area
- keep the remaining unresolved services as opportunistic cleanup and only
  revisit them when they block real workflows or when we decide to hide them
  from the default CLI surface
- prefer spending effort on real user-facing CLI behavior over more mapping
  rounds unless a clear gap shows up in practice

Current unmapped retained services by module:

#### `certificateauthority` (`5`)
- `certificate-import`
- `certificate-reject`
- `certificate-request`
- `certificate-revoke`
- `certificate-sign-request`

#### `endpointvisibility` (`13`)
- `device-fingerprint`
- `fingerprint-name`
- `network-scan-disable`
- `network-scan-enable`
- `onguard-activity`
- `onguard-activity-message`
- `onguard-activity-notification`
- `onguard-custom-script`
- `subnet-mapping-disable`
- `subnet-mapping-enable`
- `subnet-mapping-name-disable`
- `subnet-mapping-name-enable`
- `windows-hotfix-kbid-operating_system`

#### `guestactions` (`4`)
- `sms`
- `smtp`
- `sponsor`
- `{id}`

#### `guestconfiguration` (`2`)
- `pass`
- `weblogin`

#### `integrations` (`10`)
- `config`
- `context-server-action-action-name`
- `endpoint-context-server-server-name-trigger-poll`
- `endpoint-context-server-trigger-poll`
- `log`
- `reinstall`
- `restart`
- `start`
- `stop`
- `upgrade`

#### `localserverconfiguration` (`6`)
- `ad-domain`
- `ad-domain-netbios-name`
- `{server_uuid}`
- `{server_uuid}-start`
- `{server_uuid}-stop`
- `{service_id}`

#### `logs` (`2`)
- `endpoint`
- `endpoint-time-range`

#### `sessioncontrol` (`12`)
- `active-session`
- `disconnect`
- `reauthorize`
- `session-action`
- `session-action-coa`
- `session-action-coa-ip`
- `session-action-coa-mac`
- `session-action-coa-username`
- `session-action-disconnect`
- `session-action-disconnect-ip`
- `session-action-disconnect-mac`
- `session-action-disconnect-username`

### 2. Cache/help/completion performance follow-up

Focused check completed on `2026-04-10`.

Focused local measurements against the current cached catalog:
- module help (`netloom identities ?`) is roughly `153-181 ms` steady-state
  end-to-end, with a first-run outlier around `244 ms`
- top-level completion (`netloom --_complete --_cur=`) is roughly `114-142 ms`
  steady-state end-to-end, with a first-run outlier around `154 ms`
- representative internal CLI timing showed help around `100 ms` total with
  `load_core_cached_catalog` around `65 ms`
- representative internal CLI timing showed completion around `59 ms` total
  with `load_core_cached_catalog` around `48 ms`
- a focused loader-only microbenchmark with explicit settings landed around
  `15 ms` median for the visible fast index and around `11 ms` median for the
  visible full-cache path, which suggests the remaining end-to-end cost is
  mostly process/import overhead plus cached catalog loading rather than help
  rendering itself

Current recommendation:
- do not continue with a `netloomd` implementation right now
- keep the timing and progress instrumentation in place
- only revisit deeper optimization if users actually feel the current latency
  in real shell use
- if we optimize further before a daemon, focus on startup/import overhead and
  cached catalog/index deserialization cost

## Completed Work

### Phase 1: Cache performance and UX

Done:
- compact full cache JSON
- derived fast index
- completion prefers the fast index
- compact help prefers the fast index
- full-cache fallback behavior preserved
- lightweight core-owned cache loader for help/completion
- split timing for help and completion
- cache-update timing
- cache-update progress reporting

Measured outcomes:
- cached interactive help improved from roughly `155-195 ms` in the old hot
  path to roughly `40-45 ms`
- cached completion is roughly `26-33 ms`
- cache-update timing showed the rebuild is network-bound, especially
  subdocument fetches

### Phase 2: `netloomd`

Not recommended right now:
- a focused local check on `2026-04-10` still puts normal cached help and
  completion in the "noticeable but acceptable" range rather than in a range
  that clearly justifies daemon complexity
- only revisit a daemon approach if help/completion become materially slower
  in practice, the cache grows substantially, or repeated shell completion
  starts to feel like a real workflow drag
