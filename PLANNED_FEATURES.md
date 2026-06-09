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
