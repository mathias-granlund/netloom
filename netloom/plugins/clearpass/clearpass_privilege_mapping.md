## Verified ClearPass Privilege Mappings

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
| `cppm_enforcement_profile` | `cppm_enforcement_profile` | `enforcementprofile` | `enforcement-profile` | `list` |
| `cppm_admin_privileges` | `cppm_admin_privileges` | `globalserverconfiguration` | `admin-privilege` | `list` |
| `cppm_admin_users` | `cppm_admin_users` | `globalserverconfiguration` | `admin-user` | `list` |
| `cppm_licenses` | `cppm_licenses` | `globalserverconfiguration` | `application-license` | `list` |
| `cppm_attributes` | `cppm_attributes` | `globalserverconfiguration` | `attribute` | `list` |
| `cppm_clearpass_portal` | `cppm_clearpass_portal` | `globalserverconfiguration` | `clearpass-portal` | `list` |
| `cppm_data_filters` | `cppm_data_filters` | `globalserverconfiguration` | `data-filter` | `list` |
| `cppm_file_backup_server` | `cppm_file_backup_server` | `globalserverconfiguration` | `file-backup-server` | `list` |
| `auth_profiles` | `auth_profiles` | `globalserverconfiguration` | `operator-profile` | `list` |
| `cppm_server_policy_manager_zones` | `cppm_server_policy_manager_zones` | `globalserverconfiguration` | `policy-manager-zones` | `list` |
| `cppm_snmp_trap_receivers` | `cppm_snmp_trap_receivers` | `globalserverconfiguration` | `snmp-trap-receiver` | `list` |
| `api_clients` | `api_clients` | `identities` | `api-client` | `list` |
| `mac` + `guest_users` | `mac` + `guest_users` | `identities` | `device` | `list` |
| `cppm_deny_listed_users` | `cppm_deny_listed_users` | `identities` | `deny-listed-users` | `list` |
| `cppm_endpoints` | `cppm_endpoints` | `identities` | `endpoint` | `list` |
| `cppm_external_account` | `cppm_external_account` | `identities` | `external-account` | `list` |
| `guest_users` | `guest_users` | `identities` | `guest` | `list` |
| `cppm_local_users` | `cppm_local_users` | `identities` | `local-user` | `list` |
| `cppm_static_host_list` | `cppm_static_host_list` | `identities` | `static-host-list` | `list` |
| `platform` | `platform` | `localserverconfiguration` | `server` | `list` |
| `cppm_system_events` | `cppm_system_events` | `logs` | `system-event` | `list` |
| `cppm_application_dict` | `cppm_application_dict` | `policyelements` | `application-dictionary` | `list` |
| `auth_config` + `cppm_config` | `auth_config` + `cppm_config` | `policyelements` | `auth-source` | `list` |
| `cppm_auth_methods` | `cppm_auth_methods` | `policyelements` | `auth-method` | `list` |
| `cppm_enforcement_policy` | `cppm_enforcement_policy` | `policyelements` | `enforcement-policy` | `list` |
| `cppm_network_devices` | `cppm_network_devices` | `policyelements` | `network-device` | `list` |
| `cppm_network_device_groups` | `cppm_network_device_groups` | `policyelements` | `network-device-group` | `list` |
| `cppm_network_proxy_targets` | `cppm_network_proxy_targets` | `policyelements` | `proxy-target` | `list` |
| `cppm_radius_dict` | `cppm_radius_dict` | `policyelements` | `radius-dictionary` | `list` |
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
| `cppm_messaging_setup` | `globalserverconfiguration` | `messaging-setup` | accepted, but endpoint returns `404` even for admin |
| `smtp_config` | `globalserverconfiguration` | `messaging-setup` | accepted, but endpoint returns `404` even for admin |
| `sms_setup` | `globalserverconfiguration` | `messaging-setup` | accepted, but endpoint returns `404` even for admin |

## Combo Rules

Some services need more than one effective runtime privilege at the same time.
Those are enforced in the cache as `all-of` rules instead of normal single-key
matches.

| Module | Service | Required effective privileges |
| --- | --- | --- |
| `identities` | `device` | `mac` and `guest_users` |
| `policyelements` | `auth-source` | `auth_config` and `cppm_config` |

## Remaining Unresolved Services

These are the only services still not promoted into enforced cache mappings after
the current live discovery rounds:

| Module | Service | Current blocker |
| --- | --- | --- |
| `globalserverconfiguration` | `messaging-setup` | endpoint returns `404` even for admin |

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
