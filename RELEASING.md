# Releasing LMMock

Git tags are the release switch. Pushing `vX.Y.Z` runs `.github/workflows/release.yml` and creates:

- a wheel and source distribution;
- standalone archives for Linux, macOS, and Windows;
- `linux/amd64` and `linux/arm64` images on GHCR;
- a GitHub Release with generated notes and checksums.

## Release checklist

1. Set the same version in `pyproject.toml` and `src/lmmock/__init__.py`.
2. Update both READMEs if startup behavior changed.
3. Run `python -m pytest` and `python -m build`.
4. Commit, push `main`, then create and push the matching tag.
5. Confirm the Release workflow and test one archive plus the GHCR image.

```bash
git tag -a v0.1.0 -m "LMMock v0.1.0"
git push origin v0.1.0
```

PyPI publishing is disabled by default. To enable trusted publishing, add the repository variable `PUBLISH_PYPI=true`, create a `pypi` environment, and register this repository and workflow with PyPI. No PyPI token is stored in GitHub.
