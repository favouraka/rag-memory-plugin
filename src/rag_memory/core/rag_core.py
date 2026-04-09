"""
Core RAG functionality - TF-IDF + Neural retrieval with sqlite-vec
This module provides the core search and indexing capabilities with full hybrid support.
"""

import hashlib
import json
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from .cache import PerformanceMetrics, QueryCache

logger = logging.getLogger(__name__)


class RAGCore:
    """
    Core RAG implementation with hybrid retrieval (TF-IDF + Neural).

    Features:
    - TF-IDF retrieval (fast, keyword-based)
    - Neural retrieval (semantic, embedding-based)
    - Hybrid mode (fusion of both)
    - Graceful TF-IDF fallback when model unavailable
    - Connection pooling for concurrent access
    - Embedding caching for performance
    """

    # Class-level connection pool
    _pool = {}
    _pool_lock = threading.Lock()

    def __init__(
        self,
        db_path: Optional[str] = None,
        model_path: str = "sentence-transformers/all-MiniLM-L6-v2",
        enable_model_cache: bool = True,
        pool_size: int = 5,
    ):
        """
        Initialize RAG core.

        Args:
            db_path: Path to SQLite database. Uses default if not provided.
            model_path: Path to sentence-transformers model
            enable_model_cache: Cache embeddings for performance
            pool_size: Maximum number of connections in pool
        """
        if db_path is None:
            db_path = Path.home() / ".hermes" / "plugins" / "rag-memory" / "rag_core.db"

        self.db_path = db_path
        self.model_path = model_path
        self.enable_model_cache = enable_model_cache
        self.pool_size = pool_size

        # Lazy initialization (load on first use)
        self._model = None
        self._neural_enabled = None  # None = unknown, will be determined on first use
        self._embedding_dim = 384  # Default for all-MiniLM-L6-v2
        self._embedding_cache = {} if enable_model_cache else None

        # Performance features
        self._query_cache = QueryCache(max_size=1000, ttl=300)
        self._metrics = PerformanceMetrics()

        # Connection management
        self._local = threading.local()
        self._initialize_db()

        logger.info("✓ RAG core initialized")

    @contextmanager
    def _get_connection(self):
        """
        Get a database connection from the pool or create a new one.

        Uses thread-local storage for thread safety.
        """
        # Check if thread already has a connection
        if hasattr(self._local, "conn") and self._local.conn is not None:
            yield self._local.conn
            return

        # Create new connection for this thread
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # Load sqlite-vec extension
        try:
            conn.enable_load_extension(True)
            import sqlite_vec

            sqlite_vec.load(conn)
        except Exception as e:
            logger.warning(f"⚠ Failed to load sqlite-vec: {e}")

        self._local.conn = conn
        try:
            yield conn
        finally:
            # Don't close - keep for thread-local reuse
            pass

    def _initialize_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

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

            # Neural embeddings table (regular table for now)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS doc_embeddings (
                    doc_id TEXT PRIMARY KEY,
                    embedding BLOB,
                    model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)
            logger.info("✓ Neural embeddings table created")

            # Create indexes
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_namespace ON documents(namespace)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_tfidf_terms_term ON tfidf_terms(term)"
            )

            conn.commit()
            logger.info("✓ RAG core database initialized")

    def _load_model(self):
        """
        Load sentence-transformers model with lazy initialization.

        Called on first use to avoid startup delay.
        Falls back to TF-IDF only if model fails to load.
        """
        if self._neural_enabled is not None:
            return  # Already determined

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading model: {self.model_path}")
            self._model = SentenceTransformer(self.model_path)
            self._embedding_dim = self._model.get_sentence_embedding_dimension()
            self._neural_enabled = True
            logger.info(
                f"✓ Model loaded: {self.model_path} (dim={self._embedding_dim})"
            )
        except Exception as e:
            logger.warning(f"⚠ Model load failed, using TF-IDF only: {e}")
            self._neural_enabled = False
            self._model = None

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text.

        Args:
            text: Input text

        Returns:
            Embedding vector as list of floats, or None if neural disabled
        """
        # Try to load model if not yet determined
        if self._neural_enabled is None:
            self._load_model()

        if not self._neural_enabled:
            return None

        # Check cache first
        if self._embedding_cache is not None:
            cache_key = hashlib.md5(text.encode()).hexdigest()
            if cache_key in self._embedding_cache:
                return self._embedding_cache[cache_key]

        # Generate embedding
        try:
            import numpy as np

            embedding = self._model.encode(text, show_progress_bar=False)
            embedding_list = embedding.astype(np.float32).tolist()

            # Cache if enabled
            if self._embedding_cache is not None:
                cache_key = hashlib.md5(text.encode()).hexdigest()
                self._embedding_cache[cache_key] = embedding_list

            return embedding_list
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

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
        # Generate ID if not provided
        if not document_id:
            content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
            document_id = f"{namespace}_{content_hash}"

        # Prepare metadata
        metadata_json = json.dumps(metadata or {})

        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Insert document
                cursor.execute(
                    "INSERT INTO documents (id, namespace, content, metadata) VALUES (?, ?, ?, ?)",
                    (document_id, namespace, content, metadata_json),
                )

                # Index for TF-IDF
                self._index_tfidf(cursor, document_id, content)

                # Generate and store embedding
                # Try loading model if not yet determined
                if self._neural_enabled is None:
                    self._load_model()

                if self._neural_enabled:
                    embedding = self._generate_embedding(content)
                    if embedding is not None:
                        try:
                            import numpy as np

                            embedding_array = np.array(embedding, dtype=np.float32)
                            cursor.execute(
                                "INSERT INTO doc_embeddings (doc_id, embedding, model) VALUES (?, ?, ?)",
                                (
                                    document_id,
                                    embedding_array.tobytes(),
                                    self.model_path,
                                ),
                            )
                        except Exception as e:
                            logger.warning(f"⚠ Failed to store embedding: {e}")

                conn.commit()
                logger.debug(f"✓ Document added: {document_id}")

                return {"id": document_id, "namespace": namespace, "status": "added"}

            except sqlite3.IntegrityError:
                # Document already exists, update it
                cursor.execute(
                    "UPDATE documents SET content = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (content, metadata_json, document_id),
                )

                # Re-index TF-IDF
                cursor.execute(
                    "DELETE FROM tfidf_terms WHERE document_id = ?", (document_id,)
                )
                self._index_tfidf(cursor, document_id, content)

                # Update embedding
                # Try loading model if not yet determined
                if self._neural_enabled is None:
                    self._load_model()

                if self._neural_enabled:
                    embedding = self._generate_embedding(content)
                    if embedding is not None:
                        try:
                            import numpy as np

                            embedding_array = np.array(embedding, dtype=np.float32)
                            cursor.execute(
                                "UPDATE doc_embeddings SET embedding = ?, model = ? WHERE doc_id = ?",
                                (
                                    embedding_array.tobytes(),
                                    self.model_path,
                                    document_id,
                                ),
                            )
                        except Exception as e:
                            logger.warning(f"⚠ Failed to update embedding: {e}")

                conn.commit()
                logger.debug(f"✓ Document updated: {document_id}")

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
                    "INSERT OR REPLACE INTO tfidf_terms (document_id, term, frequency) VALUES (?, ?, ?)",
                    (document_id, term, freq),
                )

    def search(
        self,
        query: str,
        namespace: Optional[str] = None,
        mode: str = "hybrid",
        limit: int = 10,
        tokens: int = 500,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search RAG index.

        Args:
            query: Search query
            namespace: Optional namespace filter
            mode: 'hybrid', 'tfidf', or 'neural'
            limit: Max results
            tokens: Token budget for content truncation
            use_cache: Use query cache

        Returns:
            List of search results
        """
        start_time = time.time()

        # Check cache first
        if use_cache:
            cached = self._query_cache.get(query, namespace, mode)
            if cached is not None:
                self._metrics.record_search(time.time() - start_time, cached=True)
                return cached

        # Determine if neural is available
        if self._neural_enabled is None:
            self._load_model()

        if mode == "neural" and not self._neural_enabled:
            logger.warning(
                "⚠ Neural mode requested but not available, falling back to TF-IDF"
            )
            mode = "tfidf"

        if mode == "hybrid" and not self._neural_enabled:
            mode = "tfidf"

        if mode == "hybrid":
            # Fuse TF-IDF and neural results
            tfidf_results = self._search_tfidf(query, namespace, limit * 2)
            neural_results = self._search_neural(query, namespace, limit * 2)
            results = self._fuse_results(tfidf_results, neural_results, limit)
        elif mode == "neural":
            results = self._search_neural(query, namespace, limit)
        else:  # tfidf
            results = self._search_tfidf(query, namespace, limit)

        # Truncate content based on token budget
        avg_chars_per_token = 4
        char_limit = tokens * avg_chars_per_token

        for result in results:
            content = result.get("content", "")
            if len(content) > char_limit:
                result["content"] = content[:char_limit] + "..."
            result["_namespace"] = result.get("namespace", namespace or "default")

        results = results[:limit]

        # Cache results
        if use_cache:
            self._query_cache.set(query, namespace, mode, results)

        # Record metrics
        self._metrics.record_search(time.time() - start_time, cached=False)

        return results

    def _search_tfidf(
        self, query: str, namespace: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """
        Search using TF-IDF.

        Args:
            query: Search query
            namespace: Optional namespace filter
            limit: Max results

        Returns:
            List of results with scores
        """
        import re
        from collections import Counter

        with self._get_connection() as conn:
            cursor = conn.cursor()

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
                        "score": float(row[4]) if row[4] else 0.0,
                        "_mode": "tfidf",
                    }
                )

            return results

    def _search_neural(
        self, query: str, namespace: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """
        Search using neural embeddings.

        Args:
            query: Search query
            namespace: Optional namespace filter
            limit: Max results

        Returns:
            List of results with similarity scores
        """
        import numpy as np

        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        if query_embedding is None:
            return []

        query_array = np.array(query_embedding, dtype=np.float32)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get all embeddings (with optional namespace filter)
            if namespace:
                sql = """
                    SELECT d.id, d.namespace, d.content, d.metadata, e.embedding
                    FROM documents d
                    JOIN doc_embeddings e ON d.id = e.doc_id
                    WHERE d.namespace = ?
                """
                cursor.execute(sql, (namespace,))
            else:
                sql = """
                    SELECT d.id, d.namespace, d.content, d.metadata, e.embedding
                    FROM documents d
                    JOIN doc_embeddings e ON d.id = e.doc_id
                """
                cursor.execute(sql)

            rows = cursor.fetchall()

            # Calculate cosine similarity for each document
            results = []
            for row in rows:
                try:
                    # Load embedding from blob
                    doc_embedding_bytes = row[4]
                    doc_embedding = np.frombuffer(doc_embedding_bytes, dtype=np.float32)

                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_array, doc_embedding)

                    results.append(
                        {
                            "id": row[0],
                            "namespace": row[1],
                            "content": row[2],
                            "metadata": row[3],
                            "score": float(similarity),
                            "_mode": "neural",
                        }
                    )
                except Exception as e:
                    logger.debug(f"Failed to calculate similarity for {row[0]}: {e}")
                    continue

            # Sort by similarity score (descending)
            results.sort(key=lambda x: x["score"], reverse=True)

            return results[:limit]

    def _cosine_similarity(self, a: "np.ndarray", b: "np.ndarray") -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity score (0-1)
        """
        import numpy as np

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def _fuse_results(
        self, tfidf_results: List[Dict], neural_results: List[Dict], limit: int
    ) -> List[Dict]:
        """
        Fuse TF-IDF and neural results using Reciprocal Rank Fusion (RRF).

        Args:
            tfidf_results: Results from TF-IDF search
            neural_results: Results from neural search
            limit: Max results to return

        Returns:
            Fused and ranked results
        """
        # RRF constant (typically 60)
        k = 60

        # Score accumulator
        scores = {}

        # Add TF-IDF scores
        for rank, result in enumerate(tfidf_results):
            doc_id = result["id"]
            rrf_score = 1.0 / (k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score
            result["_rrf_score"] = scores[doc_id]

        # Add neural scores
        for rank, result in enumerate(neural_results):
            doc_id = result["id"]
            rrf_score = 1.0 / (k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score

            # Find result in tfidf_results or add it
            merged = next((r for r in tfidf_results if r["id"] == doc_id), None)
            if merged:
                merged["_rrf_score"] = scores[doc_id]
                merged["_mode"] = "hybrid"
            else:
                result["_rrf_score"] = scores[doc_id]
                result["_mode"] = "hybrid"
                tfidf_results.append(result)

        # Sort by RRF score
        tfidf_results.sort(key=lambda x: x.get("_rrf_score", 0), reverse=True)

        return tfidf_results[:limit]

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document dict or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT namespace FROM documents ORDER BY namespace"
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document by ID.

        Args:
            document_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            deleted = cursor.rowcount > 0
            conn.commit()

            if deleted:
                logger.debug(f"✓ Document deleted: {document_id}")

            return deleted

    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dict with stats
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Count documents
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]

            # Count namespaces
            cursor.execute("SELECT COUNT(DISTINCT namespace) FROM documents")
            ns_count = cursor.fetchone()[0]

            # Count TF-IDF terms
            cursor.execute("SELECT COUNT(*) FROM tfidf_terms")
            term_count = cursor.fetchone()[0]

            return {
                "documents": doc_count,
                "namespaces": ns_count,
                "tfidf_terms": term_count,
                "neural_enabled": self._neural_enabled,
                "model": self.model_path if self._neural_enabled else None,
                "cache_stats": self._query_cache.stats(),
                "performance": self._metrics.get_stats(),
            }

    def clear_cache(self):
        """Clear query cache"""
        self._query_cache.clear()
        logger.info("✓ Query cache cleared")

    def reset_metrics(self):
        """Reset performance metrics"""
        self._metrics.reset()
        logger.info("✓ Metrics reset")

    def close(self):
        """Close database connection(s)."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None
            logger.info("✓ RAG core connection closed")
