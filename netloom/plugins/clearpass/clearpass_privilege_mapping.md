## Privilege-Gated Verified ClearPass Mappings

These mappings were verified live against a dedicated discovery operator profile.
The profile kept a minimal API baseline, then one extra privilege key was added
at a time and the resulting endpoint probes were checked.

## Discovery Workflow

The reusable discovery runner now lives with the ClearPass plugin and can be
executed as a normal Python module:

```bash
python -m netloom.plugins.clearpass.privilege_discovery --out=clearpass_privilege_discovery.json
```

Useful flags for future mapping rounds:

- `--modules=identities,policyelements`
- `--services=identities/api-client,policyelements/proxy-target`
- `--limit=10`
- `--include-mapped`
- `--candidate-file=clearpass_privilege_candidates.json`
- `--admin-profile=admin --discovery-profile=discovery`

| Operator profile privilege key | Effective runtime privilege | Module | Service | Verified access |
| --- | --- | --- | --- | --- |
| `#mdps_view_certificate` | `mdps_view_certificate` | `certificateauthority` | `certificate` | `list` |
| `#mdps_view_certificate` + `#mdps_export_ca_key` | `mdps_view_certificate` + `mdps_export_ca_key` | `certificateauthority` | `certificate-export` | `add` via direct `POST /api/certificate/1/export` returning `200` with `application/x-pkcs12` |
| `mdps_create_csr` | `mdps_create_csr` | `certificateauthority` | `certificate-new` | `add` via direct `POST /api/certificate/new` returning `200` and creating pending certificate request `id=220` |
| `mdps_device_manage` | `mdps_device_manage` | `certificateauthority` | `onboard-device` | `list` |
| `mdps_device_manage` | `mdps_device_manage` | `certificateauthority` | `onboard-user` | `list` |
| `cppm_enforcement_profile` | `cppm_enforcement_profile` | `enforcementprofile` | `enforcement-profile` | `list` |
| `cppm_captive_portal_profile` | `cppm_captive_portal_profile` | `enforcementprofile` | `captive-portal-profile` | `get` |
| `cppm_captive_portal_profile` | `cppm_captive_portal_profile` | `enforcementprofile` | `captive-portal-profile-name` | `get` via fake name returning `404` instead of baseline `403` |
| `cppm_dur_class` | `cppm_dur_class` | `enforcementprofile` | `dur-class` | `get` |
| `cppm_dur_class` | `cppm_dur_class` | `enforcementprofile` | `dur-class-name` | `get` via fake name returning `404` instead of baseline `403` |
| `cppm_ethertype_access_control_list` | `cppm_ethertype_access_control_list` | `enforcementprofile` | `ethertype-access-control-list` | `get` |
| `cppm_ethertype_access_control_list` | `cppm_ethertype_access_control_list` | `enforcementprofile` | `ethertype-access-control-list-name` | `get` via fake name returning `404` instead of baseline `403` |
| `cppm_mac_access_control_list` | `cppm_mac_access_control_list` | `enforcementprofile` | `mac-access-control-list` | `get` |
| `cppm_mac_access_control_list` | `cppm_mac_access_control_list` | `enforcementprofile` | `mac-access-control-list-name` | `get` via fake name returning `404` instead of baseline `403` |
| `cppm_nat_pool` | `cppm_nat_pool` | `enforcementprofile` | `nat-pool` | `get` |
| `cppm_nat_pool` | `cppm_nat_pool` | `enforcementprofile` | `nat-pool-name` | `get` via fake name returning `404` instead of baseline `403` |
| `cppm_net_destination` | `cppm_net_destination` | `enforcementprofile` | `net-destination` | `get` |
| `cppm_net_destination` | `cppm_net_destination` | `enforcementprofile` | `net-destination-name` | `get` via fake name returning `404` instead of baseline `403` |
| `cppm_net_service` | `cppm_net_service` | `enforcementprofile` | `net-service` | `get` |
| `cppm_net_service` | `cppm_net_service` | `enforcementprofile` | `net-service-name` | `get` via fake name returning `404` instead of baseline `403` |
| `cppm_policer_profile` | `cppm_policer_profile` | `enforcementprofile` | `policer-profile` | `get` |
| `cppm_policer_profile` | `cppm_policer_profile` | `enforcementprofile` | `policer-profile-name` | `get` via fake name returning `404` instead of baseline `403` |
| `cppm_policy` | `cppm_policy` | `enforcementprofile` | `policy` | `get` |
| `cppm_policy` | `cppm_policy` | `enforcementprofile` | `policy-name` | `get` via real `test_policy` |
| `cppm_qos_profile` | `cppm_qos_profile` | `enforcementprofile` | `qos-profile` | `get` |
| `cppm_qos_profile` | `cppm_qos_profile` | `enforcementprofile` | `qos-profile-name` | `get` via fake name returning `404` instead of baseline `403` |
| `cppm_session_access_control_list` | `cppm_session_access_control_list` | `enforcementprofile` | `session-access-control-list` | `get` |
| `cppm_session_access_control_list` | `cppm_session_access_control_list` | `enforcementprofile` | `session-access-control-list-name` | `get` via fake name returning `404` instead of baseline `403` |
| `cppm_stateless_access_control_list` | `cppm_stateless_access_control_list` | `enforcementprofile` | `stateless-access-control-list` | `get` |
| `cppm_stateless_access_control_list` | `cppm_stateless_access_control_list` | `enforcementprofile` | `stateless-access-control-list-name` | `get` via fake name returning `404` instead of baseline `403` |
| `cppm_time_range` | `cppm_time_range` | `enforcementprofile` | `time-range` | `get` |
| `cppm_time_range` | `cppm_time_range` | `enforcementprofile` | `time-range-name` | `get` via fake name returning `404` instead of baseline `403` |
| `cppm_voip_profile` | `cppm_voip_profile` | `enforcementprofile` | `voip-profile` | `get` |
| `cppm_voip_profile` | `cppm_voip_profile` | `enforcementprofile` | `voip-profile-name` | `get` via fake name returning `404` instead of baseline `403` |
| `cppm_fingerprints` | `cppm_fingerprints` | `endpointvisibility` | `fingerprint` | `list` |
| `cppm_onguard_global_settings` | `cppm_onguard_global_settings` | `endpointvisibility` | `global-settings` | `list` |
| `cppm_networkscan` | `cppm_networkscan` | `endpointvisibility` | `network-scan` | `list` |
| `cppm_policy_manager_zones` | `cppm_policy_manager_zones` | `endpointvisibility` | `policy-manager-zones` | `list` |
| `cppm_profiler_subnet_mapping` | `cppm_profiler_subnet_mapping` | `endpointvisibility` | `profiler-subnet-mapping` | `list` |
| `cppm_profiler_subnet_mapping` | `cppm_profiler_subnet_mapping` | `endpointvisibility` | `profiler-subnet-mapping-network` | `get` via fake network returning `404` instead of baseline `403` |
| `cppm_onguard_settings` | `cppm_onguard_settings` | `endpointvisibility` | `settings` | `list` |
| `cppm_agentless_onguard_subnet_mapping` | `cppm_agentless_onguard_subnet_mapping` | `endpointvisibility` | `subnet-mapping` | `list` |
| `cppm_windows_hotfix` | `cppm_windows_hotfix` | `endpointvisibility` | `windows-hotfix` | `list` |
| `cppm_admin_privileges` | `cppm_admin_privileges` | `globalserverconfiguration` | `admin-privilege` | `list` |
| `cppm_admin_users` | `cppm_admin_users` | `globalserverconfiguration` | `admin-user` | `list` |
| `cppm_licenses` | `cppm_licenses` | `globalserverconfiguration` | `application-license` | `list` |
| `cppm_licenses` | `cppm_licenses` | `globalserverconfiguration` | `application-license-summary` | `get` |
| `cppm_attributes` | `cppm_attributes` | `globalserverconfiguration` | `attribute` | `list` |
| `cppm_attributes` | `cppm_attributes` | `globalserverconfiguration` | `attribute-name` | `get` via real `entity_name=LocalUser`, `name=Title` |
| `cppm_clearpass_portal` | `cppm_clearpass_portal` | `globalserverconfiguration` | `clearpass-portal` | `list` |
| `cppm_data_filters` | `cppm_data_filters` | `globalserverconfiguration` | `data-filter` | `list` |
| `cppm_file_backup_server` | `cppm_file_backup_server` | `globalserverconfiguration` | `file-backup-server` | `list` |
| `auth_profiles` | `auth_profiles` | `globalserverconfiguration` | `operator-profile` | `list` |
| `cppm_config` | `cppm_config` | `globalserverconfiguration` | `parameters` | `get` |
| `cppm_admin_user_pass_policy` | `cppm_admin_user_pass_policy` | `globalserverconfiguration` | `password-policy` | `get` |
| `cppm_admin_user_pass_policy` | `cppm_admin_user_pass_policy` | `globalserverconfiguration` | `messaging-setup` | `get`; empty-body `POST` returns `400` instead of baseline `403` |
| `cppm_server_policy_manager_zones` | `cppm_server_policy_manager_zones` | `globalserverconfiguration` | `policy-manager-zones` | `list` |
| `cppm_snmp_trap_receivers` | `cppm_snmp_trap_receivers` | `globalserverconfiguration` | `snmp-trap-receiver` | `list` |
| `platform_authentication` | `platform_authentication` | `guestconfiguration` | `authentication` | `list` |
| `guestmanager` | `guestmanager` | `guestconfiguration` | `guestmanager` | `list` |
| `guest_print_list` | `guest_print_list` | `guestconfiguration` | `print` | `list` |
| `api_clients` | `api_clients` | `identities` | `api-client` | `list` |
| `cppm_deny_listed_users` | `cppm_deny_listed_users` | `identities` | `deny-listed-users-user_id-mac_address` | `get` via fake ID/MAC returning `404` instead of baseline `403` |
| `mac` + `guest_users` | `mac` + `guest_users` | `identities` | `device` | `list` |
| `cppm_deny_listed_users` | `cppm_deny_listed_users` | `identities` | `deny-listed-users` | `list` |
| `cppm_endpoints` | `cppm_endpoints` | `identities` | `endpoint` | `list` |
| `cppm_external_account` | `cppm_external_account` | `identities` | `external-account` | `list` |
| `guest_users` | `guest_users` | `identities` | `guest` | `list` |
| `cppm_local_users` | `cppm_local_users` | `identities` | `local-user` | `list` |
| `cppm_static_host_list` | `cppm_static_host_list` | `identities` | `static-host-list` | `list` |
| `insight_alert` | `insight_alert` | `insight` | `alert` | `list` |
| `insight_alert` | `insight_alert` | `insight` | `alert-disable` | `update` via real `test_alert` |
| `insight_alert` | `insight_alert` | `insight` | `alert-enable` | `update` via real `test_alert` |
| `insight_alert` | `insight_alert` | `insight` | `alert-mute` | `update` via real `test_alert` |
| `insight_alert` | `insight_alert` | `insight` | `alert-unmute` | `update` via real `test_alert` |
| `insight_report` | `insight_report` | `insight` | `report` | `list` |
| `insight_report` | `insight_report` | `insight` | `report-disable` | `update` via fake report name returning `404` instead of baseline `403` |
| `insight_report` | `insight_report` | `insight` | `report-enable` | `update` via real `test_report` |
| `insight_report` | `insight_report` | `insight` | `report-run` | `add` via real `test_report` |
| `cppm_context_server_actions` | `cppm_context_server_actions` | `integrations` | `context-server-action` | `list` |
| `cppm_device_insight` | `cppm_device_insight` | `integrations` | `device-insight` | `list` |
| `cppm_endpoint_context_server` | `cppm_endpoint_context_server` | `integrations` | `endpoint-context-server` | `list` |
| `cppm_event_sources` | `cppm_event_sources` | `integrations` | `event-sources` | `list` |
| `cppm_ingress_event_dict` | `cppm_ingress_event_dict` | `integrations` | `ingress-event-dictionary` | `list` |
| `extension_instance` | `extension_instance` | `integrations` | `instance` | `list` |
| `extension_store` | `extension_store` | `integrations` | `store` | `list` |
| `cppm_syslog_export_filter` | `cppm_syslog_export_filter` | `integrations` | `syslog-export-filter` | `list` |
| `cppm_syslog_target` | `cppm_syslog_target` | `integrations` | `syslog-target` | `list` |
| `platform` | `platform` | `localserverconfiguration` | `server` | `list` |
| `cppm_login_audit` | `cppm_login_audit` | `logs` | `login-audit` | `get` |
| `cppm_system_events` | `cppm_system_events` | `logs` | `system-event` | `list` |
| `cppm_certificates` | `cppm_certificates` | `platformcertificates` | `cert-sign-request` | `add` |
| `cppm_cert_trust_list` | `cppm_cert_trust_list` | `platformcertificates` | `cert-trust-list` | `list` |
| `cppm_cert_trust_list` | `cppm_cert_trust_list` | `platformcertificates` | `cert-trust-list-details` | `list` |
| `cppm_certificates` | `cppm_certificates` | `platformcertificates` | `client-cert` | `list` |
| `cppm_revocation_lists` | `cppm_revocation_lists` | `platformcertificates` | `revocation-list` | `list` |
| `cppm_certificates` | `cppm_certificates` | `platformcertificates` | `self-signed-cert` | `add` via direct POST with verified minimal payload |
| `cppm_certificates` | `cppm_certificates` | `platformcertificates` | `server-cert` | `get` |
| `cppm_certificates` | `cppm_certificates` | `platformcertificates` | `server-cert-name` | `get` |
| `cppm_certificates` | `cppm_certificates` | `platformcertificates` | `server-cert-name-disable` | `update` |
| `cppm_certificates` | `cppm_certificates` | `platformcertificates` | `server-cert-name-enable` | `update` |
| `cppm_certificates` | `cppm_certificates` | `platformcertificates` | `service-cert` | `list` |
| `#guest_sessions_history` | `guest_sessions_history` | `sessioncontrol` | `session` | `list` |
| `smtp_send` | `smtp_send` | `toolsandutilities` | `send` | `add` |
| `cppm_application_dict` | `cppm_application_dict` | `policyelements` | `application-dictionary` | `list` |
| `auth_config` + `cppm_config` | `auth_config` + `cppm_config` | `policyelements` | `auth-source` | `list` |
| `cppm_auth_methods` | `cppm_auth_methods` | `policyelements` | `auth-method` | `list` |
| `cppm_enforcement_policy` | `cppm_enforcement_policy` | `policyelements` | `enforcement-policy` | `list` |
| `cppm_network_devices` | `cppm_network_devices` | `policyelements` | `network-device` | `list` |
| `cppm_network_device_groups` | `cppm_network_device_groups` | `policyelements` | `network-device-group` | `list` |
| `cppm_network_proxy_targets` | `cppm_network_proxy_targets` | `policyelements` | `proxy-target` | `list` |
| `cppm_radius_dict` | `cppm_radius_dict` | `policyelements` | `radius-dictionary` | `list` |
| `cppm_radius_dict` | `cppm_radius_dict` | `policyelements` | `radius-dictionary-disable` | `update` |
| `cppm_radius_dict` | `cppm_radius_dict` | `policyelements` | `radius-dictionary-enable` | `update` |
| `cppm_radius_dict` | `cppm_radius_dict` | `policyelements` | `radius-dictionary-name-disable` | `update` |
| `cppm_radius_dict` | `cppm_radius_dict` | `policyelements` | `radius-dictionary-name-enable` | `update` |
| `cppm_radius_dyn_autz_template` | `cppm_radius_dyn_autz_template` | `policyelements` | `radius-dynamic-authorization-template` | `list` |
| `cppm_posture_policy` | `cppm_posture_policy` | `policyelements` | `posture-policy` | `list` |
| `cppm_role_mapping` | `cppm_role_mapping` | `policyelements` | `role-mapping` | `list` |
| `cppm_roles` | `cppm_roles` | `policyelements` | `role` | `list` |
| `cppm_services` | `cppm_services` | `policyelements` | `service` | `list` |
| `cppm_services` | `cppm_services` | `policyelements` | `service-disable` | `update` |
| `cppm_services` | `cppm_services` | `policyelements` | `service-enable` | `update` |
| `cppm_services` | `cppm_services` | `policyelements` | `service-name-disable` | `update` |
| `cppm_services` | `cppm_services` | `policyelements` | `service-name-enable` | `update` |
| `cppm_services` | `cppm_services` | `policyelements` | `service-reorder` | `update` |
| `cppm_tacacs_service_dict` | `cppm_tacacs_service_dict` | `policyelements` | `tacacs-service-dictionary` | `list` |

