"""File indexing for Hermes memory files.

Indexes static knowledge files into RAG database:
- MEMORY.md - Long-term facts and preferences
- Skills - Skill documentation
- Tools - Tool documentation and schemas
- Session state - Current context (optional)

Uses smart chunking by markdown headers and deduplication by content hash.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag_memory.core import RAGCore

logger = logging.getLogger(__name__)


# Default patterns for files to index
DEFAULT_PATTERNS = {
    "memory": ["MEMORY.md", "SESSION-STATE.md"],
    "skills": ["skills/*/*.md", "skills/*/*.SKILL.md"],
    "tools": ["tools/*.md"],
    "docs": ["*.md"],
}


def chunk_by_headers(content: str, max_size: int = 2000) -> list[str]:
    """Chunk markdown content by headers.

    Splits content on ## headers to create semantic chunks.
    Ensures chunks don't exceed max_size characters.

    Args:
        content: Markdown content to chunk
        max_size: Maximum characters per chunk

    Returns:
        List of content chunks
    """
    # Split on ## headers
    chunks = []
    current_chunk = ""
    current_header = ""

    lines = content.split("\n")

    for line in lines:
        # Check for ## header
        header_match = re.match(r"^##+\s+(.+)$", line)

        if header_match:
            # Save previous chunk if it exists
            if current_chunk.strip():
                chunks.append(current_header + "\n" + current_chunk)

            # Start new chunk
            current_header = line
            current_chunk = ""
        else:
            current_chunk += line + "\n"

        # Check if chunk is too large
        if len(current_chunk) > max_size:
            # Force split on current chunk
            chunks.append(current_header + "\n" + current_chunk)
            current_chunk = ""

    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_header + "\n" + current_chunk)

    # If no headers found, return entire content as one chunk
    if not chunks and content.strip():
        chunks = [content]

    return chunks


def compute_hash(content: str) -> str:
    """Compute SHA-256 hash of content.

    Args:
        content: Content to hash

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(content.encode()).hexdigest()


