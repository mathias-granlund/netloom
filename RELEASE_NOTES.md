# netloom v1.9.5

This release keeps package metadata aligned while updating the GitHub Actions
workflows for the upcoming Node 24 transition on hosted runners.

## Highlights

- updated the package workflow to action versions aligned with the Node 24
  migration path on GitHub-hosted runners
- updated the Pages workflow checkout step to the Node 24-ready checkout action
- aligned package metadata, release notes, README badge, and checked-in manpage
  headers with version `1.9.5`

## Examples

```bash
gh workflow run package.yml
gh run watch
```

## Notes

- the Node.js 20 warning from `checkout` and `setup-python` should no longer
  apply to the upgraded workflow actions
- installable man pages still come from `netloom/data/man/`
