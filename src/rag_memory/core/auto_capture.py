"""
Automatic Peer Tracking for RAG System
Integrates Peer/Session model with auto-capture functionality
"""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

# Handle both plugin context and test context
try:
    # Plugin context: relative import
    from ..models import Peer, PeerManager, Session, SessionManager
except ImportError:
    # Test context: absolute import
    from models import PeerManager, Session, SessionManager


class AutoPeerCapture:
    """
    Automatically tracks peers and sessions during message capture
    Integrates with RAG auto-capture for seamless peer management
    """

    def __init__(
        self,
        db_path: str = "rag_data.db",
        peer_manager: Optional[PeerManager] = None,
        session_manager: Optional[SessionManager] = None,
    ):
        """
        Initialize auto peer capture

        Args:
            db_path: Path to RAG database
            peer_manager: Optional existing PeerManager
            session_manager: Optional existing SessionManager
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, timeout=30.0)
        self.conn.row_factory = sqlite3.Row

        # Initialize managers
        self.peer_manager = peer_manager or PeerManager(db_conn=self.conn)
        self.session_manager = session_manager or SessionManager(db_conn=self.conn)

        # Track active session
        self._active_session_id: Optional[str] = None

        # Message buffer for batch processing
        self._message_buffer: List[Dict[str, Any]] = []
        self._buffer_flush_threshold = 5

        print("✓ Auto Peer Capture initialized")

    def capture_message(
        self,
        peer_id: str,
        role: str,
        content: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Capture a message with automatic peer and session tracking

        Args:
            peer_id: Peer identifier (auto-created if not exists)
            role: Message role (user, assistant, system)
            content: Message content
            session_id: Optional session ID (auto-created if not provided)
            metadata: Optional message metadata

        Returns:
            Captured message dict with peer and session info
        """
        timestamp = datetime.now()

        # Ensure peer exists
        peer = self.peer_manager.get_peer(peer_id)
        if not peer:
            peer = self.peer_manager.create_peer(
                peer_id=peer_id,
                metadata={"auto_created": True, "created_at": timestamp.isoformat()},
            )

        # Ensure session exists
        session_id = session_id or self._active_session_id
        if not session_id:
            session_id = f"auto_session_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}"
            self._active_session_id = session_id

        session = self.session_manager.get_session(session_id)
        if not session:
            session = self.session_manager.create_session(session_id)
            session.add_peers([peer])

        # Ensure peer is in session
        if peer_id not in session._peers:
            session.add_peers([peer])

        # Add message to buffer
        message = {
            "peer_id": peer_id,
            "role": role,
            "content": content,
            "session_id": session_id,
            "timestamp": timestamp,
            "metadata": metadata or {},
        }

        self._message_buffer.append(message)

        # Add to peer and session
        peer.add_message(
            role=role,
            content=content,
            session_id=session_id,
            timestamp=timestamp,
            metadata=metadata,
        )

        # Add to session (don't double-add to peer)
        session._messages.append(
            {
                "id": f"{session_id}_{len(session._messages)}_{int(timestamp.timestamp())}",
                "session_id": session_id,
                "peer_id": peer_id,
                "role": role,
                "content": content,
                "timestamp": timestamp.isoformat(),
                "metadata": metadata or {},
            }
        )

        # Flush buffer if threshold reached
        if len(self._message_buffer) >= self._buffer_flush_threshold:
            self.flush_buffer()

        return {**message, "peer": peer.to_dict(), "session": session.to_dict()}

    def start_session(
        self,
        session_id: str,
        peer_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Start a new session with specified peers

        Args:
            session_id: Session identifier
            peer_ids: List of peer IDs to include
            metadata: Optional session metadata

        Returns:
            Session instance
        """
        # Create or get peers
        peers = []
        for peer_id in peer_ids:
            peer = self.peer_manager.get_peer(peer_id)
            if not peer:
                peer = self.peer_manager.create_peer(
                    peer_id=peer_id, metadata={"auto_created": True}
                )
            peers.append(peer)

        # Create session
        session = self.session_manager.create_session(session_id, metadata)
        session.add_peers(peers)

        self._active_session_id = session_id

        return session

    def end_session(self, session_id: Optional[str] = None) -> None:
        """
        End a session and flush buffer

        Args:
            session_id: Optional session ID (defaults to active session)
        """
        session_id = session_id or self._active_session_id
        if session_id:
            self.flush_buffer()
            if session_id == self._active_session_id:
                self._active_session_id = None

    def flush_buffer(self) -> List[Dict[str, Any]]:
        """
        Flush message buffer to persistent storage

        Returns:
            List of flushed messages
        """
        if not self._message_buffer:
            return []

        flushed = list(self._message_buffer)
        self._message_buffer.clear()

        # Here you would integrate with the main RAG database
        # For now, peer and session managers handle persistence

        return flushed

    def get_peer_context(
        self, peer_id: str, tokens: int = 2000, session_id: Optional[str] = None
    ) -> str:
        """
        Get conversation context for a specific peer

        Args:
            peer_id: Peer identifier
            tokens: Token limit for context
            session_id: Optional filter by session

        Returns:
            Formatted context string
        """
        peer = self.peer_manager.get_peer(peer_id)
        if not peer:
            return ""

        return peer.get_context(tokens=tokens, session_id=session_id)

    def get_session_context(
        self,
        session_id: str,
        summary: bool = True,
        tokens: int = 2000,
        include_system: bool = False,
    ) -> "SessionContext":
        """
        Get session context for LLM consumption

        Args:
            session_id: Session identifier
            summary: Include session summary
            tokens: Token limit
            include_system: Include system messages

        Returns:
            SessionContext object
        """
        from session import SessionContext

        session = self.session_manager.get_session(session_id)
        if not session:
            return SessionContext(session_id, [], None)

        return session.context(
            summary=summary, tokens=tokens, include_system=include_system
        )

    def search_peer(
        self, peer_id: str, query: str, limit: int = 5, session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search within a peer's messages

        Args:
            peer_id: Peer identifier
            query: Search query
            limit: Maximum results
            session_id: Optional filter by session

        Returns:
            List of matching messages
        """
        peer = self.peer_manager.get_peer(peer_id)
        if not peer:
            return []

        return peer.search(query=query, limit=limit, session_id=session_id)

    def list_peers(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all peers

        Args:
            limit: Optional maximum peers to return

        Returns:
            List of peer dictionaries
        """
        peers = self.peer_manager.list_peers()
        return (
            [peer.to_dict() for peer in peers[:limit]]
            if limit
            else [peer.to_dict() for peer in peers]
        )

    def list_sessions(
        self, peer_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List sessions, optionally filtered by peer

        Args:
            peer_id: Optional filter by peer ID
            limit: Optional maximum sessions to return

        Returns:
            List of session dictionaries
        """
        sessions = self.session_manager.list_sessions(peer_id=peer_id, limit=limit)
        return [session.to_dict() for session in sessions]

    def get_active_session(self) -> Optional[Dict[str, Any]]:
        """Get the active session"""
        if not self._active_session_id:
            return None

        session = self.session_manager.get_session(self._active_session_id)
        return session.to_dict() if session else None

    def set_active_session(self, session_id: str) -> None:
        """Set the active session"""
        self._active_session_id = session_id

    def get_peer_stats(self, peer_id: str) -> Dict[str, Any]:
        """
        Get statistics for a peer

        Args:
            peer_id: Peer identifier

        Returns:
            Dictionary with peer statistics
        """
        peer = self.peer_manager.get_peer(peer_id)
        if not peer:
            return {}

        sessions = peer.get_sessions(limit=1000)
        total_messages = sum(s["message_count"] for s in sessions)

        return {
            "peer_id": peer_id,
            "total_messages": total_messages,
            "total_sessions": len(sessions),
            "metadata": peer.get_metadata(),
            "recent_sessions": sessions[:5],
        }

    def cleanup(self) -> None:
        """Cleanup resources"""
        self.flush_buffer()
        self.conn.close()


if __name__ == "__main__":
    # Quick test
    print("Auto Peer Capture - Quick Test")
    print("=" * 50)

    import os
    import tempfile

    # Create temp database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = temp_db.name
    temp_db.close()

    try:
        # Initialize auto capture
        auto = AutoPeerCapture(db_path=db_path)

        # Start a session
        session = auto.start_session(
            session_id="test-session-1",
            peer_ids=["alice", "bob", "assistant"],
            metadata={"type": "test"},
        )

        print(f"\n✓ Created session: {session.session_id}")
        print(f"  Peers: {', '.join(session.get_peer_ids())}")

        # Capture messages
        auto.capture_message("alice", "user", "Hello Bob!")
        auto.capture_message("bob", "user", "Hi Alice!")
        auto.capture_message("assistant", "assistant", "How can I help?")

        print("\n✓ Captured 3 messages")

        # Get peer context
        alice_context = auto.get_peer_context("alice", tokens=500)
        print(f"\nAlice's context:\n{alice_context}")

        # Get session context
        session_ctx = auto.get_session_context("test-session-1")
        print(f"\nSession context: {len(session_ctx.messages)} messages")

        # List peers
        peers = auto.list_peers()
        print(f"\n✓ Total peers: {len(peers)}")
        for peer in peers:
            print(f"  - {peer['peer_id']}: {peer['message_count']} messages")

        # List sessions
        sessions = auto.list_sessions()
        print(f"\n✓ Total sessions: {len(sessions)}")

        # Get peer stats
        alice_stats = auto.get_peer_stats("alice")
        print("\nAlice's stats:")
        print(f"  - Total messages: {alice_stats['total_messages']}")
        print(f"  - Total sessions: {alice_stats['total_sessions']}")

        # End session
        auto.end_session()

        print("\n✓ All tests passed!")

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
