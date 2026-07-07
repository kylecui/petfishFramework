# Release Checklist

> Run before every release tag. Prevents document drift and version inconsistencies.

## Pre-release checks

```bash
# 1. No stale version references
grep -R "v0\.1\b" README.md docs/ pyproject.toml src/
# Expected: only CHANGELOG historical entries

# 2. No "coming in" placeholders
grep -R "coming in" README.md docs/ examples/
# Expected: no output

# 3. Badge URL matches test count
grep "badge/tests" README.md
# Expected: current test count in both text and URL

# 4. api.md version matches release version
grep "authoritative reference" docs/api.md
# Expected: current version number

# 5. All tests pass
uv run pytest tests/ -q
# Expected: all passed

# 6. Ruff clean
uv run ruff check src/ tests/ examples/
# Expected: All checks passed
```

## Release process (Trusted Publishing — NO API TOKEN)

```bash
# 1. Bump version in pyproject.toml + src/petfishframework/__init__.py
# 2. Update CHANGELOG.md
# 3. Commit
git add -A && git commit -m "release: vX.Y.Z"

# 4. Push master
git push origin master

# 5. Tag (MUST start with 'v')
git tag vX.Y.Z
git push origin vX.Y.Z

# → GitHub Actions CI runs tests
# → GitHub Actions publish.yml builds + publishes via OIDC
# → PyPI receives the package with NO API TOKEN
# → Verify at https://pypi.org/project/petfishframework/
```

## Post-release checks

```bash
# 1. PyPI shows new version
curl -s https://pypi.org/pypi/petfishframework/json | python -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"

# 2. pip install works
pip install petfishframework==X.Y.Z

# 3. GitHub Actions both green
gh run list --repo kylecui/petfishFramework --limit 2
# Expected: CI success + Publish success
```

## NEVER

- ❌ Do NOT use twine (Trusted Publishing replaces it)
- ❌ Do NOT use API tokens (revoked; OIDC only)
- ❌ Do NOT tag without `v` prefix (workflow only triggers on `v*`)
- ❌ Do NOT skip the pre-release grep checks
