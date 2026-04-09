"""
Tool schemas for RAG Memory Plugin
These schemas define what the LLM sees and how it can call the tools.
"""

RAG_SEARCH = {
    "name": "rag_search",
    "description": (
        "Search the RAG memory system for relevant information. "
        "Supports three modes: 'hybrid' (TF-IDF + Neural, recommended), "
        "'tfidf' (fast, 1-5ms), 'neural' (semantic, 40-100ms). "
        "Results are automatically scoped by peer/session if provided. "
        "Use this when you need to find past information, context, "
        "or relevant knowledge from memory."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query or question"},
            "mode": {
                "type": "string",
                "enum": ["hybrid", "tfidf", "neural"],
                "default": "hybrid",
                "description": "Retrieval mode: hybrid (recommended), tfidf (fast), neural (semantic)",
            },
            "namespace": {
                "type": "string",
                "description": "Optional: Search within specific namespace (e.g., 'peer_alice', 'session_chat-1')",
            },
            "peer_id": {
                "type": "string",
                "description": "Optional: Search within peer's namespace (auto-converts to peer_<peer_id>)",
            },
            "session_id": {
                "type": "string",
                "description": "Optional: Search within session's namespace (auto-converts to session_<session_id>)",
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of results to return",
            },
            "tokens": {
                "type": "integer",
                "default": 500,
                "description": "Approximate token budget for results (trims content if needed)",
            },
        },
        "required": ["query"],
    },
}

RAG_ADD_DOCUMENT = {
    "name": "rag_add_document",
    "description": (
        "Add a document to RAG memory. "
        "Documents are automatically indexed with embeddings for semantic search. "
        "Supports namespace scoping by peer/session. "
        "Use this to store information, code, notes, or any content "
        "that should be searchable later."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Document content to add to memory",
            },
            "namespace": {
                "type": "string",
                "description": "Optional: Namespace to store in (e.g., 'peer_alice', 'session_chat-1')",
            },
            "peer_id": {
                "type": "string",
                "description": "Optional: Store in peer's namespace (auto-converts to peer_<peer_id>)",
            },
            "session_id": {
                "type": "string",
                "description": "Optional: Store in session's namespace (auto-converts to session_<session_id>)",
            },
            "metadata": {
                "type": "object",
                "description": "Optional: Metadata to attach (e.g., {'source': 'user', 'importance': 'high'})",
            },
            "document_id": {
                "type": "string",
                "description": "Optional: Custom document ID (auto-generated if not provided)",
            },
        },
        "required": ["content"],
    },
}

RAG_GET_PEER_CONTEXT = {
    "name": "rag_get_peer_context",
    "description": (
        "Get conversation context and history for a specific peer. "
        "Returns recent messages and optionally broader conversation context. "
        "Useful when you need to understand what a peer has been discussing "
        "or refresh context about past interactions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "peer_id": {
                "type": "string",
                "description": "Peer identifier to get context for",
            },
            "tokens": {
                "type": "integer",
                "default": 500,
                "description": "Approximate token budget (retrieves as many messages as fit)",
            },
            "include_metadata": {
                "type": "boolean",
                "default": False,
                "description": "Include peer metadata (name, preferences, etc.)",
            },
            "format": {
                "type": "string",
                "enum": ["text", "openai", "anthropic"],
                "default": "text",
                "description": "Output format: text (plain), openai (OpenAI messages), anthropic (Claude messages)",
            },
        },
        "required": ["peer_id"],
    },
}