## Baseline Verified Services

These services were verified as accessible with the stripped minimum API
baseline, so they stay visible in the CLI but are not counted as extra
privilege mappings.

| Module | Service | Verified baseline access |
| --- | --- | --- |
| `apioperations` | `me` | `list`, `add` |
| `apioperations` | `oauth` | `add` |
| `apioperations` | `privileges` | `get` |
| `certificateauthority` | `certificate-chain` | `get` via direct `GET /api/certificate/1/chain`; restricted discovery token still showed only baseline runtime privileges `?api_index`, `api_docs`, and `apigility` |
| `globalserverconfiguration` | `all-privileges` | `get` |
| `globalserverconfiguration` | `db-sync` | `add` via direct `POST` with `{"timeout":"10"}` returning JSON fields `error`, `is_publisher`, `sync_time`, `timeout`, `timeout_error`, and `message` |
| `localserverconfiguration` | `cppm-version` | `get` |
| `localserverconfiguration` | `fips` | `get` |
| `localserverconfiguration` | `version` | `get` |
| `toolsandutilities` | `random-mpsk` | `list` |
| `toolsandutilities` | `random-password` | `list` |

## Accepted But Not Yet Verified

These privilege keys were accepted by the operator-profile API and appeared in
the effective runtime privilege list, but the live endpoint probes still did
not produce a promotable success in this round, so they are not enforced in
the cache filter yet.

