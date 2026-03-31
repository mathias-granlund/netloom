# Planned Features

## Current Priorities

### 1. ClearPass privilege coverage for the full retained catalog

Top priority.

Current measured coverage against the retained full ClearPass catalog:
- full retained services: `192`
- privilege-gated verified services: `125`
- baseline verified services: `10`
- unresolved services: `57`

Goal:
- continue turning retained full-catalog services into verified privilege
  rules
- keep using small live discovery rounds against the dedicated discovery
  operator profile
- explicitly separate real privilege gaps from endpoints that are not
  actually usable on the current ClearPass server
- treat `certificateauthority` as the only remaining higher-priority mapping
  area for now; the remaining unresolved services are lower value and may be
  hidden from the CLI later if they stay unmapped

Current unmapped retained services by module:

#### `certificateauthority` (`8`)
- `chain`
- `export`
- `import`
- `new`
- `reject`
- `request`
- `revoke`
- `sign`

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

Lower priority for now.

Interactive performance now feels good in normal use:
- help is roughly `40-45 ms`
- completion is roughly `26-33 ms`
- cache loading is down around `3-5 ms`

Current recommendation:
- stop active latency shaving unless a new real-world pain point appears
- keep the timing and progress instrumentation in place
- revisit remaining import-time trimming only if users actually feel a need

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
- only revisit a daemon approach if help/completion become slow again in
  practice
