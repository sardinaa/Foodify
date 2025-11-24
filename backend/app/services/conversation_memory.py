"""
Simple conversation memory service for chat agent.
Just tracks message history for context continuity.
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.db import crud_chat

# Create a global executor for DB operations
db_executor = ThreadPoolExecutor(max_workers=5)

class ConversationMemory:
    """
    Simple conversation memory that tracks message history.
    Provides context from previous messages for continuity.
    """
    
    def __init__(self, db: Session, session_id: str):
        """
        Initialize conversation memory for a session.
        
        Args:
            db: Database session
            session_id: Unique session identifier
        """
        self.db = db
        self.session_id = session_id
    
    async def _run_sync(self, func, *args):
        """Run a synchronous DB function in a thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(db_executor, func, *args)

    async def add_message(
        self,
        role: str,
        content: str,
        intent: Optional[str] = None,
        recipe_ids: Optional[List[int]] = None
    ) -> None:
        """Add a message to the conversation history asynchronously."""
        await self._run_sync(
            crud_chat.add_message,
            self.db,
            self.session_id,
            role,
            content,
            intent,
            recipe_ids
        )
    
    async def get_conversation_history(self, limit: Optional[int] = 5) -> List[Dict]:
        """
        Get recent conversation history asynchronously.
        
        Args:
            limit: Number of recent messages to retrieve (default: 5)
        
        Returns:
            List of message dictionaries with role, content, and optionally recipes
        """
        messages = await self._run_sync(
            crud_chat.get_conversation_history, 
            self.db, 
            self.session_id, 
            limit
        )
        
        result = []
        
        for msg in messages:
            message_dict = {"role": msg.role}
            
            # Try to parse JSON content (for assistant messages with recipes)
            try:
                parsed = json.loads(msg.content)
                if isinstance(parsed, dict) and "text" in parsed:
                    message_dict["content"] = parsed["text"]
                    if "recipes" in parsed:
                        message_dict["recipes"] = parsed["recipes"]
                else:
                    message_dict["content"] = msg.content
            except (json.JSONDecodeError, TypeError):
                # Not JSON, just plain text
                message_dict["content"] = msg.content
            
            result.append(message_dict)
        
        return result
    
    async def get_context_for_prompt(self) -> str:
        """
        Get recent conversation formatted as context string for LLM.
        
        Returns:
            Formatted conversation history
        """
        history = await self.get_conversation_history(limit=6)  # Last 3 exchanges (6 messages)
        
        if not history:
            return ""
        
        context_parts = ["Previous conversation:"]
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role_label}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    async def record_user_message(self, message: str, intent: str) -> None:
        """
        Record a user message asynchronously.
        
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
        Record an assistant response asynchronously.
        
        Args:
            response: Assistant's response text
            recipe_ids: List of recipe IDs suggested in the response
            recipes: Full recipe data (optional, for modification context)
        """
        # If recipes are provided, include them in the content as JSON
        if recipes:
            content = json.dumps({
                "text": response,
                "recipes": recipes
            })
        else:
            content = response
        
        await self.add_message("assistant", content, None, recipe_ids)

    async def get_summary(self) -> Dict:
        """Get session summary asynchronously."""
        return await self._run_sync(crud_chat.get_session_preferences, self.db, self.session_id)
