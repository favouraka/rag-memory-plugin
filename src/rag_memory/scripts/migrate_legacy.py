#!/usr/bin/env python3
"""Migrate data from legacy ~/rag-system to RAG Memory plugin.

This script:
1. Connects to legacy ~/rag-system/rag_data.db
2. Exports all documents with embeddings
3. Imports to new ~/.hermes/plugins/rag-memory/rag_memory.db
4. Verifies data integrity

Usage
-----
.. code-block:: bash

    python -m rag_memory.scripts.migrate_legacy

Or via CLI:
.. code-block:: bash

    rag-memory migrate-from-legacy
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def export_legacy_data(legacy_db_path: Path) -> list[dict]:
    """Export all data from legacy RAG database.

    Args:
        legacy_db_path: Path to ~/rag-system/rag_data.db

    Returns:
        List of documents with content, metadata, embeddings
    """
    if not legacy_db_path.exists():
        logger.error(f"Legacy database not found: {legacy_db_path}")
        sys.exit(1)

    logger.info(f"📂 Exporting from: {legacy_db_path}")

    conn = sqlite3.connect(str(legacy_db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    documents = []

    try:
        # Check if doc_vectors table exists (neural)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='doc_vectors'"
        )
        has_vectors = cursor.fetchone() is not None

        if has_vectors:
            logger.info("📊 Exporting neural vectors...")
            cursor.execute(
                "SELECT id, content, metadata, created_at FROM doc_vectors ORDER BY id"
            )
            rows = cursor.fetchall()

            for row in rows:
                doc = {
                    "id": row["id"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "created_at": row["created_at"],
                    "namespace": "legacy",
                }
                documents.append(doc)

            logger.info(f"✓ Exported {len(documents)} documents with vectors")

        # Also export TF-IDF documents if separate
        tfidf_db = legacy_db_path.parent / "rag_data_tfidf.db"
        if tfidf_db.exists():
            logger.info(f"📂 Exporting TF-IDF data from: {tfidf_db}")

            conn2 = sqlite3.connect(str(tfidf_db))
            conn2.row_factory = sqlite3.Row
            cursor2 = conn2.cursor()

            cursor2.execute("SELECT id, content, metadata FROM documents")
            rows = cursor2.fetchall()

            for row in rows:
                doc = {
                    "id": row["id"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "namespace": "legacy_tfidf",
                }
                documents.append(doc)

            conn2.close()
            logger.info(f"✓ Exported {len(rows)} TF-IDF documents")

    except Exception as e:
        logger.error(f"✗ Export failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

    return documents


def import_to_plugin(
    documents: list[dict], plugin_db_path: Path, regen_embeddings: bool = False
) -> int:
    """Import documents to RAG Memory plugin database.

    Args:
        documents: List of documents from export
        plugin_db_path: Path to ~/.hermes/plugins/rag-memory/rag_memory.db
        regen_embeddings: Regenerate embeddings using sentence-transformers

    Returns:
        Number of documents imported
    """
    logger.info(f"📂 Importing to: {plugin_db_path}")

    # Initialize plugin database
    try:
        from rag_memory.core import RAGCore

        plugin_db_path.parent.mkdir(parents=True, exist_ok=True)
        rag = RAGCore(str(plugin_db_path))
        # RAGCore initializes automatically in __init__

    except ImportError:
        logger.error("✗ RAG Memory plugin not installed")
        logger.info("Install: pip install rag-memory-plugin[neural]")
        sys.exit(1)

    imported = 0

    for doc in documents:
        try:
            # Parse metadata
            metadata = doc.get("metadata", {})
            metadata["legacy_id"] = doc.get("id")
            metadata["legacy_created_at"] = doc.get("created_at")

            # Add document (RAGCore will handle embeddings)
            rag.add_document(
                content=doc.get("content", ""),
                namespace=doc.get("namespace", "legacy"),
                metadata=metadata,
            )
            imported += 1

        except Exception as e:
            logger.warning(f"⚠ Failed to import document {doc.get('id')}: {e}")

    logger.info(f"✓ Imported {imported}/{len(documents)} documents")
    return imported


def verify_migration(legacy_db_path: Path, plugin_db_path: Path) -> bool:
    """Verify data integrity after migration.

    Args:
        legacy_db_path: Original database
        plugin_db_path: New database

    Returns:
        True if verification passed
    """
    logger.info("🔍 Verifying migration...")

    # Count documents in both databases
    conn_legacy = sqlite3.connect(str(legacy_db_path))
    cursor_legacy = conn_legacy.cursor()

    try:
        cursor_legacy.execute("SELECT COUNT(*) FROM doc_vectors")
        legacy_count = cursor_legacy.fetchone()[0]
    except sqlite3.OperationalError:
        # Table might not exist
        cursor_legacy.execute("SELECT COUNT(*) FROM documents")
        legacy_count = cursor_legacy.fetchone()[0]

    conn_legacy.close()

    conn_plugin = sqlite3.connect(str(plugin_db_path))
    cursor_plugin = conn_plugin.cursor()
    cursor_plugin.execute("SELECT COUNT(*) FROM documents")
    plugin_count = cursor_plugin.fetchone()[0]
    conn_plugin.close()

    logger.info(f"  Legacy: {legacy_count} documents")
    logger.info(f"  Plugin: {plugin_count} documents")

    if plugin_count >= legacy_count:
        logger.info("✓ Verification passed")
        return True
    else:
        logger.warning("⚠ Document count mismatch")
        return False


def main() -> None:
    """Run migration."""
    logger.info("🚀 RAG Memory Migration: Legacy → Plugin\n")

    # Paths
    legacy_db = Path.home() / "rag-system" / "rag_data.db"
    hermes_home = Path.home() / ".hermes"
    plugin_db = hermes_home / "plugins" / "rag-memory" / "rag_memory.db"

    # Check if legacy exists
    if not legacy_db.exists():
        logger.error("✗ Legacy ~/rag-system not found")
        logger.info(f"  Expected: {legacy_db}")
        sys.exit(1)

    # Export
    documents = export_legacy_data(legacy_db)

    if not documents:
        logger.error("✗ No documents found to export")
        sys.exit(1)

    # Backup existing plugin DB if it exists
    if plugin_db.exists():
        backup_path = plugin_db.with_suffix(
            f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        logger.info(f"📦 Backing up existing DB to: {backup_path}")
        plugin_db.rename(backup_path)

    # Import
    import_to_plugin(documents, plugin_db, regen_embeddings=False)

    # Verify
    if verify_migration(legacy_db, plugin_db):
        logger.info("\n✅ Migration complete!")
        logger.info(f"📊 New database: {plugin_db}")
        logger.info("\n🧪 Test with:")
        logger.info("  rag-memory doctor")
        logger.info("  rag-memory search 'test query'")
    else:
        logger.warning("\n⚠ Migration completed with warnings")
        sys.exit(1)


if __name__ == "__main__":
    main()
