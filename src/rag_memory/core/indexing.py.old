"""
File and workspace indexing for RAG
"""

import logging
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FileIndexer:
    """Index files into RAG database"""

    # Binary file extensions to skip
    BINARY_EXTENSIONS = {
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib',
        '.exe', '.bin', '.obj', '.o', '.a', '.lib',
        '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp',
        '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.ttf', '.otf', '.woff', '.woff2', '.eot',
    }

    # Max file size (1MB)
    MAX_FILE_SIZE = 1_048_576

    def __init__(self, rag_core):
        """
        Initialize FileIndexer

        Args:
            rag_core: RAGCore instance
        """
        self.rag = rag_core

    def _is_binary(self, path: Path) -> bool:
        """Check if file is binary"""
        # Check extension
        if path.suffix.lower() in self.BINARY_EXTENSIONS:
            return True

        # Check size
        if path.stat().st_size > self.MAX_FILE_SIZE:
            return True

        # Check content
        try:
            with open(path, 'rb') as f:
                chunk = f.read(8192)
                if b'\x00' in chunk:
                    return True
        except Exception:
            return True

        return False

    def index_file(
        self,
        file_path: str,
        namespace: str = "files",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Index a single file

        Args:
            file_path: Path to file
            namespace: Namespace to store in
            metadata: Additional metadata

        Returns:
            Dict with status
        """
        path = Path(file_path)

        if not path.exists():
            return {"status": "error", "reason": "file_not_found"}

        if not path.is_file():
            return {"status": "error", "reason": "not_a_file"}

        # Skip binary files
        if self._is_binary(path):
            return {
                "status": "skipped",
                "reason": "binary",
                "path": str(path)
            }

        # Read content
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            return {
                "status": "error",
                "reason": "read_failed",
                "error": str(e)
            }

        # Skip empty files
        if not content.strip():
            return {
                "status": "skipped",
                "reason": "empty",
                "path": str(path)
            }

        # Generate document ID
        doc_id = f"file_{hashlib.md5(str(path).encode()).hexdigest()}"

        # Prepare metadata
        file_meta = {
            "source": "file",
            "path": str(path),
            "name": path.name,
            "extension": path.suffix,
            "size": path.stat().st_size,
            "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat()
        }
        if metadata:
            file_meta.update(metadata)

        # Add to RAG
        result = self.rag.add_document(
            content=content,
            namespace=namespace,
            metadata=file_meta,
            document_id=doc_id
        )

        result['path'] = str(path)
        return result

    def index_workspace(
        self,
        workspace_path: str,
        namespace: str = "workspace",
        pattern: str = "**/*.py",
        exclude: Optional[List[str]] = None,
        max_files: int = 1000
    ) -> Dict:
        """
        Recursively index workspace files

        Args:
            workspace_path: Path to workspace
            namespace: Namespace to store in
            pattern: Glob pattern (e.g., "**/*.py")
            exclude: Paths to exclude (glob patterns)
            max_files: Maximum files to index

        Returns:
            Dict with indexed/skipped/error counts
        """
        workspace = Path(workspace_path)

        if not workspace.exists():
            return {"status": "error", "reason": "workspace_not_found"}

        exclude = exclude or ['**/.git/**', '**/node_modules/**', '**/__pycache__/**', '**/venv/**', '**/.venv/**']

        indexed = 0
        skipped = 0
        errors = 0
        files_processed = 0

        logger.info(f"Indexing workspace: {workspace}")
        logger.info(f"Pattern: {pattern}")

        for file_path in workspace.glob(pattern):
            if files_processed >= max_files:
                logger.warning(f"Reached max files limit ({max_files})")
                break

            # Skip excluded paths
            if any(file_path.match(excl) for excl in exclude):
                skipped += 1
                continue

            if not file_path.is_file():
                continue

            files_processed += 1

            result = self.index_file(str(file_path), namespace=namespace)

            if result.get("status") == "added":
                indexed += 1
                if indexed % 10 == 0:
                    logger.info(f"Indexed {indexed} files...")
            elif result.get("status") == "skipped":
                skipped += 1
            else:
                errors += 1
                logger.debug(f"Error indexing {file_path}: {result}")

        logger.info(f"✓ Indexed {indexed} files, skipped {skipped}, errors {errors}")

        return {
            "status": "complete",
            "indexed": indexed,
            "skipped": skipped,
            "errors": errors,
            "namespace": namespace
        }

    def search_files(
        self,
        query: str,
        namespace: str = "files",
        limit: int = 10
    ) -> List[Dict]:
        """
        Search indexed files

        Args:
            query: Search query
            namespace: Namespace to search
            limit: Max results

        Returns:
            List of file results
        """
        results = self.rag.search(
            query=query,
            namespace=namespace,
            mode="hybrid",
            limit=limit
        )

        # Add file metadata to results
        for result in results:
            meta = result.get('metadata', {})
            # Handle both dict and JSON string
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except:
                    meta = {}
            result['file_path'] = meta.get('path', 'unknown')
            result['file_name'] = meta.get('name', 'unknown')

        return results
