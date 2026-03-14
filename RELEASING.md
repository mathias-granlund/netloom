# Releasing netloom

This project publishes the `netloom-tool` package to PyPI and exposes both the
`netloom` and `arapy` CLI commands during the current rename transition.

## One-time setup

1. Create the `netloom-tool` project on PyPI.
2. In PyPI, configure a Trusted Publisher for:
   - owner: `mathias-granlund`
   - repository: `netloom`
   - workflow: `package.yml`
   - environment: `pypi`
3. In GitHub, make sure the `pypi` environment exists for this repository.

## Pre-release checks

Run locally before tagging:

```bash
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
pytest -q
python -m build
python -m twine check dist/*
python -m pip install --force-reinstall dist/*.whl
netloom --version
arapy --version
netloom-install-manpage --print-path
```

## Publish flow

1. Update versioned files as needed.
2. Commit the release changes.
3. Create and push the release tag:

```bash
git push
git push origin vX.Y.Z
```

On a pushed `v*` tag, GitHub Actions will:

1. run the test matrix
2. build the wheel and sdist
3. validate metadata with `twine check`
4. smoke-test the installed wheel
5. publish `dist/*` to PyPI using Trusted Publishing

## Notes

- The internal Python package name remains `arapy` for now.
- Environment variables and config directories still use the `ARAPY_*` /
  `~/.config/arapy/` naming during the compatibility period.
