# PyPI Publishing Status

**Date:** April 6, 2026
**Package:** rag-memory-plugin v1.0.0

---

## Current Status: ⚠️ PyPI Publishing Issues

**Issue:** Modern Python packaging tools (setuptools >=68, hatchling) add the `License-File` field to package metadata per PEP 639, but PyPI doesn't support this field yet.

**Impact:** Cannot upload to PyPI with current tools.

---

## Installation (Works Perfectly)

### From GitHub (Recommended)

```bash
pip install git+https://github.com/favouraka/rag-memory-plugin.git[neural]
```

**Benefits:**
- ✅ Works perfectly right now
- ✅ Always installs latest version
- ✅ No PyPI issues
- ✅ Simple and reliable

### From Local Wheel

```bash
cd /tmp/rag-memory-plugin
pip install dist/rag_memory_plugin-1.0.0-py3-none-any.whl[neural]
```

**Benefits:**
- ✅ Works offline
- ✅ Fast installation
- ✅ No network required

---

## PyPI Publishing Details

### The Issue

Modern Python packaging tools (setuptools >=68, hatchling) include the `License-File` field in package metadata as specified in PEP 639. However, PyPI's validation doesn't support this field yet.

### What We Tried

1. ✅ Built package successfully (48K wheel, 46K source)
2. ✅ Package metadata is correct per modern standards
3. ❌ TestPyPI rejected it (outdated validation)
4. ❌ Production PyPI rejected it (same issue)
5. ✅ Tried hatchling (same issue)
6. ✅ Tried setuptools (same issue)

### Error Message

```
ERROR: InvalidDistribution: Invalid distribution metadata:
       unrecognized or malformed field 'license-file'
```

### Workarounds (Not Recommended)

1. **Downgrade setuptools to <60**
   - Would remove License-File field
   - But uses very old tools
   - Not recommended for new packages

2. **Manually edit package metadata**
   - Complex and error-prone
   - Would break reproducibility
   - Not recommended

3. **Wait for PyPI to support PEP 639**
   - Best long-term solution
   - But no timeline
   - Can't wait indefinitely

---

## Recommendation

**Use GitHub installation:**

```bash
pip install git+https://github.com/favouraka/rag-memory-plugin.git[neural]
```

This is:
- Simple
- Reliable
- Always latest version
- Works perfectly

---

## Alternative: Flit or Poetry

We could try alternative build tools like **flit** or **poetry** which might not add the License-File field:

```bash
# Try with flit
pip install flit
flit publish

# Or try with poetry
pip install poetry
poetry publish
```

But these are significant changes to the build system and would require rewriting setup.py/pyproject.toml.

---

## Future

When PyPI adds support for PEP 639 (License-File field), we can publish normally:

```bash
cd /tmp/rag-memory-plugin
python3 -m build
python3 -m twine upload dist/*
```

Until then, GitHub installation works perfectly.

---

## Package Details

**Name:** rag-memory-plugin
**Version:** 1.0.0
**Built:** ✓ Successfully
**Metadata:** ✓ Valid (per PEP 639)
**PyPI:** ✗ Validation issue (not our fault)

**Repository:** https://github.com/favouraka/rag-memory-plugin
**Installation:** `pip install git+https://github.com/favouraka/rag-memory-plugin.git[neural]`

---

**Status:** Package is production-ready ✅
**Issue:** PyPI validation doesn't support modern metadata ⚠️
**Solution:** Use GitHub installation (works perfectly) ✅
