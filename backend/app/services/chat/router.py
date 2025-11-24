"""Intent routing helpers for chat agent handlers."""

from __future__ import annotations

from importlib import import_module
from typing import Awaitable, Callable, Dict

from sqlalchemy.orm import Session

from app.services.conversation_memory import ConversationMemory

Handler = Callable[[Session, str, str, ConversationMemory | None], Awaitable[Dict]]

_HANDLER_PATHS: Dict[str, str] = {
    "url_analysis": "app.services.chat_agent:handle_url_analysis_mode",
    "modification": "app.services.chat_agent:handle_modification_mode",
    # "ingredients" intent now handled by default recipe_search (full RAG handles it)
    "weekly_menu": "app.services.chat_agent:handle_weekly_menu_mode",
}
_DEFAULT_HANDLER = "app.services.chat_agent:handle_recipe_search_mode"


def _resolve_handler(path: str) -> Handler:
    module_name, func_name = path.split(":", 1)
    module = import_module(module_name)
    return getattr(module, func_name)


def get_handler(intent: str) -> Handler:
    """Return the coroutine handler for the provided intent."""
    path = _HANDLER_PATHS.get(intent, _DEFAULT_HANDLER)
    return _resolve_handler(path)


async def dispatch_intent(
    intent: str,
    db: Session,
    session_id: str,
    message: str,
    memory: ConversationMemory | None,
) -> Dict:
    """Dispatch to the handler mapped to the detected intent."""
    handler = get_handler(intent)
    return await handler(db, session_id, message, memory)
