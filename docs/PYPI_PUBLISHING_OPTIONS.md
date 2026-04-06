# PyPI Publishing Guide

**Date:** April 6, 2026
**Package:** rag-memory-plugin v1.0.0

---

## Current Status

✅ **Package Built Successfully**
- Wheel: `rag_memory_plugin-1.0.0-py3-none-any.whl` (50K)
- Source: `rag_memory_plugin-1.0.0.tar.gz` (47K)
- Location: `/tmp/rag-memory-plugin/dist/`

❌ **NOT on PyPI Yet**
- Needs API token for publishing
- Ready to publish when you are

---

## Publishing Options

### Option 1: TestPyPI (Recommended First Step)

**Benefits:**
- Safe testing environment
- Won't affect production PyPI
- Good for verification

**Steps:**

1. **Create TestPyPI Account**
   - URL: https://test.pypi.org/account/register/
   - Separate from production PyPI

2. **Create API Token**
   - URL: https://test.pypi.org/manage/account/token/
   - Scope: "Entire account" (for first publish)
   - Save token securely

3. **Publish**
   ```bash
   cd /tmp/rag-memory-plugin
   python3 -m twine upload --repository testpypi dist/* \
     --username __token__ \
     --password pypi-***
   ```

4. **Verify**
   ```bash
   # Install from TestPyPI
   pip install --index-url https://test.pypi.org/simple/ \
     rag-memory-plugin[neural]

   # Check installation
   rag-memory doctor
   ```

5. **URL After Publish**
   - Package: https://test.pypi.org/p/rag-memory-plugin
   - Installation: `pip install --index-url https://test.pypi.org/simple/ rag-memory-plugin[neural]`

---

### Option 2: Production PyPI (Live)

**Benefits:**
- Publicly available
- Permanent publication
- Simple installation: `pip install rag-memory-plugin[neural]`

**Steps:**

1. **Create PyPI Account** (if you don't have one)
   - URL: https://pypi.org/account/register/
   - Verify email address

2. **Enable 2FA** (Required for publishing)
   - URL: https://pypi.org/manage/account/two-factor/
   - Use app-based 2FA (TOTP) or WebAuthn

3. **Create API Token**
   - URL: https://pypi.org/manage/account/token/
   - Token name: "rag-memory-plugin" or similar
   - Scope: "Entire account" (for first publish)
   - **IMPORTANT:** Copy token immediately (only shown once!)

4. **Publish**
   ```bash
   cd /tmp/rag-memory-plugin
   python3 -m twine upload dist/* \
     --username __token__ \
     --password pypi-***

   # Or use token directly (replace *** with your token)
   python3 -m twine upload dist/* \
     --username __token__ \
     --password pypi-***
   ```

5. **Verify**
   ```bash
   # Install from PyPI
   pip install rag-memory-plugin[neural]

   # Check installation
   rag-memory doctor
   ```

6. **URL After Publish**
   - Package: https://pypi.org/p/rag-memory-plugin
   - Installation: `pip install rag-memory-plugin[neural]`

---

### Option 3: Skip For Now

**Install from GitHub:**

```bash
# Install directly from GitHub
pip install git+https://github.com/favouraka/rag-memory-plugin.git

# With neural dependencies
pip install git+https://github.com/favouraka/rag-memory-plugin.git[neural]

# Or install in editable mode
git clone https://github.com/favouraka/rag-memory-plugin.git
cd rag-memory-plugin
pip install -e ".[neural]"
```

**Benefits:**
- No PyPI setup required
- Always installs latest version
- Good for development

**Drawbacks:**
- Requires git
- Slower installation
- Not as discoverable

---

## Verification After Publishing

Once published, verify the installation:

```bash
# Basic installation
pip install rag-memory-plugin[neural]

# Check installation
python3 -c "from rag_memory import RAGCore; print('✓ Imported successfully')"

# Check CLI
rag-memory doctor

# Check plugin
rag-memory --help
```

---

## Package Metadata

**Name:** rag-memory-plugin
**Version:** 1.0.0
**Author:** Clawford Orji
**License:** MIT
**Python:** 3.10+
**Dependencies:**
- pydantic>=2.0
- pyyaml>=6.0
- click>=8.0
- rich>=13.0
- sqlite-vec>=0.1.0
- scikit-learn>=0.24.0
- numpy>=1.24.0

**Optional Dependencies:**
- neural: sentence-transformers>=2.2.0
- dev: pytest, pytest-cov, ruff, mypy

---

## Installation Examples

After publishing to PyPI:

```bash
# Basic (TF-IDF only)
pip install rag-memory-plugin

# Full (with Neural)
pip install rag-memory-plugin[neural]

# Development
pip install rag-memory-plugin[dev]

# All extras
pip install rag-memory-plugin[all]
```

---

## Next Steps

**If you choose to publish:**
1. Create PyPI/TestPyPI account
2. Generate API token
3. Run the publish command
4. Verify installation

**If you choose to skip:**
1. Document installation from GitHub
2. Add to README.md installation section
3. Consider publishing later

---

**Recommendation:** Start with TestPyPI to verify everything works, then publish to production PyPI.

---

**Documentation:** https://github.com/favouraka/rag-memory-plugin
**Status:** Built and ready to publish ✅
