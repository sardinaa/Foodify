"""
Simple conversation memory service for chat agent.
Just tracks message history for context continuity.
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import json

from app.db import crud_chat


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
        self.session = crud_chat.get_or_create_session(db, session_id)
    
    def add_message(
        self,
        role: str,
        content: str,
        intent: Optional[str] = None,
        recipe_ids: Optional[List[int]] = None
    ) -> None:
        """Add a message to the conversation history."""
        crud_chat.add_message(
            self.db,
            self.session_id,
            role,
            content,
            intent,
            recipe_ids
        )
    
    def get_conversation_history(self, limit: Optional[int] = 5) -> List[Dict]:
        """
        Get recent conversation history.
        
        Args:
            limit: Number of recent messages to retrieve (default: 5)
        
        Returns:
            List of message dictionaries with role, content, and optionally recipes
        """
        messages = crud_chat.get_conversation_history(self.db, self.session_id, limit)
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
    
    def get_context_for_prompt(self) -> str:
        """
        Get recent conversation formatted as context string for LLM.
        
        Returns:
            Formatted conversation history
        """
        history = self.get_conversation_history(limit=6)  # Last 3 exchanges (6 messages)
        
        if not history:
            return ""
        
        context_parts = ["Previous conversation:"]
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role_label}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    def record_user_message(self, message: str, intent: str) -> None:
        """
        Record a user message.
        
        Args:
            message: User message content
            intent: Detected intent
        """
        self.add_message("user", message, intent)
    
    def record_assistant_response(
        self,
        response: str,
        recipe_ids: Optional[List[int]] = None,
        recipes: Optional[List[Dict]] = None
    ) -> None:
        """
        Record an assistant response.
        
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
        
        self.add_message("assistant", content, None, recipe_ids)