RAG_GET_SESSION_CONTEXT = {
    "name": "rag_get_session_context",
    "description": (
        "Get full context of a session including all peer messages. "
        "Returns complete conversation history across all participants. "
        "Useful for reviewing past conversations or understanding "
        "the full context of a multi-party discussion."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Session identifier to get context for",
            },
            "limit": {
                "type": "integer",
                "default": 100,
                "description": "Maximum number of messages to return",
            },
            "format": {
                "type": "string",
                "enum": ["text", "openai", "anthropic"],
                "default": "text",
                "description": "Output format: text (plain), openai (OpenAI messages), anthropic (Claude messages)",
            },
            "include_metadata": {
                "type": "boolean",
                "default": False,
                "description": "Include session metadata (start time, participants, etc.)",
            },
        },
        "required": ["session_id"],
    },
}

RAG_START_SESSION = {
    "name": "rag_start_session",
    "description": (
        "Start a new session with multiple peers. "
        "Creates a session ID and associates it with specified peers. "
        "The session becomes the active session for auto-capture. "
        "Use this when beginning a new conversation or group discussion."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Optional: Custom session ID (auto-generated if not provided)",
            },
            "peer_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of peer IDs participating in the session",
            },
            "metadata": {
                "type": "object",
                "description": "Optional: Session metadata (e.g., {'topic': 'planning', 'platform': 'telegram'})",
            },
            "activate": {
                "type": "boolean",
                "default": True,
                "description": "Set as the active session for auto-capture (default: True)",
            },
        },
        "required": ["peer_ids"],
    },
}

RAG_END_SESSION = {
    "name": "rag_end_session",
    "description": (
        "End a session, flushing any buffered messages and finalizing the record. "
        "If session_id not provided, ends the currently active session. "
        "Use this when a conversation ends or you want to finalize capture."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Optional: Session ID to end (ends active session if not provided)",
            }
        },
    },
}

RAG_CAPTURE_MESSAGE = {
    "name": "rag_capture_message",
    "description": (
        "Capture a message with automatic peer and session tracking. "
        "Creates peers automatically if they don't exist. "
        "Adds to active session if session_id not provided. "
        "Supports metadata and custom timestamps. "
        "Use this to record messages for memory and context tracking."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "peer_id": {
                "type": "string",
                "description": "Peer identifier who sent the message",
            },
            "role": {
                "type": "string",
                "enum": ["user", "assistant", "system"],
                "default": "user",
                "description": "Message role: user, assistant, or system",
            },
            "content": {"type": "string", "description": "Message content"},
            "session_id": {
                "type": "string",
                "description": "Optional: Session ID (uses active session if not provided)",
            },
            "metadata": {
                "type": "object",
                "description": "Optional: Message metadata (e.g., {'source': 'telegram', 'platform': 'discord'})",
            },
            "timestamp": {
                "type": "string",
                "description": "Optional: ISO timestamp (default: current time)",
            },
        },
        "required": ["peer_id", "content"],
    },
}

RAG_LIST_PEERS = {
    "name": "rag_list_peers",
    "description": (
        "List all peers in memory. "
        "Returns peer IDs with optional metadata and statistics. "
        "Useful for discovering what peers exist or getting an overview "
        "of tracked participants."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 50,
                "description": "Maximum number of peers to return",
            },
            "include_stats": {
                "type": "boolean",
                "default": True,
                "description": "Include peer statistics (message count, sessions, etc.)",
            },
            "filter_metadata": {
                "type": "object",
                "description": "Optional: Filter by metadata (e.g., {'platform': 'telegram'})",
            },
        },
    },
}

RAG_LIST_SESSIONS = {
    "name": "rag_list_sessions",
    "description": (
        "List all sessions in memory. "
        "Returns session IDs with optional metadata and participant info. "
        "Useful for discovering past sessions or getting an overview "
        "of recorded conversations."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 50,
                "description": "Maximum number of sessions to return",
            },
            "peer_id": {
                "type": "string",
                "description": "Optional: Filter sessions by peer ID",
            },
            "include_messages": {
                "type": "boolean",
                "default": False,
                "description": "Include session messages (warning: can be large)",
            },
            "include_metadata": {
                "type": "boolean",
                "default": True,
                "description": "Include session metadata",
            },
        },
    },
}
