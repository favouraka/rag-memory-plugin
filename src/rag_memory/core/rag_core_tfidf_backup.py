"""
Core RAG functionality - TF-IDF + Neural retrieval
This module provides the core search and indexing capabilities.
"""

import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RAGCore:
    """
    Core RAG implementation with hybrid retrieval (TF-IDF + Neural).
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize RAG core.

        Args:
            db_path: Path to SQLite database. Uses default if not provided.
        """
        if db_path is None:
            db_path = Path.home() / ".hermes" / "plugins" / "rag-memory" / "rag_core.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._initialize_db()

    def _initialize_db(self):
        """Initialize database schema."""
        cursor = self.conn.cursor()

        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # TF-IDF terms table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tfidf_terms (
                document_id TEXT NOT NULL,
                term TEXT NOT NULL,
                frequency INTEGER NOT NULL,
                PRIMARY KEY (document_id, term),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # Embeddings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                document_id TEXT PRIMARY KEY,
                embedding BLOB,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_namespace ON documents(namespace)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_tfidf_terms_term ON tfidf_terms(term)"
        )

        self.conn.commit()
        logger.info("✓ RAG core database initialized")

    def add_document(
        self,
        content: str,
        namespace: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a document to RAG index.

        Args:
            content: Document content
            namespace: Namespace to store in
            metadata: Optional metadata
            document_id: Custom document ID

        Returns:
            Dict with document ID
        """
        import json

        # Generate ID if not provided
        if not document_id:
            content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
            document_id = f"{namespace}_{content_hash}"

        # Insert document
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO documents (id, namespace, content, metadata) VALUES (?, ?, ?, ?)",
                (document_id, namespace, content, json.dumps(metadata or {})),
            )

            # Index for TF-IDF
            self._index_tfidf(cursor, document_id, content)

            # For neural retrieval, we'd generate embeddings here
            # For now, we'll skip and implement later
            # self._generate_embedding(document_id, content)

            self.conn.commit()

            return {"id": document_id, "namespace": namespace, "status": "added"}

        except sqlite3.IntegrityError:
            # Document already exists, update it
            cursor.execute(
                "UPDATE documents SET content = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (content, json.dumps(metadata or {}), document_id),
            )

            # Re-index TF-IDF
            cursor.execute(
                "DELETE FROM tfidf_terms WHERE document_id = ?", (document_id,)
            )
            self._index_tfidf(cursor, document_id, content)

            self.conn.commit()

            return {"id": document_id, "namespace": namespace, "status": "updated"}

    def _index_tfidf(self, cursor, document_id: str, content: str):
        """
        Index document for TF-IDF retrieval.

        Args:
            cursor: Database cursor
            document_id: Document ID
            content: Document content
        """
        import re
        from collections import Counter

        # Simple tokenization - split on non-word characters
        tokens = re.findall(r"\b\w+\b", content.lower())

        # Count term frequencies
        term_freq = Counter(tokens)

        # Insert into database
        for term, freq in term_freq.items():
            if len(term) > 2:  # Skip very short terms
                cursor.execute(
                    "INSERT INTO tfidf_terms (document_id, term, frequency) VALUES (?, ?, ?)",
                    (document_id, term, freq),
                )

    def search(
        self,
        query: str,
        namespace: Optional[str] = None,
        mode: str = "hybrid",
        limit: int = 10,
        tokens: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Search RAG index.

        Args:
            query: Search query
            namespace: Optional namespace filter
            mode: 'hybrid', 'tfidf', or 'neural'
            limit: Max results
            tokens: Token budget for content truncation

        Returns:
            List of search results
        """

        cursor = self.conn.cursor()

        if mode in ["tfidf", "hybrid"]:
            results = self._search_tfidf(cursor, query, namespace, limit)
        else:
            results = []

        # For neural mode, we'd implement embedding search here
        # For now, just use TF-IDF

        # Truncate content based on token budget
        avg_chars_per_token = 4
        char_limit = tokens * avg_chars_per_token

        for result in results:
            content = result.get("content", "")
            if len(content) > char_limit:
                result["content"] = content[:char_limit] + "..."

        # Add namespace to results
        for result in results:
            result["_namespace"] = result.get("namespace", namespace or "default")

        return results[:limit]

    def _search_tfidf(
        self, cursor, query: str, namespace: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """
        Search using TF-IDF.

        Args:
            cursor: Database cursor
            query: Search query
            namespace: Optional namespace filter
            limit: Max results

        Returns:
            List of results with scores
        """
        import re
        from collections import Counter

        # Tokenize query
        query_tokens = re.findall(r"\b\w+\b", query.lower())
        query_freq = Counter(query_tokens)

        if not query_tokens:
            return []

        # Build SQL query
        placeholders = ",".join(["?"] * len(query_tokens))

        if namespace:
            sql = f"""
                SELECT d.id, d.namespace, d.content, d.metadata,
                       SUM(tf.frequency) as score
                FROM documents d
                JOIN tfidf_terms tf ON d.id = tf.document_id
                WHERE d.namespace = ?
                AND tf.term IN ({placeholders})
                GROUP BY d.id
                ORDER BY score DESC
                LIMIT ?
            """
            params = [namespace] + list(query_tokens) + [limit]
        else:
            sql = f"""
                SELECT d.id, d.namespace, d.content, d.metadata,
                       SUM(tf.frequency) as score
                FROM documents d
                JOIN tfidf_terms tf ON d.id = tf.document_id
                WHERE tf.term IN ({placeholders})
                GROUP BY d.id
                ORDER BY score DESC
                LIMIT ?
            """
            params = list(query_tokens) + [limit]

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "id": row[0],
                    "namespace": row[1],
                    "content": row[2],
                    "metadata": row[3],
                    "score": float(row[4]),
                }
            )

        return results

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document dict or None
        """
        import json

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, namespace, content, metadata, created_at FROM documents WHERE id = ?",
            (document_id,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "namespace": row[1],
            "content": row[2],
            "metadata": json.loads(row[3]) if row[3] else {},
            "created_at": row[4],
        }

    def list_namespaces(self) -> List[str]:
        """
        List all namespaces in the database.

        Returns:
            List of namespace strings
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT namespace FROM documents ORDER BY namespace")
        rows = cursor.fetchall()
        return [row[0] for row in rows]

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("✓ RAG core connection closed")
