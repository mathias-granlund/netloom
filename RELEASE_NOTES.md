# netloom v1.9.7

This release focuses on interactive CLI performance work and the follow-up
planning around completion and dynamic help latency.

## Highlights

- added a compact derived cache index so completion and compact help no longer
  need the full API cache for normal interactive paths
- added opt-in CLI timing output with `NETLOOM_CLI_TIMING=1`
- documented the current cache-performance status and next optimization step in
  `CACHE_PERFORMANCE_PLAN.md`
- cleaned up the timing configuration so only `NETLOOM_CLI_TIMING` is supported

## Examples

```bash
NETLOOM_CLI_TIMING=1 netloom logs system-event ?
NETLOOM_CLI_TIMING=1 netloom policyelements role list ?
netloom cache update
```

## Notes

- installable man pages still come from `netloom/data/man/`
- current timing data shows the remaining interactive bottleneck is plugin
  loading, not cache parsing
- `netloom cache update` itself is not timed yet; that is the next measurement
  improvement
