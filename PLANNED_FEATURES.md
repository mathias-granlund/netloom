# Planned Features

## Current Priorities

### 1. ClearPass privilege coverage for the full retained catalog

Top priority.

Current measured coverage against the retained full ClearPass catalog:
- full retained services: `192`
- services with verified privilege mappings: `58`
- services without verified mappings: `134`

Current measured coverage against the visible cache:
- visible services in the current cache: `47`
- visible services with explicit verified mappings: `46`
- visible services without an explicit mapping: `1`
- the only currently visible unmapped service is `apioperations/oauth`

Important status notes:
- `globalserverconfiguration/operator-profile` is now verified with
  `auth_profiles`
- `policyelements/radius-dictionary` is now verified with `cppm_radius_dict`
- multiple `integrations/*` services are now verified, including
  `context-server-action`, `device-insight`, `endpoint-context-server`,
  `event-sources`, `instance`, `store`, `syslog-export-filter`, and
  `syslog-target`
- `insight/alert` and `insight/report` are now verified after Insight was
  enabled on the ClearPass server
- several `platformcertificates/*` services are now verified, including
  `cert-trust-list`, `cert-trust-list-details`, `client-cert`,
  `revocation-list`, `server-cert`, and `service-cert`
- `certificateauthority/certificate` is now verified with
  `mdps_view_certificate`
- `certificateauthority/device` and `certificateauthority/user` are now
  verified with `mdps_device_manage`
- additional Onboard internal keys are now documented for future
  `certificateauthority` work:
  `mdps_ca`, `mdps_create_csr`, `mdps_issue_certificate`,
  and `mdps_revoke_certificate`
- `integrations/ingress-event-dictionary` is now verified with
  `cppm_ingress_event_dict`
- `globalserverconfiguration/messaging-setup` is still not promoted, but it
  currently returns `404` even for admin on this server, so it looks like an
  endpoint availability issue rather than a missing privilege mapping

Goal:
- continue turning retained full-catalog services into verified privilege
  rules
- keep using small live discovery rounds against the dedicated discovery
  operator profile
- explicitly separate real privilege gaps from endpoints that are not
  actually usable on the current ClearPass server

Current unmapped retained services by module:

#### `apioperations` (`3`)
- `me`
- `oauth`
- `privileges`

#### `certificateauthority` (`8`)
- `chain`
- `export`
- `import`
- `new`
- `reject`
- `request`
- `revoke`
- `sign`

#### `endpointvisibility` (`22`)
- `device-fingerprint`
- `fingerprint`
- `fingerprint-name`
- `global-settings`
- `network-scan`
- `network-scan-disable`
- `network-scan-enable`
- `onguard-activity`
- `onguard-activity-message`
- `onguard-activity-notification`
- `onguard-custom-script`
- `policy-manager-zones`
- `profiler-subnet-mapping`
- `profiler-subnet-mapping-network`
- `settings`
- `subnet-mapping`
- `subnet-mapping-disable`
- `subnet-mapping-enable`
- `subnet-mapping-name-disable`
- `subnet-mapping-name-enable`
- `windows-hotfix`
- `windows-hotfix-kbid-operating_system`

#### `enforcementprofile` (`28`)
- `captive-portal-profile`
- `captive-portal-profile-name`
- `dur-class`
- `dur-class-name`
- `ethertype-access-control-list`
- `ethertype-access-control-list-name`
- `mac-access-control-list`
- `mac-access-control-list-name`
- `nat-pool`
- `nat-pool-name`
- `net-destination`
- `net-destination-name`
- `net-service`
- `net-service-name`
- `policer-profile`
- `policer-profile-name`
- `policy`
- `policy-name`
- `qos-profile`
- `qos-profile-name`
- `session-access-control-list`
- `session-access-control-list-name`
- `stateless-access-control-list`
- `stateless-access-control-list-name`
- `time-range`
- `time-range-name`
- `voip-profile`
- `voip-profile-name`

#### `globalserverconfiguration` (`4`)
- `all-privileges`
- `attribute-name`
- `db-sync`
- `messaging-setup`

#### `guestactions` (`4`)
- `sms`
- `smtp`
- `sponsor`
- `{id}`

#### `guestconfiguration` (`5`)
- `authentication`
- `guestmanager`
- `pass`
- `print`
- `weblogin`

#### `identities` (`1`)
- `deny-listed-users-user_id-mac_address`

#### `insight` (`7`)
- `alert-disable`
- `alert-enable`
- `alert-mute`
- `alert-unmute`
- `report-disable`
- `report-enable`
- `report-run`

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

#### `localserverconfiguration` (`9`)
- `ad-domain`
- `ad-domain-netbios-name`
- `cppm-version`
- `fips`
- `version`
- `{server_uuid}`
- `{server_uuid}-start`
- `{server_uuid}-stop`
- `{service_id}`

#### `logs` (`3`)
- `endpoint`
- `endpoint-time-range`
- `login-audit`

#### `platformcertificates` (`5`)
- `cert-sign-request`
- `self-signed-cert`
- `server-cert-name`
- `server-cert-name-disable`
- `server-cert-name-enable`

#### `policyelements` (`9`)
- `radius-dictionary-disable`
- `radius-dictionary-enable`
- `radius-dictionary-name-disable`
- `radius-dictionary-name-enable`
- `service-disable`
- `service-enable`
- `service-name-disable`
- `service-name-enable`
- `service-reorder`

#### `sessioncontrol` (`13`)
- `active-session`
- `disconnect`
- `reauthorize`
- `session`
- `session-action`
- `session-action-coa`
- `session-action-coa-ip`
- `session-action-coa-mac`
- `session-action-coa-username`
- `session-action-disconnect`
- `session-action-disconnect-ip`
- `session-action-disconnect-mac`
- `session-action-disconnect-username`

#### `toolsandutilities` (`3`)
- `random-mpsk`
- `random-password`
- `send`

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

### Cache performance and UX

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

### ClearPass privilege mapping

Recently verified mappings include:
- `certificateauthority/device -> mdps_device_manage`
- `certificateauthority/user -> mdps_device_manage`
- `certificateauthority/certificate -> mdps_view_certificate`
- `globalserverconfiguration/operator-profile -> auth_profiles`
- `policyelements/radius-dictionary -> cppm_radius_dict`

Current explicitly unresolved service:
- `globalserverconfiguration/messaging-setup`
  - still returns `404` even for admin on this server

## Deferred Ideas

### Phase 1.8: Validate shallow full-view projection

Still optional:
- evaluate whether `project_catalog_view(..., catalog_view=\"full\")` can reuse
  `full_modules` directly instead of deep-copying it
- only keep it if downstream consumers treat the catalog as read-only

### Phase 1.9: Parallelize catalog rebuild

Deferred:
- current rebuild timing shows a parallel fetch design would be the main
  technical speed path if we ever revisit rebuild performance
- for now, progress reporting solves the more immediate UX problem

### Phase 2: `netloomd`

Not recommended right now:
- only revisit a daemon approach if help/completion become slow again in
  practice
