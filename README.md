# RAG Memory Plugin for Hermes Agent

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/github-favouraka%2Frag--memory--plugin-blue.svg)](https://github.com/favouraka/rag-memory-plugin)
[![Status](https://img.shields.io/badge/status-production--ready-success.svg)](https://github.com/favouraka/rag-memory-plugin)

**Production-grade Retrieval-Augmented Generation memory system** with hybrid TF-IDF + Neural search, automatic context injection, interactive setup, and comprehensive backup/recovery capabilities.

## ✨ Features

- 🔍 **Hybrid Search**: TF-IDF + Neural retrieval with sqlite-vec and sentence-transformers
- 🪝 **Auto-Capture**: Hooks inject relevant context before LLM calls, capture responses after
- 🏷️ **Namespace Isolation**: Separate memory spaces for conversations, files, projects
- ⚡ **Performance**: Query caching, connection pooling, lazy loading (<2ms search time)
- 🔧 **Zero-Config**: Interactive setup wizard, works out of the box
- 💾 **Backup Management**: Create, list, restore, and delete database backups
- 🚑 **Auto-Recovery**: Automatic database corruption detection and recovery
- 📝 **File Indexing**: Index files and directories for semantic search
- 🔄 **Migration**: Migrate data from legacy installations or other databases
- 🛠️ **20+ CLI Commands**: Comprehensive command-line interface
- 📦 **Pip Installable**: Standard Python package with entry points

## 🚀 Installation

### Method 1: Installation Script (Recommended ⭐)

**Easiest method - automatically sets up virtual environment:**

```bash
curl -sSL https://raw.githubusercontent.com/favouraka/rag-memory-plugin/main/install.sh | bash
```

**What it does:**
- Checks Python version (requires 3.10+)
- Creates virtual environment at `~/.rag-memory`
- Installs package with neural search
- Adds rag-memory to PATH in your shell config
- Shows activation command

**After installation:**
```bash
# Activate in current session
source ~/.bashrc    # or ~/.zshrc for zsh users

# Or restart your terminal
```

### Method 2: Manual Installation with Virtual Environment

**Create venv and install:**

```bash
# Create virtual environment
python3 -m venv ~/.rag-memory
source ~/.rag-memory/bin/activate

# Install with neural search
pip install git+https://github.com/favouraka/rag-memory-plugin.git#egg=rag-memory-plugin[neural]

# Add to PATH permanently
echo 'export PATH="$HOME/.rag-memory/bin:$PATH"' >> ~/.bashrc

# Deactivate when done
deactivate
```

**After installation:**
```bash
# Activate in current session
source ~/.bashrc

# Or restart your terminal
```

### Method 3: Clone and Install (Development)

```bash
git clone https://github.com/favouraka/rag-memory-plugin.git
cd rag-memory-plugin
python3 -m venv ~/.rag-memory
source ~/.rag-memory/bin/activate
pip install -e ".[neural]"
```

---

## 📚 Quick Start

### 1. Run Setup Wizard

```bash
rag-memory setup
```

The setup wizard will:
- ✅ Create database directory
- ✅ Initialize SQLite database
- ✅ Check dependencies (sqlite-vec, neural model)
- ✅ Create configuration file
- ✅ Guide you through optional features

**Non-interactive mode:**
```bash
rag-memory setup --skip-prompts
```

### 2. Verify Installation

```bash
rag-memory doctor
rag-memory status
```

### 3. Index Your Files (Optional)

```bash
# Index a single file
rag-memory index ~/Documents/notes.md --namespace personal

# Index a directory
rag-memory index ~/Projects/ --namespace work

# Index Hermes memory files
rag-memory index-files
```

### 4. Search Your Memory

```bash
rag-memory search "what did we work on yesterday?"
rag-memory search "AI agent" --namespace work --limit 5
```

---

## 💻 Command Reference

### Setup & Installation

```bash
# Interactive setup
rag-memory setup [--skip-prompts] [--reinit] [--sqlite-vec] [--neural]

# Install neural dependencies
rag-memory install neural [--force]
```

### Diagnostics

```bash
# Full health check
rag-memory doctor

# Quick status check
rag-memory status [--json] [--quiet]

# Exit codes: 0=healthy, 1=warning, 2=error
```

### Configuration

```bash
# View configuration
rag-memory config show

# Edit in $EDITOR
rag-memory config edit

# Set value
rag-memory config set database.path /custom/path
rag-memory config set search.max_results 20

# Reset to defaults
rag-memory config reset

# Validate configuration
rag-memory config validate
```

### Search & Index

```bash
# Search memory
rag-memory search "query" [--namespace] [--limit]

# Index file or directory
rag-memory index <path> [--namespace] [--chunk-size] [--force]

# Index Hermes files
rag-memory index-files [--pattern] [--chunk-size] [--force]
```

### Backup Management

```bash
# Create backup
rag-memory backup create [--description "Before changes"]

# List backups
rag-memory backup list [--json]

# Restore from backup
rag-memory backup restore <backup_file> [--force] [--backup-current]

# Delete backup
rag-memory backup delete <backup_file> [--force]
```

### Recovery & Reset

```bash
# Auto-recovery from corruption
rag-memory recover [--backup-corrupted] [--from-backup <file>]

# Reset database (with backup)
rag-memory reset [--force] [--no-backup] [--keep-config]
```

### Migration

```bash
# Migrate from database
rag-memory migrate <path> [--auto] [--backup]

# Migrate from legacy ~/rag-system
rag-memory migrate --auto
```

### Import/Export

```bash
# Export to JSON
rag-memory export output.json [--namespace]

# Import from JSON
rag-memory import-data input.json
```

---

## ⚙️ Configuration

Configuration file: `~/.hermes/plugins/rag-memory/config.yaml`

```yaml
database:
  path: ~/.hermes/plugins/rag-memory/rag_core.db
  backup_enabled: true
  backup_path: ~/.hermes/plugins/rag-memory/backups/

search:
  max_results: 10
  default_mode: hybrid    # tfidf | neural | hybrid
  threshold: 0.5

neural:
  enabled: true
  model: sentence-transformers/all-MiniLM-L6-v2
  cache_dir: ~/.cache/torch/sentence_transformers/

indexing:
  auto_index: true
  chunk_size: 500
  chunk_overlap: 50
```

### Hermes Plugin Configuration

In `~/.hermes/config.yaml`:

```yaml
plugins:
  rag_memory:
    enabled: true
    mode: hybrid              # tfidf | neural | hybrid
    auto_capture: true        # Enable hooks
    cache_enabled: true       # Query caching
    cache_ttl: 300           # Cache lifetime (seconds)
    max_results: 10          # Max search results
```

---

## 📖 Usage Examples

### Daily Workflow

```bash
# Check health
rag-memory status

# Search memory
rag-memory search "meeting notes from yesterday"

# Backup before changes
rag-memory backup create --description "Before changes"

# Index new documents
rag-memory index ~/Documents/new_project/ --namespace work
```

### Backup & Restore

```bash
# Create backup
rag-memory backup create --description "Before migration"

# List all backups
rag-memory backup list

# Restore if needed
rag-memory backup restore rag_core_backup_20260406_120000.db

# Delete old backup
rag-memory backup delete old_backup.db
```

### Recovery

```bash
# If database is corrupted
rag-memory recover

# Restore from specific backup
rag-memory recover --from-backup rag_core_backup_20260406_120000.db
```

### Migration

```bash
# Auto-migrate from legacy ~/rag-system
rag-memory migrate --auto

# Migrate from specific database
rag-memory migrate /path/to/old.db --backup
```

---

## 🔄 Migration from Old Installation

**Previously installed with `--user` or `~/.hermes-venv`?**

See [MIGRATION.md](MIGRATION.md) for step-by-step migration guide to the new `~/.rag-memory` location.

**Quick migration script:**

```bash
curl -sSL https://raw.githubusercontent.com/favouraka/rag-memory-plugin/main/migrate_to_new_venv.sh | bash
```

This will:
- Remove old installation (~/.hermes-venv or user-space)
- Preserve all your data (database, config, backups)
- Install to new location (~/.rag-memory)
- Update your PATH

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Hermes Agent                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │ RAG Memory Plugin                                  │  │
│  │                                                     │  │
│  │  ┌─────────────┐    ┌─────────────┐              │  │
│  │  │  Tools      │    │   Hooks     │              │  │
│  │  │ - rag_search│    │ - pre_llm   │              │  │
│  │  │ - rag_add   │    │ - post_llm  │              │  │
│  │  │ - rag_stats │    │ - session   │              │  │
│  │  └──────┬──────┘    └──────┬──────┘              │  │
│  │         │                    │                     │  │
│  │  ┌──────▼────────────────────▼──────┐            │  │
│  │  │         RAGCore                   │            │  │
│  │  │  ┌────────────────────────────┐  │            │  │
│  │  │  │ TF-IDF Index (sqlite-vec) │  │            │  │
│  │  │  └────────────────────────────┘  │            │  │
│  │  │  ┌────────────────────────────┐  │            │  │
│  │  │  │ Neural Embeddings          │  │            │  │
│  │  │  │ (sentence-transformers)    │  │            │  │
│  │  │  └────────────────────────────┘  │            │  │
│  │  │  ┌────────────────────────────┐  │            │  │
│  │  │  │ Query Cache (LRU)          │  │            │  │
│  │  │  └────────────────────────────┘  │            │  │
│  │  └─────────────────────────────────┘  │            │  │
│  └─────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

---

## ⚡ Performance

| Operation | Time | Notes |
|-----------|------|-------|
| TF-IDF search | <10ms | No model required |
| Neural search | 60-100ms | sentence-transformers |
| Cached search | <1ms | 40-60% hit rate |
| Add document | 20-50ms | With embedding generation |
| Backup creation | <1s | For typical database |

---

## 🐛 Troubleshooting

### Database Corrupted

```bash
rag-memory recover
```

### Neural Model Not Working

```bash
# Reinstall neural dependencies
rag-memory install neural --force

# Falls back to TF-IDF automatically if download fails
```

### Database Not Found

```bash
# Run setup
rag-memory setup

# Or restore from backup
rag-memory backup restore <backup_file>
```

### Permission Errors

```bash
# Use virtual environment instead
python3 -m venv ~/.rag-memory
source ~/.rag-memory/bin/activate
pip install git+https://github.com/favouraka/rag-memory-plugin.git#egg=rag-memory-plugin[neural]
```

### Virtual Environment Location

**Where is everything installed?**

```bash
# Virtual environment
~/.rag-memory/
├── bin/
│   ├── python3
│   ├── pip3
│   └── rag-memory
├── lib/
│   └── python3.x/site-packages/
│       └── rag_memory/
└── pyvenv.cfg

# Data and configuration (separate from venv)
~/.hermes/plugins/rag-memory/
├── rag_core.db
├── config.yaml
└── backups/
```

**Recreate virtual environment:**
```bash
rm -rf ~/.rag-memory
curl -sSL https://raw.githubusercontent.com/favouraka/rag-memory-plugin/main/install.sh | bash
```

**Uninstall completely:**
```bash
# Remove virtual environment
rm -rf ~/.rag-memory

# Remove data and backups
rm -rf ~/.hermes/plugins/rag-memory/

# Remove from PATH
# Edit ~/.bashrc (or ~/.zshrc) and remove the export PATH line
```

---

## 🛠️ Development

### Setup Development Environment

```bash
git clone https://github.com/favouraka/rag-memory-plugin.git
cd rag-memory-plugin
python3 -m venv ~/.rag-memory
source ~/.rag-memory/bin/activate
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/
```

### Type Checking

```bash
mypy src/rag_memory
```

### Linting

```bash
ruff check src/rag_memory
```

---

## 📦 Plugin Integration

The plugin registers tools that Hermes can use:

**Tools:**
- `rag_search`: Search memory by semantic similarity
- `rag_add_document`: Add document to memory
- `rag_stats`: Show database statistics
- `rag_flush`: Flush write buffers

**Hooks:**
- `pre_llm`: Inject relevant context before LLM calls
- `post_llm`: Capture LLM responses after generation
- `session_start`: Initialize session context
- `session_end`: Save session context

Example in Hermes:
```
You: What did we work on yesterday?
Hermes: [Uses rag_search tool] Let me check...
      [Retrieves relevant context from previous conversations]
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

---

## 📞 Support

- **GitHub Issues**: https://github.com/favouraka/rag-memory-plugin/issues
- **Documentation**: https://github.com/favouraka/rag-memory-plugin/blob/main/docs/COMPLETE_IMPLEMENTATION.md

---

## 🎉 Status

✅ **Production Ready** - All features implemented and tested!

**Version:** 1.0.0
**Total Commands:** 20+
**Total Options:** 40+
**Documentation:** Complete
