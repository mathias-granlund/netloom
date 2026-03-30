# Planned Features

## Current Priorities

### 1. ClearPass privilege coverage for the full retained catalog

Top priority.

Current measured coverage against the retained full ClearPass catalog:
- full retained services: `192`
- privilege-gated verified services: `87`
- baseline verified services: `5`
- unresolved services: `100`

Current measured coverage against the visible cache:
- the currently checked-in cache predates the new baseline/gated split
- after the next `netloom cache update`, both privilege-gated verified and
  baseline verified services should appear in the default visible cache
- until then, the visible-cache counts on disk may lag behind the current
  rule table

Important status notes:
- `apioperations/me`, `apioperations/oauth`, and `apioperations/privileges`
  are now tracked as baseline verified services
- `globalserverconfiguration/operator-profile` is now verified with
  `auth_profiles`
- `policyelements/radius-dictionary` is now verified with `cppm_radius_dict`
- `policyelements/radius-dictionary-*` action aliases are now also verified
  with `cppm_radius_dict`
- `policyelements/service-*` action aliases are now also verified with
  `cppm_services`
- several `endpointvisibility/*` services are now verified, including
  `fingerprint`, `policy-manager-zones`, `profiler-subnet-mapping`, and
  `profiler-subnet-mapping-network`
- multiple `integrations/*` services are now verified, including
  `context-server-action`, `device-insight`, `endpoint-context-server`,
  `event-sources`, `instance`, `store`, `syslog-export-filter`, and
  `syslog-target`
- `insight/alert` and `insight/report` are now verified after Insight was
  enabled on the ClearPass server
- `insight/alert-disable`, `insight/alert-enable`, `insight/alert-mute`,
  and `insight/alert-unmute` are now verified with `insight_alert`
- `insight/report-disable` is now verified with `insight_report`
- `insight/report-enable` and `insight/report-run` are now verified with
  `insight_report` against a real `test_report`
- several `platformcertificates/*` services are now verified, including
  `cert-sign-request`, `cert-trust-list`, `cert-trust-list-details`,
  `client-cert`, `revocation-list`, `self-signed-cert`, `server-cert`,
  `server-cert-name`, `server-cert-name-disable`,
  `server-cert-name-enable`, and `service-cert`
- `toolsandutilities/send` is now verified with `smtp_send`
- `toolsandutilities/random-mpsk` and `toolsandutilities/random-password`
  are now tracked as baseline verified services
- `certificateauthority/certificate` is now verified with
  `mdps_view_certificate`
- `certificateauthority/device` and `certificateauthority/user` are now
  verified with `mdps_device_manage`
- `identities/deny-listed-users-user_id-mac_address` is now verified with
  `cppm_deny_listed_users`
- additional Onboard internal keys are now documented for future
  `certificateauthority` work:
  `mdps_ca`, `mdps_create_csr`, `mdps_issue_certificate`,
  and `mdps_revoke_certificate`
- `integrations/ingress-event-dictionary` is now verified with
  `cppm_ingress_event_dict`
- `logs/login-audit` is now verified with `cppm_login_audit`
- `globalserverconfiguration/messaging-setup` is still not promoted, but it
  still returned `403` in the latest focused probes even with
  `cppm_messaging_setup`, `smtp_config`, `smtp_send`, and `sms_setup`,
  including a reversible write probe with a cleaned minimal payload
- `guestconfiguration/pass` is still not promoted; `pass_template`,
  `pass_config`, `pass_index`, and their tested combinations were all
  accepted into the operator profile, but both `list` and reversible `add`
  probes still returned `403`
- `insight_reports` alone still was not enough for the real `test_report`
  `report-enable` and `report-run` API probes; the minimal verified mapping
  for those endpoints remains `insight_report`

Goal:
- continue turning retained full-catalog services into verified privilege
  rules
- keep using small live discovery rounds against the dedicated discovery
  operator profile
- explicitly separate real privilege gaps from endpoints that are not
  actually usable on the current ClearPass server

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

#### `endpointvisibility` (`17`)
- `device-fingerprint`
- `fingerprint-name`
- `global-settings`
- `network-scan-disable`
- `network-scan-enable`
- `onguard-activity`
- `onguard-activity-message`
- `onguard-activity-notification`
- `onguard-custom-script`
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

#### `logs` (`2`)
- `endpoint`
- `endpoint-time-range`

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
- `apioperations/me -> baseline verified`
- `apioperations/oauth -> baseline verified`
- `apioperations/privileges -> baseline verified`
- `certificateauthority/device -> mdps_device_manage`
- `certificateauthority/user -> mdps_device_manage`
- `certificateauthority/certificate -> mdps_view_certificate`
- `endpointvisibility/fingerprint -> cppm_fingerprints`
- `endpointvisibility/network-scan -> cppm_networkscan`
- `endpointvisibility/policy-manager-zones -> cppm_policy_manager_zones`
- `endpointvisibility/profiler-subnet-mapping -> cppm_profiler_subnet_mapping`
- `endpointvisibility/profiler-subnet-mapping-network -> cppm_profiler_subnet_mapping`
- `globalserverconfiguration/operator-profile -> auth_profiles`
- `platformcertificates/server-cert-name -> cppm_certificates`
- `platformcertificates/server-cert-name-disable -> cppm_certificates`
- `platformcertificates/server-cert-name-enable -> cppm_certificates`
- `toolsandutilities/send -> smtp_send`
- `identities/deny-listed-users-user_id-mac_address -> cppm_deny_listed_users`
- `logs/login-audit -> cppm_login_audit`
- `toolsandutilities/random-mpsk -> baseline verified`
- `toolsandutilities/random-password -> baseline verified`
- `policyelements/radius-dictionary -> cppm_radius_dict`
- `policyelements/radius-dictionary-disable -> cppm_radius_dict`
- `policyelements/radius-dictionary-enable -> cppm_radius_dict`
- `policyelements/radius-dictionary-name-disable -> cppm_radius_dict`
- `policyelements/radius-dictionary-name-enable -> cppm_radius_dict`
- `policyelements/service-disable -> cppm_services`
- `policyelements/service-enable -> cppm_services`
- `policyelements/service-name-disable -> cppm_services`
- `policyelements/service-name-enable -> cppm_services`
- `policyelements/service-reorder -> cppm_services`

Current explicitly unresolved service:
- `globalserverconfiguration/messaging-setup`
  - latest focused candidate probes still returned `403`

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