| Operator profile privilege key | Module | Service | Current status |
| --- | --- | --- | --- |
| `pass_template` | `guestconfiguration` | `pass` | accepted, but both the `list` probe and the reversible `add` probe still returned baseline `403` |
| `pass_config` | `guestconfiguration` | `pass` | accepted, but both the `list` probe and the reversible `add` probe still returned baseline `403` |
| `pass_index` | `guestconfiguration` | `pass` | accepted; enabling it also exposed `pass_config`, `pass_template`, `pass_cert_install`, and `pass_cert_view`, but both the `list` probe and the reversible `add` probe still returned baseline `403` |
| `mdps_create_csr` | `certificateauthority` | `certificate-request` | accepted and exposed runtime key `mdps_create_csr`; an intentionally invalid CSR upload moved from baseline `403` to `422 Invalid PKCS#10 Certificate Request`, so this is the strongest current candidate but not yet promotable |
| `mdps_revoke_certificate` | `certificateauthority` | `certificate-revoke` | accepted and exposed runtime key `mdps_revoke_certificate`; a non-destructive confirm-false probe moved from baseline `403` to `400`, so this is the strongest current candidate but not yet promotable |
| `insight_reports` | `insight` | `report-enable` | accepted on the operator profile and exposed runtime key `insight_reports`, but the real `test_report` enable probe still returned baseline `403` |
| `insight_reports` | `insight` | `report-run` | accepted on the operator profile and exposed runtime key `insight_reports`, but the real `test_report` run probe still returned baseline `403` |

