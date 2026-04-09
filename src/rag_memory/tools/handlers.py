"""
Tool handlers for RAG Memory Plugin
These are the functions that execute when the LLM calls the tools.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


# These will be initialized in __init__.py
_peer_manager = None
_session_manager = None
_auto_capture = None
_isolation = None
_rag_core = None


def set_managers(peer_manager, session_manager, auto_capture, isolation, rag_core):
    """Initialize tool handlers with manager instances."""
    global _peer_manager, _session_manager, _auto_capture, _isolation, _rag_core
    _peer_manager = peer_manager
    _session_manager = session_manager
    _auto_capture = auto_capture
    _isolation = isolation
    _rag_core = rag_core


def rag_search(args: Dict[str, Any], **kwargs) -> str:
    """Search RAG memory for relevant information."""
    try:
        query = args.get("query", "")
        mode = args.get("mode", "hybrid")
        limit = args.get("limit", 10)
        tokens = args.get("tokens", 500)

        # Determine namespace
        namespace = args.get("namespace")
        peer_id = args.get("peer_id")
        session_id = args.get("session_id")

        # Build namespace from peer/session if provided
        if not namespace:
            if peer_id and session_id:
                namespace = _isolation.get_peer_session_namespace(peer_id, session_id)
            elif peer_id:
                namespace = _isolation.get_peer_namespace(peer_id)
            elif session_id:
                namespace = _isolation.get_session_namespace(session_id)

        # Perform search
        if _rag_core and hasattr(_rag_core, "search"):
            results = _rag_core.search(
                query=query, namespace=namespace, mode=mode, limit=limit, tokens=tokens
            )
        else:
            results = []

        # Format results
        if not results:
            return f"No results found for query: '{query}'"

        output = [f"Found {len(results)} results for: '{query}'\n"]
        for i, result in enumerate(results[:limit], 1):
            content = result.get("content", "")[:500]  # Truncate long content
            score = result.get("score", 0)
            ns = result.get("_namespace", namespace)

            output.append(f"\n{i}. [{ns}] (score: {score:.2f})")
            output.append(f"   {content}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Error in rag_search: {e}")
        return f"Error searching RAG: {str(e)}"


def rag_add_document(args: Dict[str, Any], **kwargs) -> str:
    """Add a document to RAG memory."""
    try:
        content = args.get("content", "")
        metadata = args.get("metadata", {})
        document_id = args.get("document_id")

        # Determine namespace
        namespace = args.get("namespace")
        peer_id = args.get("peer_id")
        session_id = args.get("session_id")

        if not namespace:
            if peer_id and session_id:
                namespace = _isolation.get_peer_session_namespace(peer_id, session_id)
            elif peer_id:
                namespace = _isolation.get_peer_namespace(peer_id)
            elif session_id:
                namespace = _isolation.get_session_namespace(session_id)
            else:
                namespace = "default"

        # Add document
        if _rag_core and hasattr(_rag_core, "add_document"):
            result = _rag_core.add_document(
                content=content,
                namespace=namespace,
                metadata=metadata,
                document_id=document_id,
            )
            doc_id = result.get("id", document_id)
            return f"✓ Document added to namespace '{namespace}' (ID: {doc_id})"
        else:
            return "RAG core not available - document not added"

    except Exception as e:
        logger.error(f"Error in rag_add_document: {e}")
        return f"Error adding document: {str(e)}"


def rag_get_peer_context(args: Dict[str, Any], **kwargs) -> str:
    """Get conversation context for a peer."""
    try:
        peer_id = args.get("peer_id", "")
        tokens = args.get("tokens", 500)
        include_metadata = args.get("include_metadata", False)
        format = args.get("format", "text")

        if not peer_id:
            return "Error: peer_id is required"

        # Get peer
        peer = _peer_manager.get_peer(peer_id)
        if not peer:
            return f"Peer '{peer_id}' not found"

        # Get context
        context = peer.get_context(tokens=tokens)

        # Format output
        if format == "openai":
            messages = peer.to_openai(limit=tokens // 50)  # Rough estimate
            return f"Peer context ({peer_id}):\n{str(messages)}"
        elif format == "anthropic":
            messages = peer.to_anthropic(limit=tokens // 50)
            return f"Peer context ({peer_id}):\n{str(messages)}"
        else:
            output = [f"Peer context for: {peer_id}"]
            output.append(f"Total messages: {len(peer._messages_cache)}")
            output.append(f"Sessions: {len(peer._sessions_cache)}")

            if include_metadata and peer._metadata:
                output.append(f"\nMetadata: {peer._metadata}")

            output.append(f"\nContext:\n{context}")
            return "\n".join(output)

    except Exception as e:
        logger.error(f"Error in rag_get_peer_context: {e}")
        return f"Error getting peer context: {str(e)}"


def rag_get_session_context(args: Dict[str, Any], **kwargs) -> str:
    """Get context of a session."""
    try:
        session_id = args.get("session_id", "")
        limit = args.get("limit", 100)
        include_metadata = args.get("include_metadata", False)
        format = args.get("format", "text")

        if not session_id:
            return "Error: session_id is required"

        # Get session
        session = _session_manager.get_session(session_id)
        if not session:
            return f"Session '{session_id}' not found"

        # Format output
        output = [f"Session: {session_id}"]
        output.append(f"Peers: {len(session._peers)}")
        output.append(f"Messages: {len(session._messages)}")

        if include_metadata:
            output.append(f"Started: {session._start_time}")
            output.append(f"Ended: {session._end_time or 'Active'}")
            output.append(f"Peers: {', '.join(session._peers)}")

        if format == "openai":
            messages = session.to_openai(limit=limit)
            output.append(f"\nOpenAI format:\n{str(messages)}")
        elif format == "anthropic":
            messages = session.to_anthropic(limit=limit)
            output.append(f"\nAnthropic format:\n{str(messages)}")
        else:
            output.append("\nRecent messages:")
            for msg in session._messages[-limit:]:
                role = msg.get("role", "unknown")
                peer = msg.get("peer_id", "unknown")
                content = msg.get("content", "")[:200]
                output.append(f"[{peer}/{role}]: {content}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Error in rag_get_session_context: {e}")
        return f"Error getting session context: {str(e)}"


def rag_start_session(args: Dict[str, Any], **kwargs) -> str:
    """Start a new session with multiple peers."""
    try:
        session_id = args.get("session_id")
        peer_ids = args.get("peer_ids", [])
        metadata = args.get("metadata", {})
        activate = args.get("activate", True)

        if not peer_ids:
            return "Error: peer_ids is required"

        # Start session
        session = _auto_capture.start_session(
            session_id=session_id, peer_ids=peer_ids, metadata=metadata
        )

        if activate:
            _auto_capture.set_active_session(session.session_id)

        output = [f"✓ Session started: {session.session_id}"]
        output.append(f"Peers: {', '.join(peer_ids)}")
        output.append(f"Active: {activate}")

        if metadata:
            output.append(f"Metadata: {metadata}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Error in rag_start_session: {e}")
        return f"Error starting session: {str(e)}"


def rag_end_session(args: Dict[str, Any], **kwargs) -> str:
    """End a session."""
    try:
        session_id = args.get("session_id")

        # If no session_id provided, end active session
        if not session_id:
            active = _auto_capture.get_active_session()
            if active:
                session_id = active.get("session_id")
            else:
                return "No active session to end"

        if not session_id:
            return "No session ID provided and no active session found"

        # End session
        _auto_capture.end_session(session_id)

        return f"✓ Session ended: {session_id}"

    except Exception as e:
        logger.error(f"Error in rag_end_session: {e}")
        return f"Error ending session: {str(e)}"


def rag_capture_message(args: Dict[str, Any], **kwargs) -> str:
    """Capture a message with automatic peer/session tracking."""
    try:
        peer_id = args.get("peer_id", "")
        role = args.get("role", "user")
        content = args.get("content", "")
        session_id = args.get("session_id")
        metadata = args.get("metadata", {})
        timestamp = args.get("timestamp")

        if not peer_id:
            return "Error: peer_id is required"
        if not content:
            return "Error: content is required"

        # Capture message
        result = _auto_capture.capture_message(
            peer_id=peer_id,
            role=role,
            content=content,
            session_id=session_id,
            metadata=metadata,
            timestamp=timestamp,
        )

        output = [f"✓ Message captured from: {peer_id}"]
        output.append(f"Session: {result.get('session_id', 'N/A')}")
        output.append(f"Role: {role}")
        output.append(f"Content length: {len(content)} chars")

        if metadata:
            output.append(f"Metadata: {metadata}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Error in rag_capture_message: {e}")
        return f"Error capturing message: {str(e)}"


def rag_list_peers(args: Dict[str, Any], **kwargs) -> str:
    """List all peers in memory."""
    try:
        limit = args.get("limit", 50)
        include_stats = args.get("include_stats", True)
        filter_metadata = args.get("filter_metadata")

        # List peers
        peers = _auto_capture.list_peers(limit=limit)

        # Filter by metadata if provided
        if filter_metadata and peers:
            filtered = []
            for peer in peers:
                peer_meta = peer.get("metadata", {})
                if all(peer_meta.get(k) == v for k, v in filter_metadata.items()):
                    filtered.append(peer)
            peers = filtered

        if not peers:
            return "No peers found"

        output = [f"Peers ({len(peers)}):"]
        for peer in peers[:limit]:
            peer_id = peer.get("peer_id", "unknown")

            if include_stats:
                stats = _auto_capture.get_peer_stats(peer_id)
                msg_count = stats.get("total_messages", 0)
                session_count = stats.get("total_sessions", 0)
                output.append(
                    f"  - {peer_id} ({msg_count} messages, {session_count} sessions)"
                )
            else:
                output.append(f"  - {peer_id}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Error in rag_list_peers: {e}")
        return f"Error listing peers: {str(e)}"


def rag_list_sessions(args: Dict[str, Any], **kwargs) -> str:
    """List all sessions in memory."""
    try:
        limit = args.get("limit", 50)
        peer_id = args.get("peer_id")
        include_messages = args.get("include_messages", False)
        include_metadata = args.get("include_metadata", True)

        # List sessions
        sessions = _auto_capture.list_sessions(limit=limit, peer_id=peer_id)

        if not sessions:
            return "No sessions found"

        output = [f"Sessions ({len(sessions)}):"]
        for session in sessions[:limit]:
            session_id = session.get("session_id", "unknown")
            peer_count = len(session.get("_peers", {}))
            msg_count = len(session.get("_messages", []))

            output.append(f"\n  {session_id}")
            output.append(f"    Peers: {peer_count}, Messages: {msg_count}")

            if include_metadata:
                start_time = session.get("_start_time")
                if start_time:
                    output.append(f"    Started: {start_time}")

            if include_messages:
                output.append("    Messages:")
                for msg in session.get("_messages", [])[-5:]:  # Last 5
                    peer = msg.get("peer_id", "unknown")
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")[:50]
                    output.append(f"      [{peer}/{role}]: {content}...")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Error in rag_list_sessions: {e}")
        return f"Error listing sessions: {str(e)}"


# Hook functions for lifecycle events


def inject_context(ctx, **kwargs):
    """
    Pre-LLM call hook: Inject peer/session context.
    Returns context dict that gets added to system prompt.
    """
    try:
        # Check if we have active session
        active = _auto_capture.get_active_session()

        if not active:
            return {}

        session_id = active.get("session_id")

        # Get session context
        session = _session_manager.get_session(session_id)
        if not session:
            return {}

        # Get context for each peer in session
        context_parts = []

        for peer_id in session._peers:
            peer = _peer_manager.get_peer(peer_id)
            if peer and len(peer._messages_cache) > 0:
                last_message = peer._messages_cache[-1]
                if last_message:
                    role = last_message.get("role", "unknown")
                    content = last_message.get("content", "")[:200]
                    context_parts.append(f"{peer_id} ({role}): {content}...")

        if context_parts:
            context_str = "\n".join(context_parts)
            return {"context": f"Recent conversation context:\n{context_str}"}

        return {}

    except Exception as e:
        logger.error(f"Error in inject_context hook: {e}")
        return {}


def capture_output(ctx, tool_name, args, result, **kwargs):
    """
    Post-tool call hook: Capture tool outputs automatically.
    Records messages and tool calls to memory.
    """
    try:
        # Skip capturing our own RAG tools (avoid infinite recursion)
        if tool_name.startswith("rag_"):
            return

        # Try to get peer/session from context
        # This is simplified - real implementation would use ctx to get current peer/session
        active = _auto_capture.get_active_session()
        if not active:
            return

        session_id = active.get("session_id")

        # For now, just log that we captured a tool call
        logger.info(f"Captured tool call: {tool_name} in session {session_id}")

    except Exception as e:
        logger.error(f"Error in capture_output hook: {e}")
