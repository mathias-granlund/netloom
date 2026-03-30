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
| `mdps_device_manage` | `mdps_device_manage` | `certificateauthority` | `device` | `list` |
| `mdps_device_manage` | `mdps_device_manage` | `certificateauthority` | `user` | `list` |
| `cppm_enforcement_profile` | `cppm_enforcement_profile` | `enforcementprofile` | `enforcement-profile` | `list` |
| `cppm_fingerprints` | `cppm_fingerprints` | `endpointvisibility` | `fingerprint` | `list` |
| `cppm_networkscan` | `cppm_networkscan` | `endpointvisibility` | `network-scan` | `list` |
| `cppm_policy_manager_zones` | `cppm_policy_manager_zones` | `endpointvisibility` | `policy-manager-zones` | `list` |
| `cppm_profiler_subnet_mapping` | `cppm_profiler_subnet_mapping` | `endpointvisibility` | `profiler-subnet-mapping` | `list` |
| `cppm_profiler_subnet_mapping` | `cppm_profiler_subnet_mapping` | `endpointvisibility` | `profiler-subnet-mapping-network` | `get` via fake network returning `404` instead of baseline `403` |
| `cppm_admin_privileges` | `cppm_admin_privileges` | `globalserverconfiguration` | `admin-privilege` | `list` |
| `cppm_admin_users` | `cppm_admin_users` | `globalserverconfiguration` | `admin-user` | `list` |
| `cppm_licenses` | `cppm_licenses` | `globalserverconfiguration` | `application-license` | `list` |
| `cppm_licenses` | `cppm_licenses` | `globalserverconfiguration` | `application-license-summary` | `get` |
| `cppm_attributes` | `cppm_attributes` | `globalserverconfiguration` | `attribute` | `list` |
| `cppm_clearpass_portal` | `cppm_clearpass_portal` | `globalserverconfiguration` | `clearpass-portal` | `list` |
| `cppm_data_filters` | `cppm_data_filters` | `globalserverconfiguration` | `data-filter` | `list` |
| `cppm_file_backup_server` | `cppm_file_backup_server` | `globalserverconfiguration` | `file-backup-server` | `list` |
| `auth_profiles` | `auth_profiles` | `globalserverconfiguration` | `operator-profile` | `list` |
| `cppm_config` | `cppm_config` | `globalserverconfiguration` | `parameters` | `get` |
| `cppm_admin_user_pass_policy` | `cppm_admin_user_pass_policy` | `globalserverconfiguration` | `password-policy` | `get` |
| `cppm_server_policy_manager_zones` | `cppm_server_policy_manager_zones` | `globalserverconfiguration` | `policy-manager-zones` | `list` |
| `cppm_snmp_trap_receivers` | `cppm_snmp_trap_receivers` | `globalserverconfiguration` | `snmp-trap-receiver` | `list` |
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
| `toolsandutilities` | `random-mpsk` | `list` |
| `toolsandutilities` | `random-password` | `list` |

## Accepted But Not Yet Verified

These privilege keys were accepted by the operator-profile API and appeared in
the effective runtime privilege list, but the live endpoint probes still did
not produce a promotable success in this round, so they are not enforced in
the cache filter yet.

| Operator profile privilege key | Module | Service | Current status |
| --- | --- | --- | --- |
| `cppm_messaging_setup` | `globalserverconfiguration` | `messaging-setup` | accepted, but baseline and candidate probes still returned `403` |
| `smtp_config` | `globalserverconfiguration` | `messaging-setup` | accepted, but both the `list` probe and the reversible `add` probe still returned baseline `403` |
| `sms_setup` | `globalserverconfiguration` | `messaging-setup` | accepted, but both the `list` probe and the reversible `add` probe still returned baseline `403` |
| `pass_template` | `guestconfiguration` | `pass` | accepted, but both the `list` probe and the reversible `add` probe still returned baseline `403` |
| `pass_config` | `guestconfiguration` | `pass` | accepted, but both the `list` probe and the reversible `add` probe still returned baseline `403` |
| `pass_index` | `guestconfiguration` | `pass` | accepted; enabling it also exposed `pass_config`, `pass_template`, `pass_cert_install`, and `pass_cert_view`, but both the `list` probe and the reversible `add` probe still returned baseline `403` |
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
| `identities` | `device` | `mac` and `guest_users` |
| `policyelements` | `auth-source` | `auth_config` and `cppm_config` |

## Current Unresolved Live-Probe Results

These services were revisited in focused live discovery rounds and still are
not promotable into enforced cache mappings. The broader remaining unmapped
backlog still lives in `PLANNED_FEATURES.md`.

| Module | Service | Current blocker |
| --- | --- | --- |
| `globalserverconfiguration` | `messaging-setup` | candidate probes with `cppm_messaging_setup`, `smtp_config`, `smtp_send`, and `sms_setup` still return `403` for both `list` and reversible `add` probes |
| `guestconfiguration` | `pass` | candidate probes with `pass_template`, `pass_config`, `pass_index`, and their tested combinations still return `403` for both `list` and reversible `add` probes |

`certificateauthority/certificate` was promoted after enabling the read-only
Onboard `View Certificate` privilege on the dedicated discovery profile. Its
effective runtime privilege is `mdps_view_certificate`.

`certificateauthority/device` and `certificateauthority/user` were promoted
after enabling the Onboard `Manage Devices` privilege on the dedicated
discovery profile. Its effective runtime privilege is `mdps_device_manage`.

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
