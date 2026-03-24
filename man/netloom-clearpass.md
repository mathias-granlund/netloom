# `netloom-clearpass(7)`

GitHub-friendly reference for the bundled ClearPass plugin.

Source of truth for the installable man page:
[netloom/data/man/netloom-clearpass.7](../netloom/data/man/netloom-clearpass.7)

## Name

`netloom-clearpass` is the ClearPass plugin reference for `netloom`.

## Synopsis

```bash
netloom load clearpass
netloom server use <profile>
netloom cache update
netloom <module> <service> <action> [options]
```

## Description

The plugin targets HPE Aruba ClearPass Policy Manager and discovers the API
surface dynamically from the documentation endpoints exposed by the selected
server. Available modules, services, actions, request fields, and response
metadata can therefore vary between deployments and software versions.

Use this guide for ClearPass-specific behavior that does not belong in the
shared `netloom(1)` reference: configuration layout, authentication methods,
discovery workflow, privilege-aware catalog behavior, filtering conventions,
and the profile-to-profile `copy` and `diff` workflows.

## Configuration

The ClearPass plugin stores configuration under:

```text
~/.config/netloom/plugins/clearpass/
```

Important files and directories:

- `defaults.env`: Plugin-wide defaults such as the active profile, TLS
  verification, timeout, and path overrides.
- `profiles/<profile>.env`: Per-profile connection settings such as
  `NETLOOM_SERVER`.
- `credentials/<profile>.env`: Per-profile authentication settings such as
  `NETLOOM_CLIENT_ID`, `NETLOOM_CLIENT_SECRET_REF`,
  `NETLOOM_CLIENT_SECRET`, `NETLOOM_API_TOKEN`, or
  `NETLOOM_API_TOKEN_FILE`.

Typical layout:

```text
~/.config/netloom/plugins/clearpass/defaults.env
~/.config/netloom/plugins/clearpass/profiles/dev.env
~/.config/netloom/plugins/clearpass/credentials/dev.env
```

Minimal profile connection settings:

```bash
NETLOOM_SERVER=clearpass.example.com:443
```

Minimal OAuth client credentials:

```bash
NETLOOM_CLIENT_ID=dev-client-id
NETLOOM_CLIENT_SECRET_REF=dev/client-secret
```

Direct `NETLOOM_*` environment variables still override profile files when set
in the current shell session.

## Authentication

The ClearPass plugin supports three practical authentication paths:

- OAuth client credentials via `NETLOOM_SERVER`, `NETLOOM_CLIENT_ID`, and
  either `NETLOOM_CLIENT_SECRET_REF` or `NETLOOM_CLIENT_SECRET`
- Direct bearer token via `NETLOOM_API_TOKEN`
- Token file via `NETLOOM_API_TOKEN_FILE`

When a login secret is needed, the runtime checks in this order:

1. `NETLOOM_API_TOKEN`
2. `NETLOOM_API_TOKEN_FILE`
3. keychain-resolved `NETLOOM_CLIENT_SECRET_REF`
4. plaintext `NETLOOM_CLIENT_SECRET`

## Keychain Setup

When `NETLOOM_CLIENT_SECRET_REF` is configured, the runtime resolves the client
secret from the OS keychain with:

- service: `netloom/clearpass`
- username: the literal value of `NETLOOM_CLIENT_SECRET_REF`

Typical setup:

```bash
python -m keyring set netloom/clearpass dev/client-secret
```

```bash
NETLOOM_CLIENT_ID=dev-client-id
NETLOOM_CLIENT_SECRET_REF=dev/client-secret
```

To inspect the backend that Python `keyring` sees:

```bash
python -m keyring diagnose
python -m keyring --help
```

To verify a stored secret:

```bash
python -m keyring get netloom/clearpass dev/client-secret
```

In headless Linux or WSL-style environments, a keyring backend may need to be
installed and unlocked explicitly:

```bash
sudo apt install -y gnome-keyring
dbus-run-session -- bash
echo 'choose-a-keyring-password' | gnome-keyring-daemon --unlock
python -m keyring set netloom/clearpass dev/client-secret
```

If `NETLOOM_CLIENT_SECRET_REF` is configured but no usable backend exists, the
runtime only falls back to plaintext `NETLOOM_CLIENT_SECRET` when that value is
also configured.

