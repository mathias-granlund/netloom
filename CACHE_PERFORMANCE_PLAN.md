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

## Next Step

The next optimization should be to bypass plugin loading for fast paths.

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

### Phase 1.6: Add timing for cache update

Also add timing instrumentation for:
- `netloom cache update`

That will let us measure:
- network/discovery time
- catalog build time
- full cache write time
- fast index write time

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

Then measure again before deciding on a daemon.
