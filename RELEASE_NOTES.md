# netloom v1.9.8

This release focuses on interactive CLI performance work and the follow-up
planning around completion and dynamic help latency.

## Highlights

- added a compact derived cache index so completion and compact help no longer
  need the full API cache for normal interactive paths
- added opt-in CLI timing output with `NETLOOM_CLI_TIMING=1`
- replaced the old plugin-import-heavy interactive cache path with a
  lightweight core cache loader for completion and compact help
- delayed more runtime setup on trivial help and version paths
- updated `CACHE_PERFORMANCE_PLAN.md` with the completed Phase 1.5 status and
  current timing results

## Examples

```bash
NETLOOM_CLI_TIMING=1 netloom logs system-event ?
NETLOOM_CLI_TIMING=1 netloom policyelements role list ?
netloom cache update
```

## Notes

- installable man pages still come from `netloom/data/man/`
- current timing data shows cached help now lands around `15-20 ms`, with
  catalog loading itself around `3 ms`
- the remaining interactive bottleneck is now general startup/runtime setup,
  not cache parsing or plugin catalog import
- `netloom cache update` itself is not timed yet; that is the next measurement
  improvement
