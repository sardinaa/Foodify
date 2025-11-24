"""
Simple in-memory conversation memory for chat sessions.
No database persistence - stores messages in Python memory only.
"""
from typing import List, Dict, Optional

# In-memory storage: session_id -> list of messages
_sessions: Dict[str, List[Dict]] = {}


class ConversationMemory:
    """
    Simple in-memory conversation memory.
    Tracks message history within a single session.
    """
    
    def __init__(self, session_id: str):
        """
        Initialize conversation memory for a session.
        
        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        if session_id not in _sessions:
            _sessions[session_id] = []
    
    async def add_message(
        self,
        role: str,
        content: str,
        intent: Optional[str] = None,
        recipe_ids: Optional[List[int]] = None
    ) -> None:
        """Add a message to the in-memory conversation history."""
        message = {
            "role": role,
            "content": content,
            "intent": intent,
            "recipe_ids": recipe_ids
        }
        _sessions[self.session_id].append(message)
    
    async def get_conversation_history(self, limit: Optional[int] = 5) -> List[Dict]:
        """
        Get recent conversation history.
        
        Args:
            limit: Number of recent messages to retrieve (default: 5)
        
        Returns:
            List of message dictionaries with role and content
        """
        messages = _sessions.get(self.session_id, [])
        recent = messages[-limit:] if limit else messages
        
        result = []
        for msg in recent:
            message_dict = {"role": msg["role"], "content": msg["content"]}
            if "recipes" in msg:
                message_dict["recipes"] = msg["recipes"]
            result.append(message_dict)
        
        return result
    
    async def get_context_for_prompt(self) -> str:
        """
        Get recent conversation formatted as context string for LLM.
        
        Returns:
            Formatted conversation history
        """
        history = await self.get_conversation_history(limit=6)
        
        if not history:
            return ""
        
        context_parts = ["Previous conversation:"]
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role_label}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    async def record_user_message(self, message: str, intent: str) -> None:
        """
        Record a user message.
        
        Args:
            message: User message content
            intent: Detected intent
        """
        await self.add_message("user", message, intent)
    
    async def record_assistant_response(
        self,
        response: str,
        recipe_ids: Optional[List[int]] = None,
        recipes: Optional[List[Dict]] = None
    ) -> None:
        """
        Record an assistant response.
        
        Args:
            response: Assistant's response text
            recipe_ids: List of recipe IDs suggested
            recipes: Full recipe data (optional, for context)
        """
        message = {
            "role": "assistant",
            "content": response,
            "recipe_ids": recipe_ids
        }
        if recipes:
            message["recipes"] = recipes
        
        _sessions[self.session_id].append(message)
