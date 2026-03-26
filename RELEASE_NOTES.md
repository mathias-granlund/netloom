# netloom v1.9.10

This release focuses on the cache-update UX and measurement side of the
performance work by completing Phase 1.7 and making long `cache update`
runs visibly progress instead of looking stalled.

## Highlights

- added detailed timing output for `netloom cache update` under
  `NETLOOM_CLI_TIMING=1`
- added lightweight `[netloom progress]` reporting during `cache update`
- confirmed from real timing data that cache rebuild time is dominated by
  subdocument fetches rather than local JSON build/write work
- updated `CACHE_PERFORMANCE_PLAN.md` to mark Phase 1.7 complete and defer
  parallel rebuild work unless the current rebuild time becomes a practical
  pain point

## Examples

```bash
netloom cache update
NETLOOM_CLI_TIMING=1 netloom cache update
```

## Notes

- installable man pages still come from `netloom/data/man/`
- current timing data for cache rebuild shows total runtime around `23 s`, with
  subdocument fetches dominating the total time
- progress reporting is enabled by default for `cache update`, while timing
  stays opt-in behind `NETLOOM_CLI_TIMING=1`
