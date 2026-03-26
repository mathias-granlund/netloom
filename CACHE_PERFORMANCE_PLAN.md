# Cache Performance Plan

## Goal

Speed up:
- shell completion
- dynamic `?` help
- module/service/action discovery

without losing any catalog data.

## Current Status

Phase 1 is implemented:
- the full cache is now written as compact JSON instead of pretty JSON
- `netloom cache update` writes a derived fast index alongside the full cache
- completion prefers the fast index
- compact help prefers the fast index
- full-cache fallback behavior is still preserved
- opt-in help timing is available with `NETLOOM_CLI_TIMING=1`
- opt-in completion timing is available with `NETLOOM_COMPLETION_TIMING=1`

Phase 1.5 is now implemented for the main interactive bottleneck:
- completion and compact help use a core-owned lightweight cache loader
- that loader reads `api_endpoints_index.json` directly from
  `settings.paths.cache_dir`
- the fast path no longer imports `netloom.plugins.clearpass.catalog`
- fallback to plugin/runtime-backed behavior is still preserved when the cache
  is missing, invalid, or insufficient

Current cache artifacts:
- full cache: `api_endpoints_cache.json`
- fast index: `api_endpoints_index.json`

## What The Timing Data Shows

Earlier measured examples from live runs:
- help total around `182-210 ms`
- `load_cached_index` around `4-5 ms`
- `render_help` effectively `0 ms`
- `get_plugin` around `166-190 ms`

That first round showed the fast index work was already helping, but
plugin/runtime bootstrap was still dominating interactive latency.

After the completion-first Phase 1.5 follow-up, recent live timings now look
like this:
- `netloom globalserverconfiguration admin-user ?`
  - help total `15.7 ms`
  - `load_core_cached_catalog=2.9 ms`
- `netloom ?`
  - help total `20.2 ms`
  - `load_core_cached_catalog=3.3 ms`
- `netloom policyelements network-device ?`
  - help total `16.0 ms`
  - `load_core_cached_catalog=2.9 ms`
- `netloom policyelements network-device list ?`
  - help total `16.4 ms`
  - `load_core_cached_catalog=3.1 ms`
- `netloom apioperations ?`
  - help total `16.6 ms`
  - `load_core_cached_catalog=2.9 ms`

This confirms the real interactive bottleneck was not JSON parsing itself, but
the old "direct" path still importing plugin catalog code. With the
lightweight core loader in place:
- cache/index loading is now back in the low single-digit millisecond range
- help rendering remains effectively free
- the remaining interactive latency is now mostly process startup and other
  runtime setup outside catalog rendering

After the first Phase 1.6 slices, the cached help/completion path no longer
imports the plugin layer on normal runs, and the remaining work is now mostly
import time inside the lightweight interactive modules themselves.

Recent live timings after the current Phase 1.6 work:
- help:
  - `netloom apioperations ?`
    - total `43.8 ms`
    - `import_cache_layer=11.7 ms`
    - `load_core_cached_catalog=4.7 ms`
    - `import_help_layer=12.9 ms`
  - `netloom globalserverconfiguration admin-user ?`
    - total `43.1 ms`
    - `import_cache_layer=13.2 ms`
    - `load_core_cached_catalog=4.1 ms`
    - `import_help_layer=13.1 ms`
- completion:
  - `netloom api<TAB>`
    - total `33.1 ms`
    - `import_cache_layer=14.2 ms`
    - `load_core_cached_catalog=4.2 ms`
    - `import_completion_layer=14.7 ms`
  - `netloom glo<TAB>`
    - total `26.2 ms`
    - `import_cache_layer=11.6 ms`
    - `load_core_cached_catalog=3.7 ms`
    - `import_completion_layer=10.8 ms`
  - `netloom glo... admi<TAB>`
    - total `26.9 ms`
    - `import_cache_layer=11.9 ms`
    - `load_core_cached_catalog=3.9 ms`
    - `import_completion_layer=10.9 ms`

This means:
- completion is now clearly faster than help, which matches the priority
- cache loading itself is no longer the bottleneck
- help/completion are now mostly import-startup-bound in the lightweight
  interactive layers

One current gap:
- `netloom cache update` now has timing, and the measured bottleneck is
  subdocument fetch latency rather than local transform/write work

## Phase 1 Summary

### 1. Compact full cache

Done.

The full cache remains the source of truth, but it now uses compact JSON to
reduce file size and parse cost.

### 2. Derived fast index

Done.

The fast index keeps only the fields needed for:
- completion
- compact help

It stores compact action metadata such as:
- `paths`
- `params`
- `body_required`
- trimmed `body_fields`

It intentionally excludes bulkier fields that compact help does not need:
- long notes
- response codes
- response content types
- generated body examples

### 3. Route completion to the fast index

Done.

### 4. Route compact help to the fast index where possible

Done.

Used for:
- top-level help
- module help
- service help
- compact action help

Full cache is still used as a fallback when richer metadata is needed.

### 5. Keep full-cache fallback behavior

Done.

If the fast index is missing, stale, or unreadable:
- fall back to the full cache
- preserve current behavior

### Phase 1.5: Completion-first lightweight cache loading

Done.

