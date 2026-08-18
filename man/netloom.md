# `netloom(1)`

GitHub-friendly reference for the shared `netloom` CLI.

Markdown source of truth for the installable man page:
[netloom/data/man/netloom.1](../netloom/data/man/netloom.1)

## Name

`netloom` is a shared command-line interface for plugin-backed network APIs.

## Synopsis

```bash
netloom [GLOBAL-OPTIONS] <module> <service> <action> [KEY=VALUE ...]
netloom load [list | show | <plugin>]
netloom server [list | show | use <profile>]
netloom cache [clear | update]
netloom shell
netloom show running-config [options]
netloom import --file=FILE [options]
netloom [--help | ?]
netloom --version
```

## Description

`netloom` provides a common CLI surface for vendor-specific network API
plugins.

The shared runtime handles plugin selection, profile switching, cache
management, output formatting, logging, and generic request options. The exact
modules, services, actions, and request fields available under
`netloom <module> <service> <action>` depend on the active plugin and whatever
API documentation that plugin discovers from the selected server.

For provider-specific behavior, use the matching plugin reference such as
[netloom-clearpass.md](./netloom-clearpass.md).

## Built-In Commands

- `netloom load <plugin>`: Persist the active plugin used by later
  plugin-backed commands.
- `netloom load list`: List installed or configured plugins.
- `netloom load show`: Show the currently selected plugin.
- `netloom server list`: List configured profiles for the active plugin.
- `netloom server show`: Show the current profile and the config files that
  affect it.
- `netloom server use <profile>`: Select the active profile inside the active
  plugin.
- `netloom cache update`: Refresh the local API catalog for the active plugin.
- `netloom cache clear`: Remove the cached API catalog for the active plugin.
- `netloom shell`: Launch the interactive shell with context navigation,
  completion, history, and context-aware help.
- `netloom show running-config`: Export live configuration data as replayable
  `netloom ... --payload-json=...` commands.
- `netloom import --file=FILE`: Read a running-config export, compare it to the
  active server, and apply only reversible changes.

## Command Model

General form:

```bash
netloom <module> <service> <action> [--key=value ...]
```

Common actions:

- `list`: List a collection. Often equivalent to `get --all`.
- `get`: Retrieve one resource or, with `--all`, a collection.
- `add`: Create a resource.
- `update`: Patch an existing resource.
- `replace`: Replace an existing resource.
- `delete`: Delete an existing resource.
- `copy`: Copy matching resources from one profile to another when supported by
  the active plugin.
- `diff`: Compare matching resources between two profiles when supported by the
  active plugin.

Modules, services, actions, selectors, and request metadata are discovered
dynamically and may differ by plugin, server version, and enabled API surface.

## Plugins

Plugins provide vendor-specific authentication, discovery, payload handling,
normalization, and documentation while reusing the shared `netloom` runtime.

At least one plugin must be selected before running plugin-backed commands:

```bash
netloom load clearpass
```

## Global Options

- `--log-level=LEVEL`: Set the runtime log level. Use `none` to suppress logs.
- `--console`: Also print response output to the terminal.
- `--out=FILE`: Write output to an explicit file.
- `--format=FORMAT`: Choose `json`, `csv`, `raw`, or `netloom`.
- `--csv-fieldnames=FIELDS`: Comma-separated field order for CSV output.
- `--file=FILE`: Load JSON or CSV input for write or bulk-style actions.
- `--api-token=TOKEN`: Use an existing bearer token instead of logging in
  through the plugin.
- `--token-file=FILE`: Read a bearer token from a file.
- `--catalog-view=visible|full`: Choose the visible or retained full catalog.
- `--limit=N`: Set page size when supported by the endpoint.
- `--offset=N`: Set a collection offset when supported by the endpoint.
- `--sort=FIELD`: Set server-side sort when supported by the endpoint.
- `--filter=JSON|FIELD:OP:VALUE`: Set a server-side filter when supported by
  the endpoint.
- `--calculate-count=true|false`: Request total-count style responses when
  supported.
- `--encrypt=enable|disable`: Control masking of secret values in output.
- `--decrypt`: Disable output masking and show secrets in output.
- `--help` or `?`: Show context-aware help.
- `--version`: Show version.

## Filter Expressions

When a plugin supports server-side filtering, `netloom` accepts either
shorthand expressions or raw JSON expressions.

Shorthand form:

```text
FIELD:OP:VALUE
```

Common operators:

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

Common shorthand examples:

```bash
--filter=name:equals:TEST
--filter=name:contains:guest
--filter=id:in:1,2,3
--filter=enabled:exists:true
```

Common JSON patterns:

```json
{"key":{"$eq":"value"}}
{"key":{"$ne":"value"}}
{"key":{"$contains":"value"}}
{"key":{"$in":["value1","value2"]}}
{"key":{"$nin":["value1","value2"]}}
{"key":{"$gt":"value"}}
{"key":{"$gte":"value"}}
{"key":{"$lt":"value"}}
{"key":{"$lte":"value"}}
{"key":{"$regex":"regex"}}
{"key":{"$exists":true}}
{"key":{"$exists":false}}
{"$and":[filter1,filter2]}
{"$or":[filter1,filter2]}
{"$not":{filter}}
```

Advanced examples:

```bash
--filter='{"name":{"$contains":"guest"}}'
--filter='{"$and":[{"status":{"$eq":"Known"}},{"enabled":{"$exists":true}}]}'
```

