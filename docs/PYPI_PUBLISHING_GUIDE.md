# Phase 7: PyPI Publishing Guide

**Date:** April 6, 2026
**Status:** Ready to publish
**Package:** rag-memory-plugin v1.0.0

---

## Prerequisites

### 1. PyPI Account
- Register at https://pypi.org/account/register/
- Confirm email address
- Enable 2FA (recommended)

### 2. API Token
1. Go to https://pypi.org/manage/account/token/
2. Create new token
3. Scope: "Entire account" (for first upload)
4. Copy token (starts with `pypi-...`)

**⚠️ IMPORTANT:** Save the token - you won't see it again!

---

## Build Package

### Option A: Using Virtual Environment (Recommended)

```bash
# Create venv
cd /tmp/rag-memory-plugin
python3 -m venv .venv
source .venv/bin/activate

# Install build tools
pip install build twine

# Build package
python3 -m build

# Output:
# * Creating build/...
# * Building sdist...
# * Built sdist: dist/rag_memory_plugin-1.0.0.tar.gz
# * Building wheel...
# * Built wheel: dist/rag_memory_plugin-1.0.0-py3-none-any.whl
```

### Option B: Using System Python (Not Recommended)

```bash
# Override PEP 668 (externally-managed)
pip install build twine --break-system-packages
python3 -m build
```

---

## Check Package

Before uploading, verify the package:

```bash
# Check metadata
twine check dist/*

# Expected output:
# Checking dist/rag_memory_plugin-1.0.0.tar.gz: PASSED
# Checking dist/rag_memory_plugin-1.0.0-py3-none-any.whl: PASSED
```

---

## Test on TestPyPI (Recommended)

### 1. Upload to TestPyPI

```bash
twine upload --repository testpypi dist/*
```

**Credentials:**
- Username: `__token__`
- Password: Your TestPyPI API token (get from https://test.pypi.org/manage/account/token/)

### 2. Install from TestPyPI

```bash
# Create test venv
python3 -m venv test-env
source test-env/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ rag-memory-plugin[neural]

# Test CLI
rag-memory --version
rag-memory doctor

# Test import
python3 -c "import rag_memory; print(rag_memory.__version__)"
```

### 3. Clean up test environment

```bash
deactivate
rm -rf test-env
```

---

## Publish to PyPI (Production)

### 1. Upload to PyPI

```bash
twine upload dist/*
```

**Credentials:**
- Username: `__token__`
- Password: Your PyPI API token

### 2. Verify on PyPI

Visit: https://pypi.org/project/rag-memory-plugin/

### 3. Install from PyPI

```bash
# Create fresh venv
python3 -m venv fresh-env
source fresh-env/bin/activate

# Install from PyPI
pip install rag-memory-plugin[neural]

# Test
rag-memory --version
rag-memory doctor
rag-memory search "test"
```

### 4. Clean up

```bash
deactivate
rm -rf fresh-env
```

---

## Troubleshooting

### Error: "403 Forbidden"

**Cause:** Invalid or expired token

**Solution:**
1. Create new API token at https://pypi.org/manage/account/token/
2. Use `__token__` as username
3. Paste full token as password

### Error: "File already exists"

**Cause:** Version already published

**Solution:**
1. Bump version in `pyproject.toml`:
   ```toml
   version = "1.0.1"
   ```
2. Bump version in `src/rag_memory/__init__.py`:
   ```python
   __version__ = "1.0.1"
   ```
3. Rebuild: `python3 -m build`
4. Upload: `twine upload dist/*`

### Error: "Package not found" after installation

**Cause:** Entry points not configured correctly

**Solution:**
1. Check `pyproject.toml` has entry points
2. Verify `tool.hatch.build.targets.wheel.packages` includes `src/rag_memory`
3. Rebuild and upload

### Error: "Module not found"

**Cause:** Package structure issue

**Solution:**
1. Check `src/rag_memory/__init__.py` exists
2. Verify `tool.hatch.build.targets.wheel.sources`
3. Test locally: `pip install -e .`

---

## Post-Publishing Checklist

- [ ] Package appears on PyPI
- [ ] Installation works: `pip install rag-memory-plugin[neural]`
- [ ] CLI works: `rag-memory --version`
- [ ] Import works: `import rag_memory`
- [ ] Doctor command works: `rag-memory doctor`
- [ ] Search works: `rag-memory search "test"`
- [ ] Update README with PyPI badge (already added)
- [ ] Update GitHub release notes
- [ ] Announce package (if desired)

---

## Current Package Status

**Version:** 1.0.0
**Name:** rag-memory-plugin
**Dependencies:**
- Core: 7 packages
- Neural extras: 3 packages

**Entry Points:**
- CLI: `rag-memory`
- Plugin: `hermes_agent.plugins`

**Files Ready:**
- `pyproject.toml` - Package metadata
- `README.md` - Documentation with badges
- `LICENSE` - MIT license
- `src/rag_memory/` - Package source

---

## Installation Commands (After Publishing)

### Basic (TF-IDF only)
```bash
pip install rag-memory-plugin
```

### Full (with Neural)
```bash
pip install rag-memory-plugin[neural]
```

### From Git (Alternative)
```bash
pip install "git+https://github.com/favouraka/rag-memory-plugin.git[neural]"
```

### Editable (Development)
```bash
git clone https://github.com/favouraka/rag-memory-plugin.git
cd rag-memory-plugin
pip install -e ".[neural]"
```

---

## Version Bumping (Future Releases)

### 1. Update version numbers

**pyproject.toml:**
```toml
[project]
name = "rag-memory-plugin"
version = "1.0.1"  # Bump this
```

**src/rag_memory/__init__.py:**
```python
__version__ = "1.0.1"  # Bump this
```

### 2. Commit and tag

```bash
git add pyproject.toml src/rag_memory/__init__.py
git commit -m "Bump version to 1.0.1"
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin main
git push origin v1.0.1
```

### 3. Build and publish

```bash
rm -rf dist/ build/
python3 -m build
twine upload dist/*
```

---

## Next Steps After Publishing

1. **Update Documentation**
   - Add PyPI installation instructions to README
   - Update badges (if needed)

2. **Create GitHub Release**
   - Already done (v1.0.0)

3. **Test on Fresh System**
   - Install on clean machine
   - Verify all features work

4. **Monitor Issues**
   - Watch GitHub issues for bug reports
   - Respond to user questions

5. **Plan v1.0.1**
   - Collect feedback
   - Fix bugs
   - Add requested features

---

## Estimated Time

- Build package: 1-2 minutes
- TestPyPI upload: 2-3 minutes
- TestPyPI verification: 5 minutes
- PyPI upload: 2-3 minutes
- Total: ~10-15 minutes

---

## Success Criteria

- [ ] Package builds without errors
- [ ] twine check passes
- [ ] TestPyPI upload succeeds
- [ ] TestPyPI installation works
- [ ] PyPI upload succeeds
- [ ] PyPI installation works
- [ ] All CLI commands work
- [ ] Import works
- [ ] Search functionality works

---

**Status:** Ready for PyPI publishing
**Next Step:** Build package and upload to TestPyPI
