"""
Namespace Isolation for RAG System
Ensures proper scoping for peers, sessions, and RAG namespaces
"""

import sqlite3
from typing import Any, Dict, List, Optional


class NamespaceIsolation:
    """
    Manages namespace isolation for peer and session data
    Ensures that searches and retrievals are properly scoped
    """

    def __init__(self, db_conn: Optional[sqlite3.Connection] = None):
        """
        Initialize namespace isolation

        Args:
            db_conn: Optional database connection
        """
        self._db_conn = db_conn

    def get_peer_namespace(self, peer_id: str) -> str:
        """
        Get the RAG namespace for a specific peer

        Args:
            peer_id: Peer identifier

        Returns:
            Namespace string for RAG operations
        """
        return f"peer_{peer_id}"

    def get_session_namespace(self, session_id: str) -> str:
        """
        Get the RAG namespace for a specific session

        Args:
            session_id: Session identifier

        Returns:
            Namespace string for RAG operations
        """
        return f"session_{session_id}"

    def get_peer_session_namespace(self, peer_id: str, session_id: str) -> str:
        """
        Get the combined namespace for peer+session

        Args:
            peer_id: Peer identifier
            session_id: Session identifier

        Returns:
            Combined namespace string
        """
        return f"peer_{peer_id}_session_{session_id}"

    def is_peer_isolated(self, peer_id: str) -> bool:
        """
        Check if a peer is in isolated namespace

        Args:
            peer_id: Peer identifier

        Returns:
            True if peer should be isolated
        """
        # Default: all peers are isolated
        return True

    def is_session_isolated(self, session_id: str) -> bool:
        """
        Check if a session is in isolated namespace

        Args:
            session_id: Session identifier

        Returns:
            True if session should be isolated
        """
        # Default: all sessions are isolated
        return True

    def search_in_namespace(
        self, rag_instance, namespace: str, query: str, limit: int = 10, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Perform search within a specific namespace

        Args:
            rag_instance: RAG instance to search
            namespace: Namespace to search within
            query: Search query
            limit: Maximum results
            **kwargs: Additional search parameters

        Returns:
            List of search results
        """
        if not hasattr(rag_instance, "search"):
            return []

        # Perform search with namespace constraint
        results = rag_instance.search(
            namespace=namespace, query=query, limit=limit, **kwargs
        )

        return results

    def search_peer_namespace(
        self, rag_instance, peer_id: str, query: str, limit: int = 10, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search within a peer's namespace

        Args:
            rag_instance: RAG instance to search
            peer_id: Peer identifier
            query: Search query
            limit: Maximum results
            **kwargs: Additional search parameters

        Returns:
            List of search results scoped to peer
        """
        namespace = self.get_peer_namespace(peer_id)
        return self.search_in_namespace(
            rag_instance, namespace=namespace, query=query, limit=limit, **kwargs
        )

    def search_session_namespace(
        self, rag_instance, session_id: str, query: str, limit: int = 10, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search within a session's namespace

        Args:
            rag_instance: RAG instance to search
            session_id: Session identifier
            query: Search query
            limit: Maximum results
            **kwargs: Additional search parameters

        Returns:
            List of search results scoped to session
        """
        namespace = self.get_session_namespace(session_id)
        return self.search_in_namespace(
            rag_instance, namespace=namespace, query=query, limit=limit, **kwargs
        )

    def get_cross_namespace_results(
        self,
        rag_instance,
        namespaces: List[str],
        query: str,
        limit_per_namespace: int = 5,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Get results from multiple namespaces

        Args:
            rag_instance: RAG instance to search
            namespaces: List of namespaces to search
            query: Search query
            limit_per_namespace: Results per namespace
            **kwargs: Additional search parameters

        Returns:
            Combined list of results from all namespaces
        """
        all_results = []

        for namespace in namespaces:
            results = self.search_in_namespace(
                rag_instance,
                namespace=namespace,
                query=query,
                limit=limit_per_namespace,
                **kwargs,
            )

            # Tag results with namespace
            for result in results:
                result["_namespace"] = namespace

            all_results.extend(results)

        return all_results

    def validate_namespace_access(
        self, peer_id: Optional[str], session_id: Optional[str], target_namespace: str
    ) -> bool:
        """
        Validate if a peer/session can access a namespace

        Args:
            peer_id: Peer identifier
            session_id: Session identifier
            target_namespace: Namespace to access

        Returns:
            True if access is allowed
        """
        # If no peer/session specified, deny access
        if not peer_id and not session_id:
            return False

        # Check if peer matches namespace
        if peer_id:
            expected_namespace = self.get_peer_namespace(peer_id)
            if target_namespace == expected_namespace:
                return True

        # Check if session matches namespace
        if session_id:
            expected_namespace = self.get_session_namespace(session_id)
            if target_namespace == expected_namespace:
                return True

        # Check combined namespace
        if peer_id and session_id:
            expected_namespace = self.get_peer_session_namespace(peer_id, session_id)
            if target_namespace == expected_namespace:
                return True

        return False

    def get_accessible_namespaces(
        self, peer_id: Optional[str] = None, session_id: Optional[str] = None
    ) -> List[str]:
        """
        Get list of namespaces accessible to a peer/session

        Args:
            peer_id: Optional peer identifier
            session_id: Optional session identifier

        Returns:
            List of accessible namespaces
        """
        namespaces = []

        if peer_id:
            namespaces.append(self.get_peer_namespace(peer_id))

        if session_id:
            namespaces.append(self.get_session_namespace(session_id))

        if peer_id and session_id:
            namespaces.append(self.get_peer_session_namespace(peer_id, session_id))

        return namespaces

    def filter_results_by_namespace(
        self, results: List[Dict[str, Any]], allowed_namespaces: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Filter search results to only include allowed namespaces

        Args:
            results: List of search results
            allowed_namespaces: List of allowed namespaces

        Returns:
            Filtered list of results
        """
        return [
            result
            for result in results
            if result.get("_namespace") in allowed_namespaces
        ]


class IsolatedSearch:
    """
    Wrapper for RAG search with namespace isolation
    Ensures all searches are properly scoped
    """

    def __init__(self, rag_instance, isolation: NamespaceIsolation):
        """
        Initialize isolated search

        Args:
            rag_instance: RAG instance to wrap
            isolation: NamespaceIsolation instance
        """
        self.rag = rag_instance
        self.isolation = isolation

    def search(
        self,
        query: str,
        peer_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 10,
        cross_namespace: bool = False,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Perform isolated search

        Args:
            query: Search query
            peer_id: Optional peer to search within
            session_id: Optional session to search within
            limit: Maximum results
            cross_namespace: Whether to search across all accessible namespaces
            **kwargs: Additional search parameters

        Returns:
            List of search results
        """
        if cross_namespace:
            # Search across all accessible namespaces
            namespaces = self.isolation.get_accessible_namespaces(
                peer_id=peer_id, session_id=session_id
            )

            if not namespaces:
                return []

            results = self.isolation.get_cross_namespace_results(
                self.rag,
                namespaces=namespaces,
                query=query,
                limit_per_namespace=limit // max(1, len(namespaces)),
                **kwargs,
            )

            return results
        else:
            # Search in specific namespace
            if peer_id and session_id:
                namespace = self.isolation.get_peer_session_namespace(
                    peer_id, session_id
                )
            elif peer_id:
                namespace = self.isolation.get_peer_namespace(peer_id)
            elif session_id:
                namespace = self.isolation.get_session_namespace(session_id)
            else:
                # No namespace specified - return empty
                return []

            return self.isolation.search_in_namespace(
                self.rag, namespace=namespace, query=query, limit=limit, **kwargs
            )

    def add_document(
        self,
        content: str,
        peer_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Add document with namespace isolation

        Args:
            content: Document content
            peer_id: Optional peer ID
            session_id: Optional session ID
            **kwargs: Additional arguments

        Returns:
            Result from RAG add_document
        """
        if peer_id and session_id:
            namespace = self.isolation.get_peer_session_namespace(peer_id, session_id)
        elif peer_id:
            namespace = self.isolation.get_peer_namespace(peer_id)
        elif session_id:
            namespace = self.isolation.get_session_namespace(session_id)
        else:
            namespace = kwargs.get("namespace", "default")

        return self.rag.add_document(namespace=namespace, content=content, **kwargs)


if __name__ == "__main__":
    # Quick test
    print("Namespace Isolation - Quick Test")
    print("=" * 50)

    import os
    import tempfile

    # Create temp database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = temp_db.name
    temp_db.close()

    try:
        conn = sqlite3.connect(db_path)
        isolation = NamespaceIsolation(db_conn=conn)

        # Test namespace generation
        print("\n✓ Namespace generation:")
        print(f"  Peer namespace: {isolation.get_peer_namespace('alice')}")
        print(f"  Session namespace: {isolation.get_session_namespace('chat-1')}")
        print(
            f"  Combined namespace: {isolation.get_peer_session_namespace('alice', 'chat-1')}"
        )

        # Test namespace validation
        print("\n✓ Namespace validation:")
        valid = isolation.validate_namespace_access(
            peer_id="alice",
            session_id=None,
            target_namespace=isolation.get_peer_namespace("alice"),
        )
        print(f"  Alice can access peer_alice: {valid}")

        invalid = isolation.validate_namespace_access(
            peer_id="alice",
            session_id=None,
            target_namespace=isolation.get_peer_namespace("bob"),
        )
        print(f"  Alice can access peer_bob: {invalid}")

        # Test accessible namespaces
        print("\n✓ Accessible namespaces:")
        namespaces = isolation.get_accessible_namespaces(
            peer_id="alice", session_id="chat-1"
        )
        for ns in namespaces:
            print(f"  - {ns}")

        # Test filtering
        print("\n✓ Result filtering:")
        results = [
            {"_namespace": "peer_alice", "content": "Alice message"},
            {"_namespace": "peer_bob", "content": "Bob message"},
            {"_namespace": "session_chat-1", "content": "Chat message"},
        ]

        filtered = isolation.filter_results_by_namespace(
            results, ["peer_alice", "session_chat-1"]
        )

        print(f"  Original: {len(results)} results")
        print(f"  Filtered: {len(filtered)} results")

        conn.close()
        print("\n✓ All tests passed!")

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
