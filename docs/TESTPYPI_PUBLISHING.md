# TestPyPI Publishing Guide

**Package:** rag-memory-plugin v1.0.0
**Goal:** Publish to TestPyPI (safe testing environment)

---

## Step 1: Create TestPyPI Account

**URL:** https://test.pypi.org/account/register/

1. Visit https://test.pypi.org/account/register/
2. Create a new account (separate from production PyPI)
3. Verify your email address
4. Log in to TestPyPI

**Note:** TestPyPI is completely separate from production PyPI. You need a separate account.

---

## Step 2: Enable 2FA (Optional but Recommended)

**URL:** https://test.pypi.org/manage/account/two-factor/

TestPyPI doesn't require 2FA, but it's good practice if you plan to publish to production PyPI later.

---

## Step 3: Create API Token

**URL:** https://test.pypi.org/manage/account/token/

1. Visit https://test.pypi.org/manage/account/token/
2. Click "Add API token"
3. Token name: `rag-memory-plugin` (or any descriptive name)
4. Scope: "Entire account" (recommended for first publish)
   - Alternatively: "Limit to project: rag-memory-plugin" (after first publish)
5. Click "Add token"
6. **IMPORTANT:** Copy the token immediately!
   - Format: `pypi-...` (starts with "pypi-")
   - Only shown once!
   - Save it securely

**Example token:** `pypi-abc123def456...`

---

## Step 4: Publish Package

Once you have your token, run the following command:

```bash
cd /tmp/rag-memory-plugin
python3 -m twine upload --repository testpypi dist/* \
  --username __token__ \
  --password YOUR_TOKEN_HERE
```

**Replace:** `YOUR_TOKEN_HERE` with your actual TestPyPI token

**Example:**
```bash
python3 -m twine upload --repository testpypi dist/* \
  --username __token__ \
  --password pypi-abc123def456...
```

---

## Step 5: Verify Upload

After successful upload, verify here:
- **Package:** https://test.pypi.org/p/rag-memory-plugin
- **Project:** https://test.pypi.org/project/rag-memory-plugin/

You should see:
- Version: 1.0.0
- Description, author, license
- Download files (.whl and .tar.gz)

---

## Step 6: Test Installation

Install from TestPyPI to verify everything works:

```bash
# Uninstall any existing version first
pip uninstall -y rag-memory-plugin

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  rag-memory-plugin[neural]

# Verify installation
rag-memory doctor

# Check import
python3 -c "from rag_memory import RAGCore; print('✓ Import successful')"
```

**Note:** The `--extra-index-url https://pypi.org/simple/` is needed because TestPyPI doesn't have all dependencies (like sentence-transformers), so it falls back to production PyPI for those.

---

## Common Issues & Solutions

### Issue: "403 Forbidden" or "Invalid or missing authentication credentials"

**Solution:** Check that:
- Token starts with `pypi-`
- No extra spaces in token
- Token has "Entire account" scope

### Issue: "409 Conflict - Project already exists"

**Solution:** This means the package name is taken on TestPyPI. You can either:
- Upload a new version (bump version in pyproject.toml)
- Or use a different package name

### Issue: "400 Bad Request - File already exists"

**Solution:** The version was already uploaded. Either:
- Bump the version in `pyproject.toml`
- Or skip if you just want to test

### Issue: "No module named 'sentence-transformers'"

**Solution:** Make sure to use the extra index URL:
```bash
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  rag-memory-plugin[neural]
```

---

## What Happens After Success?

Once successfully published to TestPyPI:

1. **Installation works:**
   ```bash
   pip install --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple/ \
     rag-memory-plugin[neural]
   ```

2. **Package is discoverable:**
   - https://test.pypi.org/p/rag-memory-plugin

3. **Next step:** Publish to production PyPI (optional)
   - Similar process with production PyPI token
   - Command: `python3 -m twine upload dist/* --username __token__ --password PROD_TOKEN`

---

## Quick Reference

**TestPyPI URLs:**
- Register: https://test.pypi.org/account/register/
- API Token: https://test.pypi.org/manage/account/token/
- Package: https://test.pypi.org/p/rag-memory-plugin

**Publish Command:**
```bash
cd /tmp/rag-memory-plugin
python3 -m twine upload --repository testpypi dist/* \
  --username __token__ \
  --password YOUR_TOKEN_HERE
```

**Install Command:**
```bash
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  rag-memory-plugin[neural]
```

---

**Ready to publish?**

Once you have your TestPyPI API token, let me know and I'll run the publish command for you!

Just say: "I have the token" and provide it (or paste it directly in the command).

---

**Documentation:** https://github.com/favouraka/rag-memory-plugin
**Status:** Ready to publish to TestPyPI ✅
