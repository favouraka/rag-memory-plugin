"""Hermes Agent plugin registration for RAG Memory.

This module implements the ``register()`` function that Hermes calls when
loading plugins via the ``hermes_agent.plugins`` entry point.

The plugin integrates with Hermes via three mechanisms:
1. **Tools** - rag_search, rag_add, rag_stats, rag_flush (registered to agent)
2. **Hooks** - pre_llm_call (inject context), post_llm_call (capture)
3. **State** - RAGCore instance stored in plugin context for tool access

Configuration
-------------
Plugin config is read from Hermes config.yaml under ``plugins.rag_memory``::

    plugins:
      rag_memory:
        enabled: true
        mode: hybrid              # tfidf | neural | hybrid
        auto_capture: true
        cache_enabled: true
        max_results: 10

Migration Support
-----------------
On first load, the plugin automatically detects and offers to migrate data
from the legacy ~/rag-system directory if it exists.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rag_memory.core import RAGCore

logger = logging.getLogger(__name__)

__all__ = [
    "register",
    "plugin_name",
    "plugin_version",
]

# --------------------------------------------------------------------------- #
# Plugin metadata (required by Hermes plugin system)
# --------------------------------------------------------------------------- #

plugin_name = "rag-memory"
plugin_version = "1.0.0"

# --------------------------------------------------------------------------- #
# Module-level state (initialized in register())
# --------------------------------------------------------------------------- #

_rag: "RAGCore | None" = None
_config: dict[str, Any] = {}
_initialized: bool = False


# --------------------------------------------------------------------------- #
# Plugin registration
# --------------------------------------------------------------------------- #

def register(context: Any) -> None:
    """Initialize the RAG Memory plugin.

    Called by the Hermes plugin manager with a PluginContext that provides
    ``register_hook``, ``register_tool``, and ``config``.

    The function is named ``register`` to match the Hermes plugin contract.

    Args:
        context: Hermes PluginContext instance with:
            - register_hook(name, callback): Register lifecycle hook
            - register_tool(name, schema, handler): Register tool
            - config: dict from config.yaml under plugins.rag_memory
            - hermes_home: Path to Hermes config directory
    """
    global _rag, _config, _initialized

    # Extract config (use empty dict if not provided)
    _config = getattr(context, "config", {}) or {}
    if not isinstance(_config, dict):
        _config = {}

    # Check if enabled
    if not _config.get("enabled", True):
        logger.info("RAG Memory plugin disabled in config")
        return

    try:
        # Initialize RAGCore
        from rag_memory.core import RAGCore

        hermes_home = Path(getattr(context, "hermes_home", Path.home() / ".hermes"))
        data_dir = hermes_home / "plugins" / "rag-memory"

        _rag = RAGCore(
            db_path=str(data_dir / "rag_core.db"),
            mode=_config.get("mode", "hybrid"),
            cache_enabled=_config.get("cache_enabled", True),
            cache_ttl=_config.get("cache_ttl", 300),
        )
        # RAGCore initializes automatically in __init__

        _initialized = True
        logger.info("✓ RAG Memory plugin initialized")

    except Exception as e:
        logger.warning(
            f"RAG Memory plugin initialization failed: {e}",
            exc_info=True,
        )
        _initialized = False
        return

    # Register hooks
    if _config.get("auto_capture", True):
        context.register_hook("pre_llm_call", _on_pre_llm_call)
        context.register_hook("post_llm_call", _on_post_llm_call)
        context.register_hook("on_session_start", _on_session_start)
        context.register_hook("on_session_end", _on_session_end)
        logger.debug("✓ RAG Memory hooks registered")

    # Register tools
    from rag_memory.tools import schemas, handlers

    context.register_tool(
        name="rag_search",
        schema=schemas.RAG_SEARCH,
        handler=handlers.rag_search_wrapper(_rag),
    )
    context.register_tool(
        name="rag_add_document",
        schema=schemas.RAG_ADD_DOCUMENT,
        handler=handlers.rag_add_document_wrapper(_rag),
    )
    context.register_tool(
        name="rag_stats",
        schema=schemas.RAG_STATS,
        handler=handlers.rag_stats_wrapper(_rag),
    )
    context.register_tool(
        name="rag_flush",
        schema=schemas.RAG_FLUSH,
        handler=handlers.rag_flush_wrapper(_rag),
    )
    logger.debug(f"✓ RAG Memory tools registered: rag_search, rag_add_document, rag_stats, rag_flush")


# --------------------------------------------------------------------------- #
# Hook implementations
# --------------------------------------------------------------------------- #

def _on_pre_llm_call(event: dict[str, Any], context: Any) -> None:
    """Inject relevant context before LLM call.

    Searches RAG for recent conversations and injects relevant context
    into the system message.

    Args:
        event: LLM call event with messages, model, etc.
        context: Plugin context
    """
    if not _initialized or not _rag:
        return

    try:
        messages = event.get("messages", [])
        if not messages:
            return

        # Get last user message for search
        last_user_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break

        if not last_user_msg:
            return

        # Search for relevant context (last 200 chars)
        query = last_user_msg[:200]
        results = _rag.search(
            query,
            namespace="conversations",
            limit=_config.get("max_results", 10),
        )

        if results:
            # Inject context into system message
            context_lines = [
                f"[Relevant Memory - {r.get('timestamp', '')}]",
                r.get("content", "")[:300],
            ]
            context_block = "\n".join(context_lines)

            for msg in messages:
                if msg.get("role") == "system":
                    msg["content"] = f"{context_block}\n\n{msg.get('content', '')}"
                    break

    except Exception as e:
        logger.warning(f"pre_llm_call hook failed: {e}", exc_info=True)


def _on_post_llm_call(event: dict[str, Any], context: Any) -> None:
    """Capture conversation to RAG after LLM call.

    Captures user message + assistant response and stores in RAG
    for future retrieval.

    Args:
        event: LLM response event with messages
        context: Plugin context
    """
    if not _initialized or not _rag:
        return

    try:
        messages = event.get("messages", [])
        if len(messages) < 2:
            return

        # Find last user + assistant pair
        for i in range(len(messages) - 1):
            user_msg = messages[i]
            assistant_msg = messages[i + 1]

            if (
                user_msg.get("role") == "user"
                and assistant_msg.get("role") == "assistant"
            ):
                # Capture to RAG
                user_content = user_msg.get("content", "")
                assistant_content = assistant_msg.get("content", "")

                if user_content:
                    _rag.add_document(
                        content=user_content,
                        namespace="conversations",
                        metadata={"role": "user", "timestamp": _now()},
                    )

                if assistant_content:
                    _rag.add_document(
                        content=assistant_content,
                        namespace="conversations",
                        metadata={"role": "assistant", "timestamp": _now()},
                    )

                break

    except Exception as e:
        logger.warning(f"post_llm_call hook failed: {e}", exc_info=True)


def _on_session_start(event: dict[str, Any], context: Any) -> None:
    """Initialize session-specific state.

    Args:
        event: Session start event
        context: Plugin context
    """
    if not _initialized or not _rag:
        return

    try:
        session_id = event.get("session_id", "unknown")
        logger.debug(f"RAG Memory session started: {session_id}")
    except Exception as e:
        logger.warning(f"on_session_start hook failed: {e}", exc_info=True)


def _on_session_end(event: dict[str, Any], context: Any) -> None:
    """Flush any pending writes and cleanup session state.

    Args:
        event: Session end event
        context: Plugin context
    """
    if not _initialized or not _rag:
        return

    try:
        # Flush buffers
        if hasattr(_rag, "flush"):
            _rag.flush()

        session_id = event.get("session_id", "unknown")
        logger.debug(f"RAG Memory session ended: {session_id}")
    except Exception as e:
        logger.warning(f"on_session_end hook failed: {e}", exc_info=True)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _now() -> str:
    """Get current ISO timestamp."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
