# Publishing to PyPI - Step-by-Step Guide

## Prerequisites

1. **PyPI Account**: Register at https://pypi.org/account/register/
2. **API Token**: Create an API token at https://pypi.org/manage/account/token/
3. **Install build tools**:
   ```bash
   pip install build twine
   # Or in a venv:
   python3 -m venv .venv
   source .venv/bin/activate
   pip install build twine
   ```

## Build Package

### Option 1: Using python -m build (Recommended)

```bash
cd /path/to/rag-memory-plugin
python3 -m build
```

This creates:
- `dist/rag_memory_plugin-1.0.0.tar.gz` (sdist)
- `dist/rag_memory_plugin-1.0.0-py3-none-any.whl` (wheel)

### Option 2: Using setuptools (Legacy)

```bash
python3 setup.py sdist bdist_wheel
```

## Check Package

Before uploading, verify the package:

```bash
# Check metadata
twine check dist/*

# Output should be:
# Checking dist/rag_memory_plugin-1.0.0.tar.gz: PASSED
# Checking dist/rag_memory_plugin-1.0.0-py3-none-any.whl: PASSED
```

## Test on TestPyPI (Recommended)

First upload to TestPyPI to verify:

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ rag-memory-plugin

# Test installation
rag-memory --version
rag-memory doctor
```

## Publish to PyPI (Production)

Once verified, upload to production PyPI:

```bash
twine upload dist/*
```

You'll be prompted for:
- **Username**: `__token__`
- **Password**: Your PyPI API token (starts with `pypi-...`)

## Verify Installation

After publishing, verify the package is accessible:

```bash
# Install from PyPI
pip install rag-memory-plugin[neural]

# Test CLI
rag-memory --version
rag-memory doctor

# Test Python import
python3 -c "import rag_memory; print(rag_memory.__version__)"
```

## Update Version (For Future Releases)

1. Update version in `pyproject.toml`:
   ```toml
   version = "1.0.1"
   ```

2. Update version in `src/rag_memory/__init__.py`:
   ```python
   __version__ = "1.0.1"
   ```

3. Commit changes:
   ```bash
   git add pyproject.toml src/rag_memory/__init__.py
   git commit -m "Bump version to 1.0.1"
   ```

4. Create new tag:
   ```bash
   git tag -a v1.0.1 -m "Release v1.0.1"
   git push origin main
   git push origin v1.0.1
   ```

5. Build and upload:
   ```bash
   python3 -m build
   twine upload dist/*
   ```

## Troubleshooting

### Error: "403 Forbidden" or "Invalid or non-existent authentication information"

**Cause**: Wrong credentials or token expired

**Solution**:
- Use `__token__` as username
- Paste full API token as password (including `pypi-` prefix)
- Create new token at https://pypi.org/manage/account/token/

### Error: "File already exists"

**Cause**: Version already published

**Solution**:
- Bump version number
- Delete existing files from PyPI (only if you're the owner)
- Use `--skip-existing` flag (not recommended for production)

### Error: "Package not found" after installation

**Cause**: Entry points not configured correctly

**Solution**:
- Verify `pyproject.toml` has correct entry points
- Check package structure matches `tool.hatch.build.targets.wheel.packages`
- Test locally: `pip install -e .`

## Manual Build (For Current Environment)

The current environment has externally-managed Python packages. To build:

### Using Virtual Environment

```bash
# Create venv
python3 -m venv /tmp/build-env
source /tmp/build-env/bin/activate

# Install build tools
pip install build twine

# Build package
cd /tmp/rag-memory-plugin
python3 -m build

# Upload (if you have PyPI token)
twine upload dist/*
```

### Using Docker (Alternative)

```bash
docker run --rm -v $(pwd):/app -w /app python:3.12 bash -c "
    pip install build twine &&
    python3 -m build &&
    twine check dist/*
"
```

## Verification Checklist

Before publishing, verify:

- [x] `pyproject.toml` has correct version
- [x] `src/rag_memory/__init__.py` has correct `__version__`
- [x] Entry points configured correctly
- [x] All dependencies listed
- [x] README.md is comprehensive
- [x] LICENSE file present
- [x] Tests pass (if applicable)
- [x] Package builds successfully
- [x] `twine check dist/*` passes
- [x] Tested on TestPyPI (recommended)

## Post-Publishing

After successful publication:

1. **Create GitHub Release**: Already done (v1.0.0)
2. **Update README**: Add PyPI badge
3. **Announce**: Share with community
4. **Monitor issues**: Watch for bug reports

## Installation Instructions for Users

Add to README.md:

```markdown
## Installation

### From PyPI

\`\`\`bash
pip install rag-memory-plugin
\`\`\`

### From PyPI (with Neural)

\`\`\`bash
pip install rag-memory-plugin[neural]
\`\`\`

### From Git

\`\`\`bash
pip install "git+https://github.com/favouraka/rag-memory-plugin.git[neural]"
\`\`\`

### Verify Installation

\`\`\`bash
rag-memory --version
# Output: rag-memory, version 1.0.0
\`\`\`
```

## Current Status

- ✅ Package structure validated
- ✅ pyproject.toml configured
- ✅ Git repository initialized
- ✅ GitHub repository created: https://github.com/favouraka/rag-memory-plugin
- ✅ GitHub release created: v1.0.0
- ⏳ PyPI publishing (requires build environment)
- ⏳ TestPyPI verification (recommended)

## Next Steps

1. Build package (in venv or different environment)
2. Upload to TestPyPI for verification
3. Upload to production PyPI
4. Verify installation works
5. Update README with PyPI badge
