"""Cron job configuration for RAG Memory file indexing.

This module provides integration with Hermes cron system to automatically
index Hermes memory files:
- On every new session start
- Every 4 hours

The cron job ensures the RAG database stays in sync with memory files.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_cron_config() -> dict:
    """Get cron job configuration for file indexing.

    Returns:
        Dict with cron job configuration
    """
    return {
        "name": "rag-memory-index-files",
        "description": "Index Hermes memory files into RAG database",
        "schedule": "0 */4 * * *",  # Every 4 hours
        "enabled": True,
        "command": "rag-memory index-files",
        "deliver": "local",  # Save to local files only
        "metadata": {
            "trigger": "scheduled",
            "interval_hours": 4,
        },
    }


def register_session_hook(context: any) -> None:
    """Register hook to run file indexing on session start.

    This is called during plugin registration to set up automatic
    file indexing when a new Hermes session starts.

    Args:
        context: Plugin context from Hermes
    """
    try:
        # Register session start hook
        context.register_hook("on_session_start", _on_session_start_index_files)
        logger.debug("✓ Registered session start file indexing hook")
    except Exception as e:
        logger.warning(f"Failed to register session start hook: {e}")


def _on_session_start_index_files(event: dict, context: any) -> None:
    """Hook handler for session start - runs file indexing.

    Args:
        event: Session start event
        context: Plugin context
    """
    try:
        from rag_memory.core import index_hermes_files, RAGCore

        # Get RAG instance from plugin
        import rag_memory.plugin as plugin

        if not plugin._initialized or not plugin._rag:
            logger.debug("RAG not initialized, skipping file index")
            return

        # Check if we should index on session start
        config = plugin._config or {}
        if not config.get("index_on_session_start", True):
            logger.debug("File indexing on session start disabled")
            return

        # Index files
        hermes_home = Path(getattr(context, "hermes_home", Path.home() / ".hermes"))
        logger.info("📂 Indexing Hermes memory files (session start)...")

        stats = index_hermes_files(
            plugin._rag,
            hermes_home=hermes_home,
            chunk_size=config.get("file_chunk_size", 2000),
        )

        logger.info(
            f"✓ File indexing complete: {stats['files_indexed']} files, "
            f"{stats['chunks_added']} chunks added"
        )

    except Exception as e:
        logger.warning(f"Session start file indexing failed: {e}")


def setup_cron_job(context: any) -> None:
    """Set up cron job for periodic file indexing.

    Registers a cron job to run file indexing every 4 hours.

    Args:
        context: Plugin context from Hermes
    """
    try:
        # Check if cron system is available
        if not hasattr(context, "register_cron_job"):
            logger.warning("Cron system not available in this context")
            return

        # Get cron config
        cron_config = get_cron_config()

        # Register cron job
        context.register_cron_job(
            name=cron_config["name"],
            schedule=cron_config["schedule"],
            command=cron_config["command"],
            deliver=cron_config["deliver"],
            metadata=cron_config["metadata"],
        )

        logger.info(f"✓ Registered cron job: {cron_config['name']}")

    except Exception as e:
        logger.warning(f"Failed to register cron job: {e}")


# Cron job script that can be run independently
CRON_SCRIPT = """#!/bin/bash
# RAG Memory File Indexing Cron Job
# Runs every 4 hours to keep RAG database in sync with memory files

# Activate Hermes environment if needed
# source ~/.hermes/venv/bin/activate

# Run indexing
rag-memory index-files

# Check exit code
if [ $? -eq 0 ]; then
    echo "RAG file indexing completed successfully"
else
    echo "RAG file indexing failed" >&2
    exit 1
fi
"""


def write_cron_script(output_path: Path) -> None:
    """Write cron script to file.

    Args:
        output_path: Path to write script
    """
    output_path.write_text(CRON_SCRIPT)
    output_path.chmod(0o755)  # Make executable
    logger.info(f"✓ Wrote cron script: {output_path}")