## Discovered Onboard Runtime Keys

These Onboard operator-profile privileges were confirmed live and their
effective runtime keys were captured, but they have not yet been promoted into
service-level cache rules because the remaining `certificateauthority` services
do not currently expose safe non-parameterized `list` or `get` probes for the
discovery runner.

| UI privilege | Effective runtime privilege | Current note |
| --- | --- | --- |
| `Manage Certificate Authorities` | `mdps_ca` | internal key confirmed; no promotable service mapping yet |
| `Create New CSR` | `mdps_create_csr` | internal key confirmed; no promotable service mapping yet |
| `Issue Certificate` | `mdps_issue_certificate` | internal key confirmed; no promotable service mapping yet |
| `Revoke Certificate` | `mdps_revoke_certificate` | internal key confirmed; no promotable service mapping yet |

## Combo Rules

Some services need more than one effective runtime privilege at the same time.
Those are enforced in the cache as `all-of` rules instead of normal single-key
matches.

| Module | Service | Required effective privileges |
| --- | --- | --- |
| `certificateauthority` | `certificate-export` | `mdps_view_certificate` and `mdps_export_ca_key` |
| `identities` | `device` | `mac` and `guest_users` |
| `policyelements` | `auth-source` | `auth_config` and `cppm_config` |

## Attribute Endpoint Notes

