# Planned Features

## Current Priorities

### 1. `netloom shell` UX

Primary product direction for the next UX phase.

Goal:
- make `netloom` feel like an operator-first interactive tool rather than only
  a one-shot command runner
- keep the interaction model familiar to Cisco and Aruba-CX users while
  preserving the existing `netloom` command structure and UNIX-style flags

Planned behavior:
- launch with `netloom shell`
- run inside the user's current terminal first; do not make a separate window
  the default behavior
- support a resizable terminal naturally by staying terminal-native
- use a context-aware prompt driven by the active configured server profile
  name under `.config/netloom/plugins/clearpass/profiles`
- reflect navigation in the prompt, for example:
  - `<profile>:netloom#`
  - `<profile>:netloom/policyelements#`
  - `<profile>:netloom/policyelements/network-device#`
- allow bare module and service navigation, so entering `policyelements`
  changes context and entering `network-device` inside that context narrows it
  further
- allow action execution relative to the current context, for example
  `list --limit=10`
- support CLI-native affordances such as `?`, tab completion, `exit`, `top`,
  `pwd`, `show context`, and `do <full command>`

Design constraints:
- the shell must remain compatible with the existing non-interactive CLI
- the shell should be a thin interaction layer over the current parser,
  catalog, help, and command runtime where possible
- do not start implementation until explicitly requested

### 2. Shared session layer for CLI UX

Needed to make the shell fast, coherent, and extensible.

Goal:
- introduce a reusable command session model that can be shared by the shell,
  future GUI work, and any later long-lived runtime

Scope:
- keep active profile, plugin, and context state in one place
- reuse cached catalog data and interactive help data across commands
- centralize prompt state and context transitions
- prepare for token/session reuse where it is safe and useful
- keep the implementation local to the current process first

Current recommendation:
- do this before any GUI work
- treat this as the architectural foundation for future UX improvements

### 3. Delinea Secret Server as a shared keystore backend

High-value security and operations integration.

Goal:
- let `netloom-clearpass` resolve its client secret from Delinea Secret Server
- support centralized secret management without changing the active runtime
  plugin model

Scope:
- add Secret Server as a shared secret-provider backend
- support one ClearPass client-secret lookup by Secret Server path plus field
  slug
- preserve local keyring and plaintext fallback behavior

Current recommendation:
- do not introduce `netloom load secretserver` in v1
- do not build full multi-field environment mapping in v1
- prefer a small read-only `requests` client over the Delinea SDK for the
  first implementation
- use direct REST integration first, based on `/oauth2/token` and
  `/SecretServer/api/v1/...`
- use a new shared `keystores/secretserver` config area rather than
  `plugins/secretserver`
- revisit a standalone Secret Server runtime plugin only if later workflows
  need direct Secret Server operations

### 4. Web GUI on top of the same session model

Desirable after the shell and shared session layer exist.

Goal:
- provide a click-through experience for discovery, list/get flows, and common
  operational tasks without splitting the product into two different models

Scope:
- expose modules, services, and actions as navigable UI pages
- use dropdowns, forms, and guided action views generated from the same
  catalog/help metadata already used by the CLI
- surface active profile and context clearly
- add a built-in CLI pane or terminal launcher inside the GUI

Current recommendation:
- do not build the GUI first
- reuse the shell/session abstractions rather than creating a separate UI-only
  command model

### 5. `netloomd` only if later metrics justify it

Not a current priority.

Focused check completed on `2026-04-10`.

Current recommendation:
- do not continue with a `netloomd` implementation right now
- only revisit a daemon if normal shell use shows real latency pain, cache
  size grows substantially, or repeated command startup becomes a meaningful
  workflow drag
- if more optimization is needed before a daemon, focus first on startup/import
  overhead and cached catalog/index deserialization cost

### 6. Remaining ClearPass catalog and privilege coverage

Lower priority for now.

Current stance:
- current verified coverage is good enough to stop treating additional mapping
  rounds as the main focus
- keep unresolved services as opportunistic cleanup
- revisit this work when it blocks real workflows or when a UX decision depends
  on whether a service should be shown by default