Implemented:
- a core-owned, read-only interactive cache loader
- direct reads of `api_endpoints_index.json` from `settings.paths.cache_dir`
- support for visible and full catalog views
- fallback to the full cache only when needed
- fallback to plugin/runtime-backed behavior when cache-only data is
  unavailable

Used by:
- shell completion
- top-level help
- module help
- service help
- compact action help

Result:
- interactive help/completion no longer pay plugin catalog import cost on
  normal cached runs
- real-world help timings dropped from roughly `155-195 ms` in the hot path to
  roughly `15-20 ms` total
- the main remaining interactive optimization target is startup/import/runtime
  setup, not catalog loading

## Measurement

### 6. Opt-in timing instrumentation

Partially done.

Current timing coverage:
- completion
- dynamic help
- core cache/index loading inside those paths
- import cost inside the lightweight interactive cache/help/completion layers
- render/candidate generation inside those paths

Enabled with:
- `NETLOOM_CLI_TIMING=1` for help
- `NETLOOM_COMPLETION_TIMING=1` for shell completion

Current stderr format:
- `[netloom timing] ...`

Still missing:
- no major timing gap remains for the current cache/help/completion work

## Next Steps

### Phase 1.6: Late imports and late runtime setup

In progress.

Implemented so far:
- delayed more runtime setup in `netloom.cli.main`
- moved normal cached help/completion away from plugin-layer imports
- introduced lightweight interactive config helpers for plugin/path/profile
  resolution
- introduced lightweight interactive cache and compact help paths
- separated completion timing from help timing so completion can be measured
  without turning on help timing output
- split timing buckets so import cost is measured separately from cache load
  and render/candidate generation
- added shared help primitives and parity tests so the fast path and the
  general help path are less likely to drift apart

Remaining work:
- continue trimming import time inside the lightweight interactive help/cache
  modules
- keep measuring before doing deeper structural changes
- add timing for `netloom cache update` before changing rebuild architecture

Original scope:
- delay heavier imports and runtime setup until after CLI parsing decides
  whether the user only requested:
  - `--version`
  - `--help`
  - shell completion
  - other trivial built-in paths
- avoid importing plugin/runtime-heavy modules earlier than necessary in
  `netloom.cli.main`

Why:
- process startup and bootstrap now dominate the remaining interactive latency
- this should help one-shot commands that do not need full runtime setup
- completion is the most latency-sensitive path and should remain the primary
  optimization target here

Priority:
- highest

### Phase 1.7: Add timing for cache update

Done.

Implemented:
- timing instrumentation for `netloom cache update`
- top-level timing around client build and authentication
- detailed timing buckets for:
  - `/api-docs` fetch time
  - effective-privileges fetch time
  - module listing fetch time
  - subdocument fetch time
  - catalog transform/build time
  - full cache write time
  - fast index write time

Measured result from a live run:
- total `23.15 s`
- `fetch_subdocuments=19.71 s`
- `fetch_module_listings=2.24 s`
- `build_catalog=0.33 s`
- `write_full_cache=0.02 s`
- `write_fast_index=0.01 s`

Conclusion:
- cache rebuild is clearly network-bound
- local transform/write work is comparatively tiny
- future rebuild-performance work should be justified by UX value, not by
  assumptions about CPU or JSON overhead

### Phase 1.8: Validate shallow full-view projection

Planned work:
- evaluate whether `project_catalog_view(..., catalog_view=\"full\")` can reuse
  `full_modules` directly instead of deep-copying it
- only keep this optimization if downstream consumers treat the catalog as
  read-only
- add a regression test so this assumption stays explicit

Why:
- it is a small, low-risk optimization if the catalog stays immutable in
  practice

Priority:
- medium

### Cache-update progress reporting

Done.

Implemented:
- lightweight stderr progress reporting for `netloom cache update`
- visible stage updates for:
  - building client
  - authentication
  - `/api-docs`
  - effective privileges
  - module listings
  - subdocument fetch progress
  - catalog build
  - full cache write
  - fast index write

Why:
- the measured cache-update bottleneck is long-running network fetch time
- user confidence and visibility matter more than shaving a few local
  milliseconds off rebuild work

### Phase 1.9: Parallelize catalog rebuild if timing confirms it

Deferred for now.

Current recommendation:
- do not parallelize cache rebuild yet
- the timing data confirms that parallel fetches would be the main technical
  optimization path if we revisit cache-update performance later
- for now, progress reporting addresses the more immediate UX concern that the
  command can otherwise look hung during long subdocument fetch phases

## Phase 2

If Phase 1.6 still leaves completion/help too slow:
- introduce `netloomd`
- keep the catalog/index in RAM
- let completion and help query the daemon instead of reparsing cache files

## Recommendation

Do not jump to `netloomd` yet.

The current data suggests the next highest-ROI step is:
- continue trimming import/runtime setup cost inside the lightweight
  interactive help/completion layers
- keep the new cache-update timing and progress reporting in place
- revisit parallel cache rebuild work only if the `~23 s` live rebuild time
  becomes a practical pain point in normal use

The interactive cache-loading bottleneck has already been addressed in Phase
1.5, and the remaining help/completion latency is now small enough that future
work should be driven by measured startup cost and user-perceived UX value.

Recommended order:
1. Phase 1.6
2. Phase 1.8
3. revisit Phase 1.9 only if cache-update latency becomes worth optimizing