For `globalserverconfiguration/attribute` and `globalserverconfiguration/attribute-name`:

- The `entity_name` values currently confirmed from live server data are `LocalUser`, `GuestUser`, `Endpoint`, and `Device`.
- The `name` field returned by `GET /api/attribute` represents the default available attributes for each `entity_name`.
- ClearPass also allows custom attributes, so `attribute-name` is not limited to only the built-in defaults.
- The live verification for `attribute-name` used a real default attribute: `entity_name=LocalUser`, `name=Title`.

## Current Unresolved Live-Probe Results

These services were revisited in focused live discovery rounds and still are
not promotable into enforced cache mappings. The broader remaining unmapped
backlog still lives in `PLANNED_FEATURES.md`.

| Module | Service | Current blocker |
| --- | --- | --- |
| `certificateauthority` | `certificate-import` | focused probes with `mdps_csc_import`, `cppm_certificates`, `cppm_cert_trust_list`, `mdps_ca`, and tested combinations still returned baseline `403` for the invalid trusted-certificate import payload |
| `certificateauthority` | `certificate-reject` | even against a real pending CSR (`certificate/216`), tested `mdps_issue_certificate`, `mdps_ca`, `mdps_revoke_certificate`, `mdps_create_csr`, and combinations still returned baseline `403` |
| `certificateauthority` | `certificate-request` | `mdps_create_csr` now looks like the strongest candidate because the invalid CSR upload moved from baseline `403` to `422`, but the endpoint still lacks a safe promotable success probe |
| `certificateauthority` | `certificate-revoke` | `mdps_revoke_certificate` now looks like the strongest candidate because the confirm-false probe moved from baseline `403` to `400`, but the endpoint still lacks a safe promotable success probe |
| `certificateauthority` | `certificate-sign-request` | even against a real pending CSR (`certificate/216`), tested `mdps_issue_certificate`, `mdps_ca`, `mdps_create_csr`, and combinations still returned baseline `403` |
| `guestconfiguration` | `pass` | candidate probes with `pass_template`, `pass_config`, `pass_index`, and their tested combinations still return `403` for both `list` and reversible `add` probes |