Shell quoting matters because JSON expressions are passed as strings.

## Catalog Views

Some plugins retain more discovered metadata than they expose by default.
`--catalog-view=visible` shows the normal operator-facing subset, while
`--catalog-view=full` shows the full retained discovery data.

Typical troubleshooting flow:

```bash
netloom --catalog-view=full ?
netloom --catalog-view=full <module> <service> ?
```

## Output

By default, `netloom` writes response files under its state and output
directories. Default generated filenames include timestamps so repeated
commands do not overwrite earlier artifacts.

Supported output formats:

- `json`: Pretty-printed JSON output.
- `csv`: CSV output for list-style data.
- `raw`: Raw text or binary output, commonly used for export and download
  endpoints.
- `netloom`: Replayable `netloom ... add|replace|update --payload-json=...`
  commands for `get`, `get --all`, and `list` output.

## Running Config Export And Import

`netloom show running-config` walks the active catalog, reads supported
configuration objects, and writes replayable netloom commands. The default
output path is `NETLOOM_OUT_DIR/running-config.txt`. The `logs` module is
excluded because it contains event history, and
`globalserverconfiguration/messaging-setup` is excluded because ClearPass does
not return the SMTP password even with `--decrypt`.

Default exclusions come from `NETLOOM_RUNNING_CONFIG_EXCLUDE`, using the same
syntax as `--exclude=module[/service][,...]`. Passing `--exclude` on the CLI
replaces the configured list for that run.

```bash
netloom show running-config --out=running-config.txt
netloom show running-config --include=policyelements/network-device --decrypt
```

`netloom import` reads that file, exports the same services from the active
server, compares both running-config command sets, and applies only reversible
changes. Identical objects are skipped. Creates require a matching delete
action for rollback, deletes require a matching add action for rollback, and
updates use replace or update actions that can be matched to current objects.

```bash
netloom import --file=running-config.txt --dry-run
netloom import --file=running-config.txt --continue-on-error --out=import-report.json
```

Use `--dry-run` before writing to review the planned reversible changes.
Use `--continue-on-error` to keep processing after a failed line and
`--out=FILE` to save a JSON import report.

By default, exports mask secret fields. To produce a complete replay file,
export with `--decrypt` or configure a plugin-supported secret provider that
can backfill missing secret values during import.

## Environment

- `NETLOOM_ACTIVE_PROFILE`
- `NETLOOM_VERIFY_SSL`
- `NETLOOM_TIMEOUT`
- `NETLOOM_LOG_LEVEL` (`NONE` suppresses logs)
- `NETLOOM_DATA_FORMAT`
- `NETLOOM_CONSOLE`
- `NETLOOM_ENCRYPT_SECRETS`
- `NETLOOM_CACHE_DIR`
- `NETLOOM_STATE_DIR`
- `NETLOOM_OUT_DIR`
- `NETLOOM_APP_LOG_DIR`
- `NETLOOM_CONFIG_DIR`
- `NETLOOM_RUNNING_CONFIG_EXCLUDE`

Plugin references may define additional provider-specific variables.

## Files

- `~/.config/netloom/config.env`: Stores the active plugin selection.
- `~/.config/netloom/plugins/<plugin>/`: Plugin-specific configuration root.
- `~/.cache/netloom/`: Default cache directory on Linux when XDG-style defaults
  are used.
- `~/.local/state/netloom/`: Default state directory.
- `~/.local/state/netloom/responses/`: Default response output directory.
- `~/.local/state/netloom/logs/`: Default log directory.

## Completion And Help

Completion quality depends on the local API catalog. If module or service names
look incomplete, refresh the cache:

```bash
netloom cache update
```

Dynamic help is available at several levels:

```bash
netloom ?
  cache                       Manage the local API catalog cache
  load                        Select or inspect the active plugin
  server                      Select or inspect the active profile
  import                      Import a saved running-config file
  policyelements              Policy elements and network services

netloom certificateauthority ?
  certificate-chain           Get a certificate and its trust chain
  certificate-export          Export a certificate or certificate signing request

netloom <module> <service> ?
netloom <module> <service> <action> ?
```

When the Bash completion script is installed, `?` can also describe the
current context immediately without pressing `Enter`.

## Bash Completion

The repository includes a Bash completion script at
[`scripts/netloom-completion.bash`](../scripts/netloom-completion.bash).

Run it once for the current shell session:

```bash
source /path/to/netloom/scripts/netloom-completion.bash
```

One simple persistent setup is:

```bash
mkdir -p ~/.bash_completion.d
cp /path/to/netloom/scripts/netloom-completion.bash ~/.bash_completion.d
```

Then load files from that directory in `~/.bashrc` or the equivalent shell
startup file:

```bash
if [ -d "$HOME/.bash_completion.d" ]; then
  for f in "$HOME"/.bash_completion.d/*; do
    [ -r "$f" ] && source "$f"
  done
fi
```

If discovered modules or services look incomplete, run:

```bash
netloom cache update
```

## Examples

```bash
netloom load clearpass
netloom cache update
netloom server use <profile>
netloom identities endpoint list --limit=10
netloom policyelements network-device get --id=1001 --console
netloom policyelements network-device add ?
netloom certificateauthority certificate-chain get ?
netloom show running-config --out=running-config.txt
netloom import --file=running-config.txt --dry-run
```

## See Also

- [man/netloom-clearpass.md](./netloom-clearpass.md)
- [netloom/data/man/netloom.1](../netloom/data/man/netloom.1)
