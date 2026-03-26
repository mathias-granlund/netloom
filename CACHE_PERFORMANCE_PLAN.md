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
- opt-in timing is available with `NETLOOM_CLI_TIMING=1`

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

One current gap:
- `netloom cache update` is not timed yet

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
- render/candidate generation inside those paths

Enabled with:
- `NETLOOM_CLI_TIMING=1`

Current stderr format:
- `[netloom timing] ...`

Still missing:
- timing for `netloom cache update`

## Next Steps

### Phase 1.6: Late imports and late runtime setup

Planned work:
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

Planned work:
- add timing instrumentation for `netloom cache update`

That should measure:
- `/api-docs` fetch time
- module listing fetch time
- subdocument fetch time
- catalog transform/build time
- full cache write time
- fast index write time

Why:
- we need real data before changing the catalog rebuild architecture

Priority:
- high

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

### Phase 1.9: Parallelize catalog rebuild if timing confirms it

Planned work:
- after Phase 1.7 timing is in place, profile `netloom cache update` against a
  real ClearPass server
- if network latency dominates, parallelize module listing and/or subdocument
  fetches with a small bounded worker pool

Why:
- catalog rebuild is currently very sequential
- this is likely the biggest real-world win for `cache update`, but it should
  be data-driven

Priority:
- medium, after timing confirms it is worthwhile

## Phase 2

If Phase 1.6 still leaves completion/help too slow:
- introduce `netloomd`
- keep the catalog/index in RAM
- let completion and help query the daemon instead of reparsing cache files

## Recommendation

Do not jump to `netloomd` yet.

The current data suggests the next highest-ROI step is:
- delay imports/runtime setup for trivial CLI paths
- add timing for `cache update`
- then measure again before deciding whether any deeper cache-path work is
  still needed

The interactive cache-loading bottleneck has already been addressed in Phase
1.5, and the remaining help/completion latency is now small enough that future
work should be driven by measured startup cost.

Recommended order:
1. Phase 1.6
2. Phase 1.7
3. Phase 1.8
4. Phase 1.9