class FileIndexer:
    """Indexes Hermes memory files into RAG database."""

    def __init__(self, rag: "RAGCore", hermes_home: Path | None = None):
        """Initialize file indexer.

        Args:
            rag: RAGCore instance
            hermes_home: Path to Hermes home directory
        """
        self.rag = rag
        self.hermes_home = hermes_home or Path.home() / ".hermes"
        self.indexed_hashes: set[str] = set()
        self.stats = {
            "files_scanned": 0,
            "files_indexed": 0,
            "chunks_added": 0,
            "chunks_skipped": 0,
            "errors": [],
        }

    def scan_files(
        self, patterns: dict[str, list[str]] | None = None, recursive: bool = True
    ) -> dict[str, list[Path]]:
        """Scan Hermes home for files matching patterns.

        Args:
            patterns: Dict of namespace -> glob patterns
            recursive: Whether to scan recursively

        Returns:
            Dict of namespace -> list of file paths
        """
        patterns = patterns or DEFAULT_PATTERNS
        files_by_namespace: dict[str, list[Path]] = {}

        for namespace, pattern_list in patterns.items():
            files_by_namespace[namespace] = []

            for pattern in pattern_list:
                # Expand pattern
                if "*" in pattern:
                    # Use glob
                    matches = self.hermes_home.glob(pattern)
                    files_by_namespace[namespace].extend(matches)
                else:
                    # Direct path
                    file_path = self.hermes_home / pattern
                    if file_path.exists():
                        files_by_namespace[namespace].append(file_path)

            # Remove duplicates
            files_by_namespace[namespace] = list(set(files_by_namespace[namespace]))
            self.stats["files_scanned"] += len(files_by_namespace[namespace])

        return files_by_namespace

    def index_file(
        self, file_path: Path, namespace: str, chunk_size: int = 2000
    ) -> int:
        """Index a single file into RAG.

        Args:
            file_path: Path to file to index
            namespace: Namespace to store in
            chunk_size: Maximum characters per chunk

        Returns:
            Number of chunks added
        """
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return 0

        try:
            # Read file
            content = file_path.read_text(encoding="utf-8")

            if not content.strip():
                logger.debug(f"Empty file: {file_path}")
                return 0

            # Get file info
            rel_path = file_path.relative_to(self.hermes_home)
            file_stat = file_path.stat()
            modified_at = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc)

            # Chunk by headers
            chunks = chunk_by_headers(content, max_size=chunk_size)

            added = 0
            for i, chunk in enumerate(chunks):
                # Compute hash for deduplication
                chunk_hash = compute_hash(chunk)

                # Check if already indexed
                if chunk_hash in self.indexed_hashes:
                    self.stats["chunks_skipped"] += 1
                    continue

                # Add to RAG
                metadata = {
                    "source": "file_index",
                    "file_path": str(rel_path),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "modified_at": modified_at.isoformat(),
                    "indexed_at": datetime.now(timezone.utc).isoformat(),
                    "content_hash": chunk_hash,
                }

                self.rag.add_document(
                    content=chunk,
                    namespace=namespace,
                    metadata=metadata,
                )

                self.indexed_hashes.add(chunk_hash)
                added += 1
                self.stats["chunks_added"] += 1

            if added > 0:
                self.stats["files_indexed"] += 1
                logger.debug(f"Indexed {file_path}: {added} chunks")

            return added

        except Exception as e:
            error_msg = f"Failed to index {file_path}: {e}"
            logger.warning(error_msg)
            self.stats["errors"].append(error_msg)
            return 0

    def index_all(
        self,
        patterns: dict[str, list[str]] | None = None,
        chunk_size: int = 2000,
        deduplicate: bool = True,
    ) -> dict:
        """Index all matching files.

        Args:
            patterns: Dict of namespace -> glob patterns
            chunk_size: Maximum characters per chunk
            deduplicate: Whether to deduplicate by content hash

        Returns:
            Statistics dict
        """
        logger.info("📂 Scanning Hermes memory files...")

        # Load existing hashes if deduplicating
        if deduplicate:
            self._load_existing_hashes()

        # Scan files
        files_by_namespace = self.scan_files(patterns)

        # Index files
        for namespace, file_paths in files_by_namespace.items():
            logger.info(f"  Indexing namespace: {namespace}")

            for file_path in file_paths:
                self.index_file(file_path, f"hermes_{namespace}", chunk_size)

        # Log results
        logger.info(f"✓ Indexing complete:")
        logger.info(f"  Files scanned: {self.stats['files_scanned']}")
        logger.info(f"  Files indexed: {self.stats['files_indexed']}")
        logger.info(f"  Chunks added: {self.stats['chunks_added']}")
        logger.info(f"  Chunks skipped: {self.stats['chunks_skipped']}")

        if self.stats["errors"]:
            logger.warning(f"  Errors: {len(self.stats['errors'])}")
            for error in self.stats["errors"][:5]:
                logger.warning(f"    - {error}")

        return self.stats

    def _load_existing_hashes(self) -> None:
        """Load existing content hashes from RAG to avoid duplicates."""
        try:
            # Search for all documents with file_index source
            # This is a simplified check - in production you'd query directly
            results = self.rag.search(
                "", namespace="hermes_memory", limit=10000
            )  # Empty search to get all

            for result in results:
                metadata = result.get("metadata", {})
                content_hash = metadata.get("content_hash")
                if content_hash:
                    self.indexed_hashes.add(content_hash)

            logger.debug(f"Loaded {len(self.indexed_hashes)} existing hashes")

        except Exception as e:
            logger.warning(f"Failed to load existing hashes: {e}")

    def get_stats(self) -> dict:
        """Get indexing statistics.

        Returns:
            Statistics dict
        """
        return self.stats.copy()


def index_hermes_files(
    rag: "RAGCore",
    hermes_home: Path | None = None,
    patterns: dict[str, list[str]] | None = None,
    chunk_size: int = 2000,
) -> dict:
    """Index Hermes memory files into RAG.

    Convenience function for one-shot indexing.

    Args:
        rag: RAGCore instance
        hermes_home: Path to Hermes home directory
        patterns: Dict of namespace -> glob patterns
        chunk_size: Maximum characters per chunk

    Returns:
        Statistics dict
    """
    indexer = FileIndexer(rag, hermes_home)
    return indexer.index_all(patterns, chunk_size)
