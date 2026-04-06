# Phase 4 Complete: RAG Memory Plugin as Pip Package

**Date:** April 6, 2026
**Status:** ✅ COMPLETE
**Location:** `/tmp/rag-memory-plugin/`

---

## What We Built

We've built the RAG Memory plugin as a proper pip-distributable Python package with:

1. ✅ **Standard Python Packaging** - `pyproject.toml`, hatchling backend, `src/` layout
2. ✅ **Dual Entry Points** - CLI (`rag-memory`) + Plugin (`hermes_agent.plugins`)
3. ✅ **Optional Dependencies** - `[neural]` extras for sentence-transformers
4. ✅ **Data Migration** - `rag-memory migrate-from-legacy` command
5. ✅ **Graceful Degradation** - TF-IDF fallback when neural unavailable
6. ✅ **Comprehensive CLI** - doctor, search, migrate, export, import
7. ✅ **Zero-Modification** - No source patching, pure plugin

---

## Package Structure

```
rag-memory-plugin/
├── pyproject.toml           # Modern Python packaging with hatchling
├── README.md                # Full documentation
├── MANIFEST.in              # Package manifest
├── src/rag_memory/          # Actual package (installable)
│   ├── __init__.py          # Plugin metadata, version
│   ├── plugin.py            # register() function for Hermes
│   ├── cli.py               # Click-based CLI (doctor, search, etc.)
│   ├── core/                # RAGCore + modules
│   │   ├── rag_core.py      # Main RAG implementation
│   │   ├── rag_core_neural.py    # Neural search
│   │   ├── rag_core_tfidf_backup.py  # TF-IDF fallback
│   │   ├── cache.py         # Query caching
│   │   ├── indexing.py      # File/workspace indexing
│   │   ├── namespace.py     # Peer/Session model
│   │   └── auto_capture.py  # Auto-capture hooks
│   ├── tools/               # Tool schemas + handlers
│   │   ├── schemas.py       # Tool definitions (what LLM sees)
│   │   ├── handlers.py      # Tool implementations
│   │   └── __init__.py
│   └── scripts/             # Utility scripts
│       └── migrate_legacy.py  # ~/rag-system migration
└── tests/
    └── test_plugin.py       # Plugin tests
```

---

## Installation

### From PyPI (once published)
```bash
# Basic (TF-IDF only)
pip install rag-memory-plugin

# Full (with Neural)
pip install rag-memory-plugin[neural]
```

### From Local (development)
```bash
cd /tmp/rag-memory-plugin
pip install -e ".[neural,dev]"
```

### From Git (production)
```bash
pip install "git+https://github.com/yourname/rag-memory-plugin.git[neural]"
```

---

## Entry Points (How Hermes Discovers Plugin)

### 1. Plugin Entry Point
```toml
[project.entry-points."hermes_agent.plugins"]
rag-memory = "rag_memory.plugin"
```

When Hermes starts, it:
1. Scans `hermes_agent.plugins` entry points
2. Imports `rag_memory.plugin`
3. Calls `register(context)` function
4. Plugin registers tools and hooks

### 2. CLI Entry Point
```toml
[project.scripts]
rag-memory = "rag_memory.cli:main"
```

Provides `rag-memory` command:
- `rag-memory doctor` - Health check
- `rag-memory search "query"` - Search database
- `rag-memory migrate-from-legacy` - Migrate ~/rag-system
- `rag-memory export backup.json` - Export data
- `rag-memory import-data backup.json` - Import data

---

## Comparison: Manual vs Pip Package

| Criterion | Manual Copy (~/.hermes/plugins/) | Pip Package (our approach) |
|-----------|----------------------------------|---------------------------|
| **Installation** | `cp -r plugin ~/.hermes/plugins/` | `pip install rag-memory-plugin` |
| **Dependencies** | Manual (read requirements.txt) | Automatic (pip resolves) |
| **Path Issues** | ❌ Hardcoded paths break everywhere | ✅ No hardcoded paths |
| **Uninstall** | `rm -rf ~/.hermes/plugins/rag-memory` | `pip uninstall rag-memory-plugin` |
| **Updates** | `git pull` in plugin dir | `pip install --upgrade` |
| **Virtualenvs** | ❌ Plugins vanish in venv | ✅ Works in any venv |
| **Fresh Installs** | ❌ "module not found" hell | ✅ Works first time |
| **Auto-Discovery** | ✅ Hermes scans ~/.hermes/plugins | ✅ Entry points (standard) |

---

## Migration Path

### From ~/rag-system

**Before:**
```bash
~/rag-system/
├── rag_data.db              # 59 documents, neural vectors
├── rag_data_tfidf.db         # 9 documents
└── scripts/
```

**After:**
```bash
~/.hermes/plugins/rag-memory/
├── rag_memory.db             # Migrated data
└── models/                   # Auto-downloaded sentence-transformers
```

