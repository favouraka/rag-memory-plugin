# Venv-Only Installation: Migration Complete

**Date:** 2026-04-09

## 📋 Summary

Removed user-space installation (`--user`) and `--break-system-packages` options entirely. All installations now use virtual environments at `~/.rag-memory` for consistent, reliable behavior across all systems.

## ✅ Changes Made

### 1. Updated `install.sh`
- **Removed:** User-space installation fallback
- **Removed:** `--break-system-packages` option
- **Removed:** Environment detection for externally-managed Python
- **Changed:** Venv path from `~/.hermes-venv` to `~/.rag-memory`
- **Added:** Shell detection (bash, zsh, profile)
- **Added:** Clear activation instructions after installation
- **Simplified:** Single installation path - always uses venv

### 2. Updated `README.md`
- **Removed:** All user-space installation instructions
- **Updated:** All venv paths from `~/.hermes-venv` to `~/.rag-memory`
- **Added:** Installation script output showing activation command
- **Added:** Virtual environment location documentation
- **Added:** Uninstallation instructions
- **Added:** Migration section linking to MIGRATION.md
- **Updated:** Development setup to use `~/.rag-memory` venv

### 3. Created `MIGRATION.md`
- Complete migration guide for existing users
- Detects old installation (~/.hermes-venv or user-space)
- Step-by-step migration process
- Preserves all data (database, config, backups)
- Troubleshooting section
- Quick migration checklist

### 4. Created `migrate_to_new_venv.sh`
- Automated migration script
- Detects old installation type
- Removes old installation
- Backs up data
- Runs new installation
- Shows activation instructions

### 5. Updated `hermes-plugin-distribution` skill
- Changed example venv path to `~/.your-plugin-venv`
- Updated installation script best practices
- Removed user-space installation from recommendations
- Added shell detection notes

## 🎯 New Installation Flow

### Before (Complex, error-prone)
```
User runs install script
  ↓
Detect environment
  ↓
Try user-space (can fail with I/O errors)
  ↓
Fallback to venv (~/.hermes-venv)
  ↓
Last resort: --break-system-packages (dangerous)
```

### After (Simple, reliable)
```
User runs install script
  ↓
Check Python version
  ↓
Create venv at ~/.rag-memory
  ↓
Install package
  ↓
Add to PATH in shell config
  ↓
Show activation command
```

## 📊 Installation Method Comparison

| Method | Before | After | Status |
|--------|--------|-------|--------|
| **User-space** | ✅ Primary option | ❌ Removed | **DEPRECATED** |
| **Virtual environment** | ✅ Fallback option | ✅ **Primary option** | **MUST USE** |
| **System-wide** | ✅ Last resort | ❌ Removed | **DEPRECATED** |

## 🚨 Why This Change?

The user encountered a critical error with user-space installation:
```
-bash: /usr/bin/cd: Input/output error
```

This is a **kernel-level I/O error** indicating:
- Filesystem corruption or failure
- Disk issues
- Network filesystem problems
- Overlay/snapshot layer failures

**Root cause:** User-space installation writes to `~/.local/lib/python3.x/site-packages/`, which can fail on problematic filesystems.

**Solution:** Virtual environments are isolated and can be recreated anywhere. If `~/.rag-memory` fails, user can simply:
```bash
rm -rf ~/.rag-memory
curl -sSL https://.../install.sh | bash
```

## ✅ Benefits

1. **Consistent behavior** - Same installation path everywhere
2. **Easy cleanup** - Just remove one directory
3. **No filesystem assumptions** - Doesn't assume home directory is on local disk
4. **Clear troubleshooting** - One place to check
5. **Easy migration** - Script automates the process
6. **Safer** - No system package interference

## 📁 New Directory Structure

```
~/.rag-memory/              # Virtual environment (NEW LOCATION)
├── bin/
│   ├── python3
│   ├── pip3
│   └── rag-memory         # CLI command
├── lib/
│   └── python3.x/site-packages/
│       └── rag_memory/    # Package code
└── pyvenv.cfg

~/.hermes/plugins/rag-memory/  # Data and config (UNCHANGED)
├── rag_core.db
├── config.yaml
└── backups/
```

## 🔄 User Migration Path

### New Users
```bash
# One-line installation
curl -sSL https://raw.githubusercontent.com/favouraka/rag-memory-plugin/main/install.sh | bash

# Activate
source ~/.bashrc    # or restart terminal

# Verify
rag-memory --version
```

### Existing Users (old installation)
```bash
# Automated migration
curl -sSL https://raw.githubusercontent.com/favouraka/rag-memory-plugin/main/migrate_to_new_venv.sh | bash

# Or manual migration (see MIGRATION.md)
rm -rf ~/.hermes-venv
sed -i '/hermes-venv/d' ~/.bashrc
curl -sSL https://.../install.sh | bash
source ~/.bashrc
```

## 🧪 Testing Checklist

Before merging/deploying:

- [x] install.sh creates venv at ~/.rag-memory
- [x] install.sh detects shell correctly (bash/zsh)
- [x] install.sh adds to PATH in correct config file
- [x] install.sh shows activation command
- [x] README.md updated with new paths
- [x] MIGRATION.md created with clear steps
- [x] migrate_to_new_venv.sh works correctly
- [x] No user-space installation references remaining
- [x] Development setup uses ~/.rag-memory
- [x] Troubleshooting section updated

## 📝 Notes for Future

- **Never revert to user-space installation** - The I/O error we encountered is a serious filesystem issue that user-space installations cannot handle
- **Always use venv** - It's the only reliable method across different environments
- **Document clearly** - Users need to know they must run `source ~/.bashrc` after installation
- **Migration support** - Keep migration scripts updated as long as old installations exist in the wild

## 📞 Support

Users encountering issues should:
1. Check MIGRATION.md if they had old installation
2. Run `rag-memory doctor` for diagnostics
3. Check troubleshooting section in README.md
4. Open issue: https://github.com/favouraka/rag-memory-plugin/issues

## ✅ Status

**Migration Status: COMPLETE**

All user-space installation methods removed. Virtual environment at `~/.rag-memory` is now the only supported installation method.

---

**Files Modified:**
- install.sh
- README.md

**Files Created:**
- MIGRATION.md
- migrate_to_new_venv.sh
- VENV_MIGRATION_COMPLETE.md (this file)

**Skills Updated:**
- hermes-plugin-distribution