`certificateauthority/certificate` was promoted after enabling the read-only
Onboard `View Certificate` privilege on the dedicated discovery profile. Its
effective runtime privilege is `mdps_view_certificate`.

`certificateauthority/certificate-export` was promoted after enabling the
read-only `View Certificate` and `Export CA Key` privileges on the dedicated
discovery profile. The successful live export probe produced effective runtime
privileges `mdps_view_certificate` and `mdps_export_ca_key`.

`certificateauthority/certificate-new` was promoted after a direct live
`POST /api/certificate/new` probe succeeded with a token whose runtime
privileges were limited to the baseline plus `mdps_create_csr`.

`certificateauthority/onboard-device` and `certificateauthority/onboard-user`
were promoted after enabling the Onboard `Manage Devices` privilege on the
dedicated discovery profile. Its effective runtime privilege is
`mdps_device_manage`.

## Baseline Effective Privileges

The discovery API client baseline produced these runtime privileges:

| Raw runtime privilege | Normalized name | Access |
| --- | --- | --- |
| `?api_index` | `api_index` | `allowed` |
| `api_docs` | `api_docs` | `full` |
| `apigility` | `apigility` | `full` |

## Notes

- `#` means read-only access.
- `?` means allowed access.
- No prefix means full access.
- The ClearPass documentation catalog remained broadly visible even for the
  restricted discovery profile, so endpoint probing was required to verify the
  real service mapping.

## Follow-up Note

The next logical step for `v1.8.2` is to use the filtered cache more strictly
in the normal user experience, so `netloom cache update` and the resulting
module/service/action visibility line up with what the active API client can
actually access.

A useful fallback may still be worth keeping available for troubleshooting:
allowing an explicit opt-in to build or inspect the full unfiltered catalog when
someone needs to compare discovery output, investigate vendor doc changes, or
debug an incomplete mapping.