### 7. Object reference inspection for ClearPass

Useful for operator safety and dependency visibility.

Goal:
- let a user check whether a ClearPass object is referenced by other objects
- surface reverse-reference information in a Fortinet-like operator-friendly way
  without forcing the user to manually inspect multiple related objects

Planned behavior:
- support checking whether an object has one or more references from parent
  objects
- show the total reference count
- list each parent object with at least:
  - object name
  - object id
- keep the feature usable from the standard `get` and/or dedicated inspection
  flows rather than making it shell-only

Design constraints:
- the implementation should fit the existing `netloom` command model and
  ClearPass plugin structure
- reference output should be easy to read in the terminal and safe to use
  before copy, update, or delete operations
- do not assume every ClearPass object type exposes references the same way;
  feature design should allow per-service handling where needed

### 8. Running-config import ID remapping

High priority for making `netloom import` restore a complete ClearPass
configuration graph after objects have been deleted and recreated.

Background:
- ClearPass auto-increments object IDs on create. The API does not appear to
  allow callers to choose the original object ID.
- `show running-config` preserves original IDs as comments such as
  `# source-id: 3085`, but mutation commands intentionally omit those IDs from
  `add` payloads.
- The generic payload normalizer strips `id` on `add`, and this is correct for
  normal ClearPass creates.
- This means importing a missing object can restore its content but not its
  numeric ID. Example:
  - export contained `# source-id: 3085`
  - import recreated `TEST-ROLE-4`
  - ClearPass assigned new ID `3088`
- The next problem is dependent object references. Any later imported payload
  that references old ID `3085` must be rewritten to new ID `3088`.

Goal:
- keep treating exported IDs as source identity metadata, not restorable
  configuration
- build an import-time ID mapping from exported source IDs to current or newly
  created ClearPass IDs
- rewrite known dependent references before applying later import operations
- keep the first implementation conservative and ClearPass-aware rather than
  blindly replacing every numeric value that happens to equal an old ID

Current relevant files:
- `netloom/cli/show.py`
  - writes `# source-id:` / `# source-uuid:` comments
  - renders replayable `netloom ... add|replace|update --payload-json=...`
    commands
- `netloom/cli/import_config.py`
  - parses running-config files into `ConfigCommand`
  - stores source identity in `ConfigCommand.source_identity`
  - builds and applies import plans
  - currently uses source IDs for matching only
- `netloom/core/resolver.py`
  - `normalize_file_payload_for_action(...)` strips `id` from `add` payloads
- `netloom/plugins/clearpass/copy_hooks.py`
  - ClearPass payload normalization goes through the generic normalizer

Desired behavior:
- When desired and current objects match:
  - if desired has `source-id` and current has an `id`, record:
    `(<module>, <service>, <old_id>) -> <current_id>`
  - this is needed even for unchanged objects, because dependencies may refer
    to old IDs from the export
- When a missing object is created:
  - apply the `add`
  - read the new ID from the API response if present
  - if the response does not include an ID, fetch the created object by a stable
    natural key such as `name`
  - record `source-id -> new_id`
- Before applying a payload that may contain references:
  - rewrite only known reference fields using the mapping
  - do not rewrite arbitrary integers globally
  - include the rewritten payload in the report, with secrets masked unless
    `--decrypt` was used
- Dry-run behavior:
  - show that a mapping would be needed for planned creates
  - mark reference rewrites as pending/conditional when the target object will
    only be known after create
  - do not claim exact new IDs during dry-run
- Report behavior:
  - include an `id_mappings` section:
    - module
    - service
    - source_id
    - current_id or created_id
    - source object label
    - how the mapping was learned: `matched`, `created_response`, or
      `created_lookup`
  - include per-item `rewrites` when payload references were changed:
    - payload path
    - old value
    - new value
    - mapped service/type when known

Implementation plan:
- Add an import identity map structure in `netloom/cli/import_config.py`.
  Suggested shape:
  - key: `(module, service, str(source_id))`
  - value:
    - `target_id`
    - `label`
    - `source_line`
    - `mapping_source`
