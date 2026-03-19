## Verified ClearPass Privilege Mappings

These mappings were verified live against a dedicated discovery operator profile.
The profile kept the baseline API privileges `api_docs`, `apigility`, and
`cppm_endpoints`, then one extra privilege key was added at a time and the
resulting endpoint probes were checked.

| Operator profile privilege key | Effective runtime privilege | Module | Service | Verified access |
| --- | --- | --- | --- | --- |
| `cppm_endpoints` | `cppm_endpoints` | `identities` | `endpoint` | `list` |
| `cppm_local_users` | `cppm_local_users` | `identities` | `local-user` | `list` |
| `cppm_network_devices` | `cppm_network_devices` | `policyelements` | `network-device` | `list` |
| `cppm_network_device_groups` | `cppm_network_device_groups` | `policyelements` | `network-device-group` | `list` |
| `cppm_admin_privileges` | `cppm_admin_privileges` | `globalserverconfiguration` | `admin-privilege` | `list` |

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