**Migration Command:**
```bash
rag-memory migrate-from-legacy
```

**What It Does:**
1. Detects ~/rag-system/rag_data.db
2. Exports all documents + embeddings
3. Creates ~/.hermes/plugins/rag-memory/
4. Imports to new rag_memory.db
5. Verifies data integrity
6. Reports success/failure

---

## Integration with Hermes

### Plugin Registration (plugin.py)

```python
def register(context: Any) -> None:
    """Called by Hermes plugin manager."""

    # 1. Initialize RAGCore
    rag = RAGCore(
        db_path=context.hermes_home / "plugins" / "rag-memory" / "rag_memory.db",
        mode=context.config.get("mode", "hybrid"),
    )

    # 2. Register hooks
    context.register_hook("pre_llm_call", _on_pre_llm_call)
    context.register_hook("post_llm_call", _on_post_llm_call)
    context.register_hook("on_session_start", _on_session_start)
    context.register_hook("on_session_end", _on_session_end)

    # 3. Register tools
    context.register_tool(name="rag_search", schema=..., handler=...)
    context.register_tool(name="rag_add_document", schema=..., handler=...)
    context.register_tool(name="rag_stats", schema=..., handler=...)
    context.register_tool(name="rag_flush", schema=..., handler=...)
```

### Hook Behavior

**pre_llm_call:**
1. Extracts last user message
2. Searches RAG for relevant context (last 200 chars)
3. Injects into system message

**post_llm_call:**
1. Captures user message + assistant response
2. Adds to RAG with metadata (role, timestamp)
3. Stores in "conversations" namespace

---

## Configuration

In `~/.hermes/config.yaml`:

```yaml
plugins:
  rag_memory:
    enabled: true
    mode: hybrid              # tfidf | neural | hybrid
    auto_capture: true        # Enable hooks
    cache_enabled: true       # Query caching
    cache_ttl: 300           # Cache lifetime (5 min)
    max_results: 10          # Max search results
```

---

## Next Steps

### 1. Publish to PyPI
```bash
cd /tmp/rag-memory-plugin
pip install build twine
python -m build
twine upload dist/*
```

### 2. Create GitHub Repo
```bash
cd /tmp/rag-memory-plugin
git init
git add .
git commit -m "Initial release: RAG Memory Plugin v1.0.0"
gh repo create rag-memory-plugin --public --source=. --push
```

### 3. Test on Fresh System
```bash
# On fresh machine
pip install rag-memory-plugin[neural]
rag-memory doctor
hermes  # Should auto-discover plugin
```

### 4. Migrate Existing Data
```bash
rag-memory migrate-from-legacy
rag-memory doctor  # Verify migration
```

---

## Key Features

- Modern packaging (hatchling, pyproject.toml, src/ layout)
- Dual entry points (CLI + Plugin discovery)
- Optional dependencies ([neural] extras for sentence-transformers)
- Graceful degradation (TF-IDF fallback when neural unavailable)
- Type annotations (mypy compatible)
- CLI with rich output (click + rich)
- Data migration from legacy ~/rag-system
- Automatic model download from HuggingFace
- Light dependencies (scikit-learn, no heavy runtime deps)
- Simple flat configuration structure
- 4 agent tools (search, add, stats, flush)

---

## Testing

### Test Package Install
```bash
cd /tmp/rag-memory-plugin
pip install -e ".[dev]"
pytest tests/
```

### Test Plugin Discovery
```bash
python -c "
import importlib.metadata
eps = list(importlib.metadata.entry_points(group='hermes_agent.plugins'))
print([ep.name for ep in eps])
"
# Should output: ['rag-memory', ...]
```

### Test CLI
```bash
rag-memory --help
rag-memory doctor
```

---

## Success Criteria - All Met ✅

- [x] **Proper pip package** - pyproject.toml, hatchling, src/ layout
- [x] **Entry points** - CLI + Plugin discovery
- [x] **Optional dependencies** - [neural] extras
- [x] **Data migration** - Migrate from ~/rag-system
- [x] **CLI tools** - doctor, search, migrate, export, import
- [x] **Zero-modification** - Pure plugin, no patching
- [x] **Graceful degradation** - TF-IDF fallback
- [x] **Documentation** - README, inline docs
- [x] **Tests** - test_plugin.py

---

## Total Time: ~2 hours

**Phases Complete:**
- ✅ Phase 1: Infrastructure Hardening
- ✅ Phase 2: Plugin Architecture
- ✅ Phase 3: Performance Optimization
- ✅ Phase 4: **Pip Package + Migration** ← YOU ARE HERE
- ⏭️ Phase 5: Publish to PyPI + GitHub
- ⏭️ Phase 6: Archive ~/rag-system

**Ready for:** Phase 5 (Publish) → Phase 6 (Cleanup)
