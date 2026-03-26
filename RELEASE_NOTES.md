# netloom v1.9.9

This release continues the interactive CLI performance work with more
Phase 1.6 startup trimming, separate completion timing, and anti-drift
protection for the lightweight help path.

## Highlights

- added a compact derived cache index so completion and compact help no longer
  need the full API cache for normal interactive paths
- added opt-in CLI timing output with `NETLOOM_CLI_TIMING=1`
- added separate completion timing output with `NETLOOM_COMPLETION_TIMING=1`
- replaced the old plugin-import-heavy interactive cache path with a
  lightweight core cache loader for completion and compact help
- continued trimming startup/import cost in the lightweight cached
  help/completion path
- added parity tests and shared help primitives to keep the lightweight and
  full help paths aligned
- updated `CACHE_PERFORMANCE_PLAN.md` with the current Phase 1.6 status and
  latest timing results

## Examples

```bash
NETLOOM_CLI_TIMING=1 netloom logs system-event ?
NETLOOM_COMPLETION_TIMING=1 netloom poli<TAB>
netloom cache update
```

## Notes

- installable man pages still come from `netloom/data/man/`
- current timing data shows cached completion around `26-33 ms` and cached
  help around `43-44 ms`, with catalog loading itself still around `4 ms`
- the remaining interactive bottleneck is now mostly lightweight import/startup
  cost, not cache parsing or plugin catalog import
- `netloom cache update` itself is not timed yet; that is the next measurement
  improvement