- Populate the map during plan construction for already matched objects:
  - when `_find_current_match(...)` returns a current object
  - desired `source_identity["id"]` exists
  - current payload or current source identity has `id`
- Populate the map during execution for created objects:
  - after `_execute_plan_item(...)` returns successfully for an `add`
  - use response `id` first
  - fallback to a get/list lookup by stable natural key if needed
- Keep the current all-at-once planning model if possible, but make payload
  rewrite happen as late as possible:
  - build planned items with desired payloads
  - before executing each planned write, run reference rewrite against the
    latest ID map
  - for dry-run, report unresolved rewrite opportunities without mutating state
- Add a ClearPass reference rewrite registry.
  Start with explicit known fields only. Possible location:
  `netloom/plugins/clearpass/import_references.py`.
  Suggested rule shape:
  - affected module/service
  - payload path matcher
  - referenced module/service
  - whether field is scalar, list, or nested list
- Do not infer reference semantics from field names alone in v1.
  Field names like `id`, `role_id`, or `profile_id` are not enough without
  knowing which service they point to.
- Use plugin hook discovery so core import stays generic:
  - optional plugin hook name:
    `rewrite_import_references(payload, id_map, module, service)`
  - ClearPass plugin implements the hook
  - core import calls the hook before prepare/write preflight
- Ensure rewrite happens before:
  - `_request_args_and_payload(...)`
  - `_prepare_plugin_write_payload(...)`
  - plugin preflight
  so validation sees the final payload that will be sent.

Initial ClearPass scope:
- Start with services where broken references are likely and easy to verify:
  - `policyelements/enforcement-policy`
  - `policyelements/role-mapping`
  - `policyelements/auth-method`
  - `policyelements/auth-source`
  - `enforcementprofile/enforcement-profile`
- Inspect real exported payloads before coding exact rewrite paths.
  Use `running-config.txt` and targeted `netloom <module> <service> get/list
  --format=netloom --decrypt` output to identify reference fields.
- Add more rewrite rules only when confirmed by payload examples or API schema.

Tests to add:
- Unit test: unchanged desired/current object records source-id to current-id
  mapping.
- Unit test: created object records source-id to response id.
- Unit test: created object records source-id via lookup when response lacks id.
- Unit test: dependent payload is rewritten from old ID to mapped new ID before
  execution.
- Unit test: dry-run reports unresolved conditional rewrites without executing.
- Unit test: unrelated numeric values are not rewritten.
- Unit test: secret masking still applies in reports after rewrite.
- Integration-style test with fake ClearPass objects:
  - export role with source ID `100`
  - delete it
  - import recreates role as ID `200`
  - dependent object referencing role ID `100` is applied with `200`

Risks and constraints:
- Import ordering matters. If a dependent object is applied before its
  referenced object has been mapped, it must be skipped, delayed, or reported as
  unresolved.
- Some ClearPass services may reference objects by name rather than ID. Those
  should not be rewritten.
- Existing IDs in an export may not match a user's current file if the file is
  stale. Mapping should be based on the file being imported, not on assumptions
  from the live server.
- Do not try to force `id` back into ClearPass create payloads unless the API is
  proven to support it for a specific service.

Suggested prompt for a future implementation session:

```text
Implement running-config import ID remapping for netloom.

Read PLANNED_FEATURES.md section "Running-config import ID remapping" first.
The goal is to preserve logical references when ClearPass recreates missing
objects with new auto-incremented IDs. Do not try to restore object IDs
directly. Add an import identity map in netloom/cli/import_config.py, populate
it for matched and newly created objects, add a plugin hook for ClearPass
reference rewriting, and start with conservative service-specific rewrite rules
based on confirmed exported payload paths. Keep dry-run behavior honest by
reporting conditional/unresolved rewrites instead of inventing future IDs.
Add focused tests for mapping creation, reference rewriting, non-reference
numeric fields, and report output.
```

## Completed Work

### Cache/help/completion performance and UX groundwork

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

Implication:
- the current foundation is good enough to move attention from raw cache speed
  to overall shell and workflow UX
