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

Current cache artifacts:
- full cache: `api_endpoints_cache.json`
- fast index: `api_endpoints_index.json`

## What The Timing Data Shows

Measured examples from live runs:
- help total around `182-210 ms`
- `load_cached_index` around `4-5 ms`
- `render_help` effectively `0 ms`
- `get_plugin` around `166-190 ms`

This means the fast index work is already helping. The remaining latency is
not dominated by JSON parsing anymore. The next bottleneck is plugin/runtime
bootstrap.

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

## Measurement

### 6. Opt-in timing instrumentation

Partially done.

Current timing coverage:
- completion
- dynamic help
- cache/index loading inside those paths
- render/candidate generation inside those paths

Enabled with:
- `NETLOOM_CLI_TIMING=1`

Current stderr format:
- `[netloom timing] ...`

Still missing:
- timing for `netloom cache update`

## Next Steps

### Phase 1.5: Direct index loading for interactive paths

Planned next work:
- for completion and compact help, do not call `get_plugin()` when the cached
  index is enough
- load settings, resolve the active plugin name, and read the cached index
  directly from disk
- only fall back to `get_plugin()` when:
  - the fast index is missing
  - richer full-catalog data is required
  - a real runtime command needs plugin behavior

Expected result:
- remove most of the current `get_plugin` timing cost from help/completion

Priority:
- highest

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
- process startup and bootstrap still matter even after the cache/index win
- this should help one-shot commands that do not need full runtime setup

Priority:
- high

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

If Phase 1.5 still leaves completion/help too slow:
- introduce `netloomd`
- keep the catalog/index in RAM
- let completion and help query the daemon instead of reparsing cache files

## Recommendation

Do not jump to `netloomd` yet.

The current data suggests the next highest-ROI step is:
- direct cached-index loading for help/completion
- add timing for `cache update`
- delay imports/runtime setup for trivial CLI paths

Then measure again before deciding on a daemon.

Recommended order:
1. Phase 1.5
2. Phase 1.7
3. Phase 1.6
4. Phase 1.8
5. Phase 1.9