## Discovery And Cache

The ClearPass plugin discovers API structure from documentation endpoints such
as:

- `/api-docs`: top-level module and service discovery
- `/api/apigility/documentation/<Module-v1>`: action metadata, request field
  hints, and endpoint details for a module

Refresh discovery metadata when the ClearPass server is upgraded, when API
features change, or when help/completion looks stale:

```bash
netloom cache clear
netloom cache update
```

The resulting cache powers shell completion, context-aware help, and command
validation.

## Privilege-Aware Catalog

During `netloom cache update` the ClearPass plugin also queries
`/api/oauth/privileges` for effective runtime privileges.

The plugin keeps the full discovered catalog, then builds a stricter default
visible view from verified privilege mappings. This makes normal help,
completion, and command discovery better match what the current API client can
actually access.

To inspect the retained full discovery data:

```bash
netloom --catalog-view=full ?
netloom --catalog-view=full <module> <service> ?
netloom --catalog-view=full <module> <service> <action> ?
```

## Filtering

When an endpoint supports server-side filtering, the ClearPass plugin accepts
either shorthand filters or full JSON expressions.

Shorthand examples:

```bash
--filter=name:equals:TEST
--filter=name:contains:guest
--filter=id:in:1,2,3
--filter=enabled:exists:true
```

Supported shorthand operators:

```text
equals
not-equals
contains
in
not-in
gt
gte
lt
lte
exists
```

Useful JSON patterns:

```json
{"key":{"$eq":"value"}}
{"key":{"$contains":"value"}}
{"key":{"$in":["value1","value2"]}}
{"$and":[filter1,filter2]}
{"$or":[filter1,filter2]}
{"$not":{filter}}
```

Advanced JSON examples:

```bash
--filter='{"name":{"$contains":"TEST"}}'
--filter='{"$and":[{"name":{"$contains":"TEST"}},{"status":{"$eq":"Known"}}]}'
```

Shell quoting matters because JSON expressions are passed as strings.

## Copy Workflow

Preferred syntax:

```bash
netloom <module> <service> copy --from=SOURCE --to=TARGET [options]
```

Useful options include:

- `--dry-run`: Preview planned writes without changing the target profile.
- `--match-by=auto|name|id`: Choose how target objects are matched.
- `--on-conflict=fail|skip|update|replace`: Choose the write strategy when a
  match already exists.
- `--save-source=FILE`: Save fetched source objects.
- `--save-payload=FILE`: Save normalized write payloads.
- `--save-plan=FILE`: Save the planned operations.

The plugin normalizes payloads before replaying them so response-only metadata,
links, IDs, and similar API noise are not sent back as write input.

## Diff Workflow

Preferred syntax:

```bash
netloom <module> <service> diff --from=SOURCE --to=TARGET [options]
```

Useful options include:

- `--match-by=auto|name|id`
- `--all`
- `--filter=JSON|FIELD:OP:VALUE`
- `--fields=FIELD1,FIELD2`
- `--ignore-fields=FIELD1,FIELD2`
- `--out=FILE`
- `--show-all`
- `--max-items=N`

Broad selectors such as `--all` and `--filter` produce symmetric reports with
`same`, `different`, `only_in_source`, and `only_in_target` statuses. Narrow
selectors such as `--id` and `--name` stay source-scoped and primarily answer
whether the chosen source object matches an object in the target profile.

## Troubleshooting

If a profile is not behaving as expected, start with:

```bash
netloom server show
```

If help or completion looks incomplete, refresh the cache:

```bash
netloom cache update
```

If a module or service seems to be missing for the current API client, inspect
the retained catalog:

```bash
netloom --catalog-view=full ?
```

## Examples

```bash
netloom identities endpoint list --limit=10
netloom identities endpoint list --filter=name:contains:guest
netloom policyelements network-device get --id=1001
netloom policyelements network-device copy --from=dev --to=prod --all --dry-run
netloom policyelements role diff --from=lab --to=prod --all
netloom policyelements network-device add ?
```

## See Also

- [man/netloom.md](./netloom.md)
- [netloom/data/man/netloom-clearpass.7](../netloom/data/man/netloom-clearpass.7)
