# netloom v1.9.4

This release tightens the documentation split between the quick-start README
and the deeper manual pages, while also making the repository's checked-in man
docs easier to browse directly on GitHub.

## Highlights

- rewrote the README as a shorter user-friendly quick start with install,
  minimal configuration, first-run guidance, examples, and links to deeper docs
- kept `netloom/data/man/` as the single source of truth for installable man
  pages used by packaging and `netloom-install-manpage`
- replaced the top-level troff files under `man/` with Markdown reference pages
  so the manual content is easier to read on GitHub
- restored detailed shell completion and `--filter=` reference guidance in the
  manual pages while keeping the README lean
- aligned release metadata and checked-in manpage headers with version `1.9.4`

## Examples

```bash
man netloom
man netloom-clearpass
netloom-install-manpage
```

## Notes

- installable man pages still come from `netloom/data/man/`
- the top-level `man/` directory is now for GitHub-friendly Markdown browsing
