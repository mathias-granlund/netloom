# netloom v1.10.2

This release rounds out the help and documentation work with clearer module
descriptions and generated installable manpages.

## Highlights

- added short vendor-style descriptions for the ClearPass API modules in
  top-level `--help` output and cached interactive help
- made the markdown manpages under `man/` the single authoring source and
  added `netloom.generate_manpages` / `netloom-generate-manpages` to build and
  check the bundled installable manpages
- refreshed the shared and ClearPass manpages to document canonical full
  service names, vendor-style `?` help behavior, and privilege-aware command
  visibility
- replaced hard-coded example profile names with generic placeholders such as
  `<profile>`, `<source-profile>`, and `<target-profile>`

## Examples

```bash
python -m netloom.generate_manpages
python -m netloom.generate_manpages --check
netloom --help
```

## Notes

- the markdown manpages in `man/` are now the source of truth for the bundled
  installable manpages in `netloom/data/man/`
- the privilege-aware visible catalog remains the source of truth for
  user-facing command lists
