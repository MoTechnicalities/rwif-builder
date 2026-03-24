# Release Checklist

## Pre-Release Gates

1. Confirm `git status --short` is empty.
2. Run the local smoke path:
   - `python -m unittest tests.test_diff_patch tests.test_cli_init`
3. Build source and wheel distributions:
    - `python -m build`
4. Build a sample artifact and validate it.
5. Re-read [docs/RWIF_DEEP_DIVE.md](docs/RWIF_DEEP_DIVE.md) and [README.md](README.md) so public claims still match reality.
6. Confirm the default hashing path works without optional transformer dependencies.
7. If the release mentions transformer support, confirm the optional install path is documented correctly.

## Tag Preparation

1. Update version numbers if needed.
2. Review the README quickstart.
3. Review `docs/EMBEDDING_BACKENDS.md` and `docs/RWIF_DEEP_DIVE.md` for wording drift.
4. Draft release notes from the actual shipped changes.

## Remote Setup

```bash
git remote add origin <github-url>
git push -u origin main
```

## Suggested First Public Positioning

- `rwif-builder` is the forge for RWIF artifacts.
- It turns raw text into portable semantic-memory stores.
- It explains how Analog Wave Memory is packed, not just how it is served.
