# Migration Guide: Old Installation → New Venv Location

**If you previously installed with the old method** (using `--user` or `~/.hermes-venv`), follow this guide to migrate to the new `~/.rag-memory` location.

## 📋 Check Your Current Installation

```bash
# Check if old venv exists
if [ -d ~/.hermes-venv ]; then
    echo "Old installation found: ~/.hermes-venv"
    ls -la ~/.hermes-venv/bin/ | grep rag-memory
fi

# Check if user-space installation exists
if pip3 show rag-memory-plugin &>/dev/null; then
    echo "User-space installation found"
    pip3 show rag-memory-plugin | grep Location
fi

# Check if PATH includes old location
if grep -q "hermes-venv" ~/.bashrc 2>/dev/null; then
    echo "PATH includes old location"
    grep "hermes-venv" ~/.bashrc
fi
```

## 🔄 Migration Steps

### Step 1: Remove Old Installation

**If you have old venv (~/.hermes-venv):**

```bash
# Deactivate if currently active
deactivate 2>/dev/null || true

# Remove old venv
rm -rf ~/.hermes-venv

# Remove from PATH
sed -i '/hermes-venv/d' ~/.bashrc
sed -i '/hermes-venv/d' ~/.zshrc 2>/dev/null || true
```

**If you have user-space installation:**

```bash
# Uninstall package
pip3 uninstall -y rag-memory-plugin

# Remove from PATH (if manually added)
sed -i '/rag-memory/d' ~/.bashrc 2>/dev/null || true
```

### Step 2: Backup Your Data (Optional)

**Your data is stored separately and won't be affected:**

```bash
# Backup database
cp ~/.hermes/plugins/rag-memory/rag_core.db \
   ~/.hermes/plugins/rag-memory/rag_core.db.backup.$(date +%Y%m%d)

# Backup configuration
cp ~/.hermes/plugins/rag-memory/config.yaml \
   ~/.hermes/plugins/rag-memory/config.yaml.backup.$(date +%Y%m%d)

# List backups
ls -lh ~/.hermes/plugins/rag-memory/backup* 2>/dev/null || true
```

### Step 3: Run New Installation Script

```bash
curl -sSL https://raw.githubusercontent.com/favouraka/rag-memory-plugin/main/install.sh | bash
```

**After installation completes:**

```bash
# Activate in current session
source ~/.bashrc    # or ~/.zshrc

# Verify installation
rag-memory --version
rag-memory doctor
```

### Step 4: Verify Data is Intact

```bash
# Check database
rag-memory status

# Run doctor to verify everything
rag-memory doctor

# Test search
rag-memory search "test"
```

## 📊 What Changes vs What Doesn't

### ✅ Changes (installation location)
- **OLD:** `~/.hermes-venv/` or user-space
- **NEW:** `~/.rag-memory/`

### ✅ Doesn't Change (data and config)
- **Database:** `~/.hermes/plugins/rag-memory/rag_core.db` ✅
- **Configuration:** `~/.hermes/plugins/rag-memory/config.yaml` ✅
- **Backups:** `~/.hermes/plugins/rag-memory/backups/` ✅
- **All your indexed data and memory** ✅

## 🧹 Clean Up (Optional)

After successful migration, you can remove backup files:

```bash
# Remove old backups
rm -f ~/.hermes/plugins/rag-memory/backup.*

# Keep the backups directory with your recent backups
ls -lh ~/.hermes/plugins/rag-memory/backups/
```

## ❓ Troubleshooting

### "Command not found" after installation

```bash
# Make sure you sourced the shell config
source ~/.bashrc    # or source ~/.zshrc

# Or restart your terminal
```

### Database not found error

```bash
# Check if data directory exists
ls -la ~/.hermes/plugins/rag-memory/

# If missing, run setup
rag-memory setup
```

### Permission denied errors

```bash
# Make sure ~/.rag-memory is owned by your user
sudo chown -R $USER:$USER ~/.rag-memory

# Or recreate virtual environment
rm -rf ~/.rag-memory
curl -sSL https://raw.githubusercontent.com/favouraka/rag-memory-plugin/main/install.sh | bash
```

## 🎯 Quick Migration Checklist

- [ ] Identified old installation method
- [ ] Removed old venv (~/.hermes-venv) or user-space installation
- [ ] Cleaned up PATH in ~/.bashrc or ~/.zshrc
- [ ] Backed up data (optional but recommended)
- [ ] Ran new installation script
- [ ] Sourced shell config: `source ~/.bashrc`
- [ ] Verified with: `rag-memory --version`
- [ ] Ran doctor: `rag-memory doctor`
- [ ] Tested search: `rag-memory search "test"`
- [ ] Verified data is intact

## 📞 Need Help?

If you encounter issues during migration:

1. Check the troubleshooting section above
2. Run `rag-memory doctor` for diagnostics
3. Open an issue: https://github.com/favouraka/rag-memory-plugin/issues
