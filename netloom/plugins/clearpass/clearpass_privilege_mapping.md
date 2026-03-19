## Verified ClearPass Privilege Mappings

These mappings were verified live against a dedicated discovery operator profile.
The profile kept the baseline API privileges `api_docs`, `apigility`, and
`cppm_endpoints`, then one extra privilege key was added at a time and the
resulting endpoint probes were checked.

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
| `cppm_enforcement_profile` | `cppm_enforcement_profile` | `enforcementprofile` | `enforcement-profile` | `list` |
| `cppm_admin_privileges` | `cppm_admin_privileges` | `globalserverconfiguration` | `admin-privilege` | `list` |
| `cppm_admin_users` | `cppm_admin_users` | `globalserverconfiguration` | `admin-user` | `list` |
| `cppm_licenses` | `cppm_licenses` | `globalserverconfiguration` | `application-license` | `list` |
| `cppm_attributes` | `cppm_attributes` | `globalserverconfiguration` | `attribute` | `list` |
| `cppm_clearpass_portal` | `cppm_clearpass_portal` | `globalserverconfiguration` | `clearpass-portal` | `list` |
| `cppm_data_filters` | `cppm_data_filters` | `globalserverconfiguration` | `data-filter` | `list` |
| `cppm_file_backup_server` | `cppm_file_backup_server` | `globalserverconfiguration` | `file-backup-server` | `list` |
| `cppm_server_policy_manager_zones` | `cppm_server_policy_manager_zones` | `globalserverconfiguration` | `policy-manager-zones` | `list` |
| `cppm_snmp_trap_receivers` | `cppm_snmp_trap_receivers` | `globalserverconfiguration` | `snmp-trap-receiver` | `list` |
| `api_clients` | `api_clients` | `identities` | `api-client` | `list` |
| `cppm_deny_listed_users` | `cppm_deny_listed_users` | `identities` | `deny-listed-users` | `list` |
| `cppm_endpoints` | `cppm_endpoints` | `identities` | `endpoint` | `list` |
| `cppm_external_account` | `cppm_external_account` | `identities` | `external-account` | `list` |
| `guest_users` | `guest_users` | `identities` | `guest` | `list` |
| `cppm_local_users` | `cppm_local_users` | `identities` | `local-user` | `list` |
| `cppm_static_host_list` | `cppm_static_host_list` | `identities` | `static-host-list` | `list` |
| `platform` | `platform` | `localserverconfiguration` | `server` | `list` |
| `cppm_system_events` | `cppm_system_events` | `logs` | `system-event` | `list` |
| `cppm_application_dict` | `cppm_application_dict` | `policyelements` | `application-dictionary` | `list` |
| `cppm_auth_methods` | `cppm_auth_methods` | `policyelements` | `auth-method` | `list` |
| `cppm_enforcement_policy` | `cppm_enforcement_policy` | `policyelements` | `enforcement-policy` | `list` |
| `cppm_network_devices` | `cppm_network_devices` | `policyelements` | `network-device` | `list` |
| `cppm_network_device_groups` | `cppm_network_device_groups` | `policyelements` | `network-device-group` | `list` |
| `cppm_network_proxy_targets` | `cppm_network_proxy_targets` | `policyelements` | `proxy-target` | `list` |
| `cppm_radius_dyn_autz_template` | `cppm_radius_dyn_autz_template` | `policyelements` | `radius-dynamic-authorization-template` | `list` |
| `cppm_posture_policy` | `cppm_posture_policy` | `policyelements` | `posture-policy` | `list` |
| `cppm_role_mapping` | `cppm_role_mapping` | `policyelements` | `role-mapping` | `list` |
| `cppm_roles` | `cppm_roles` | `policyelements` | `role` | `list` |
| `cppm_services` | `cppm_services` | `policyelements` | `service` | `list` |
| `cppm_tacacs_service_dict` | `cppm_tacacs_service_dict` | `policyelements` | `tacacs-service-dictionary` | `list` |

## Accepted But Not Yet Verified

These privilege keys were accepted by the operator-profile API and appeared in
the effective runtime privilege list, but the direct list probe still returned
`403 Forbidden` in this round, so they are not enforced in the cache filter yet.

| Operator profile privilege key | Module | Service | Current status |
| --- | --- | --- | --- |
| `cppm_messaging_setup` | `globalserverconfiguration` | `messaging-setup` | accepted, list probe still `403` |
| `smtp_config` | `globalserverconfiguration` | `messaging-setup` | accepted, list probe still `403` |
| `sms_setup` | `globalserverconfiguration` | `messaging-setup` | accepted, list probe still `403` |
| `engine_object_acl` | `globalserverconfiguration` | `operator-profile` | accepted, list probe still `403` |
| `admin` | `globalserverconfiguration` | `operator-profile` | accepted, list probe still `403` |
| `mac` | `identities` | `device` | accepted, list probe still `403` |
| `mac_list` | `identities` | `device` | accepted, list probe still `403` |
| `auth_config` | `policyelements` | `auth-source` | accepted, list probe still `403` |
| `cppm_radius_dict` | `policyelements` | `radius-dictionary` | accepted, probe hit `500` under test |

## Baseline Effective Privileges

The discovery API client baseline produced these runtime privileges:

| Raw runtime privilege | Normalized name | Access |
| --- | --- | --- |
| `?api_index` | `api_index` | `allowed` |
| `?cppm_config` | `cppm_config` | `allowed` |
| `api_docs` | `api_docs` | `full` |
| `apigility` | `apigility` | `full` |
| `cppm_endpoints` | `cppm_endpoints` | `full` |

## Notes

- `#` means read-only access.
- `?` means allowed access.
- No prefix means full access.
- The ClearPass documentation catalog remained broadly visible even for the
  restricted discovery profile, so endpoint probing was required to verify the
  real service mapping.
