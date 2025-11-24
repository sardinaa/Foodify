"""
CRUD operations for chat sessions and conversation memory.
"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.db.models import (
    ChatSessionModel,
    ChatMessageModel,
    UserRequirementModel
)
from app.db.base_crud import CRUDBase
from pydantic import BaseModel


class ChatSessionCreate(BaseModel):
    session_id: str


class CRUDChatSession(CRUDBase[ChatSessionModel, ChatSessionCreate, ChatSessionCreate]):
    def get_or_create(self, db: Session, session_id: str) -> ChatSessionModel:
        """
        Get existing chat session or create a new one.
        """
        session = db.query(ChatSessionModel).filter(
            ChatSessionModel.session_id == session_id
        ).first()
        
        if not session:
            session = ChatSessionModel(
                session_id=session_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(session)
            db.commit()
            db.refresh(session)
        
        return session

    def update_preferences(
        self,
        db: Session,
        session_id: str,
        dietary_restrictions: Optional[List[str]] = None,
        favorite_cuisines: Optional[List[str]] = None,
        disliked_ingredients: Optional[List[str]] = None,
        preferred_meal_types: Optional[List[str]] = None,
        cooking_skill_level: Optional[str] = None,
        time_constraints: Optional[int] = None
    ) -> ChatSessionModel:
        """
        Update session preferences and context.
        """
        session = self.get_or_create(db, session_id)
        
        if dietary_restrictions is not None:
            session.dietary_restrictions = json.dumps(dietary_restrictions)
        if favorite_cuisines is not None:
            session.favorite_cuisines = json.dumps(favorite_cuisines)
        if disliked_ingredients is not None:
            session.disliked_ingredients = json.dumps(disliked_ingredients)
        if preferred_meal_types is not None:
            session.preferred_meal_types = json.dumps(preferred_meal_types)
        if cooking_skill_level is not None:
            session.cooking_skill_level = cooking_skill_level
        if time_constraints is not None:
            session.time_constraints = time_constraints
        
        session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(session)
        
        return session


chat_session = CRUDChatSession(ChatSessionModel)



def get_session_preferences(db: Session, session_id: str) -> Dict:
    """
    Get session preferences as a dictionary.
    
    Args:
        db: Database session
        session_id: Unique session identifier
    
    Returns:
        Dictionary with preferences
    """
    session = chat_session.get_or_create(db, session_id)
    
    return {
        "dietary_restrictions": json.loads(session.dietary_restrictions) if session.dietary_restrictions else [],
        "favorite_cuisines": json.loads(session.favorite_cuisines) if session.favorite_cuisines else [],
        "disliked_ingredients": json.loads(session.disliked_ingredients) if session.disliked_ingredients else [],
        "preferred_meal_types": json.loads(session.preferred_meal_types) if session.preferred_meal_types else [],
        "cooking_skill_level": session.cooking_skill_level,
        "time_constraints": session.time_constraints
    }


def update_session_preferences(
    db: Session,
    session_id: str,
    dietary_restrictions: Optional[List[str]] = None,
    favorite_cuisines: Optional[List[str]] = None,
    disliked_ingredients: Optional[List[str]] = None,
    preferred_meal_types: Optional[List[str]] = None,
    cooking_skill_level: Optional[str] = None,
    time_constraints: Optional[int] = None
) -> ChatSessionModel:
    """Backward-compatible helper that updates chat session preferences."""
    return chat_session.update_preferences(
        db=db,
        session_id=session_id,
        dietary_restrictions=dietary_restrictions,
        favorite_cuisines=favorite_cuisines,
        disliked_ingredients=disliked_ingredients,
        preferred_meal_types=preferred_meal_types,
        cooking_skill_level=cooking_skill_level,
        time_constraints=time_constraints
    )


def add_message(
    db: Session,
    session_id: str,
    role: str,
    content: str,
    intent: Optional[str] = None,
    recipe_ids: Optional[List[int]] = None
) -> ChatMessageModel:
    """
    Add a message to the chat session.
    
    Args:
        db: Database session
        session_id: Unique session identifier
        role: "user" or "assistant"
        content: Message content
        intent: Detected intent (optional)
        recipe_ids: List of recipe IDs referenced (optional)
    
    Returns:
        ChatMessageModel instance
    """
    # Ensure session exists
    chat_session.get_or_create(db, session_id)
    
    message = ChatMessageModel(
        session_id=session_id,
        role=role,
        content=content,
        intent=intent,
        recipe_ids=json.dumps(recipe_ids) if recipe_ids else None,
        created_at=datetime.utcnow()
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return message


def get_conversation_history(
    db: Session,
    session_id: str,
    limit: Optional[int] = None
) -> List[ChatMessageModel]:
    """
    Get conversation history for a session.
    
    Args:
        db: Database session
        session_id: Unique session identifier
        limit: Maximum number of messages to return (most recent first)
    
    Returns:
        List of ChatMessageModel instances
    """
    query = db.query(ChatMessageModel).filter(
        ChatMessageModel.session_id == session_id
    ).order_by(ChatMessageModel.created_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    messages = query.all()
    return list(reversed(messages))  # Return in chronological order


def add_user_requirement(
    db: Session,
    session_id: str,
    requirement_type: str,
    key: str,
    value: str,
    context: Optional[str] = None
) -> UserRequirementModel:
    """
    Add a user requirement to track during conversation.
    
    Args:
        db: Database session
        session_id: Unique session identifier
        requirement_type: Type of requirement ("ingredient", "dietary", "modification", "preference")
        key: Requirement key (e.g., "exclude_ingredient", "add_ingredient")
        value: The actual requirement value
        context: Additional context (optional)
    
    Returns:
        UserRequirementModel instance
    """
    # Ensure session exists
    chat_session.get_or_create(db, session_id)
    
    requirement = UserRequirementModel(
        session_id=session_id,
        requirement_type=requirement_type,
        key=key,
        value=value,
        context=context,
        created_at=datetime.utcnow(),
        is_active=1
    )
    
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    
    return requirement


def get_active_requirements(
    db: Session,
    session_id: str,
    requirement_type: Optional[str] = None
) -> List[UserRequirementModel]:
    """
    Get active user requirements for a session.
    
    Args:
        db: Database session
        session_id: Unique session identifier
        requirement_type: Filter by requirement type (optional)
    
    Returns:
        List of UserRequirementModel instances
    """
    query = db.query(UserRequirementModel).filter(
        UserRequirementModel.session_id == session_id,
        UserRequirementModel.is_active == 1
    )
    
    if requirement_type:
        query = query.filter(UserRequirementModel.requirement_type == requirement_type)
    
    return query.order_by(UserRequirementModel.created_at).all()


def deactivate_requirement(
    db: Session,
    requirement_id: int
) -> bool:
    """
    Deactivate a requirement (mark as no longer active).
    
    Args:
        db: Database session
        requirement_id: ID of the requirement to deactivate
    
    Returns:
        True if successful, False otherwise
    """
    requirement = db.query(UserRequirementModel).filter(
        UserRequirementModel.id == requirement_id
    ).first()
    
    if requirement:
        requirement.is_active = 0
        db.commit()
        return True
    
    return False


def clear_requirements_by_type(
    db: Session,
    session_id: str,
    requirement_type: str
) -> int:
    """
    Clear all requirements of a specific type for a session.
    
    Args:
        db: Database session
        session_id: Unique session identifier
        requirement_type: Type of requirement to clear
    
    Returns:
        Number of requirements cleared
    """
    count = db.query(UserRequirementModel).filter(
        UserRequirementModel.session_id == session_id,
        UserRequirementModel.requirement_type == requirement_type,
        UserRequirementModel.is_active == 1
    ).update({"is_active": 0})
    
    db.commit()
    return count


def get_conversation_summary(db: Session, session_id: str) -> Dict:
    """
    Get a comprehensive summary of the conversation session.
    
    Args:
        db: Database session
        session_id: Unique session identifier
    
    Returns:
        Dictionary with session summary including preferences, history, and requirements
    """
    session = chat_session.get_or_create(db, session_id)
    messages = get_conversation_history(db, session_id)
    requirements = get_active_requirements(db, session_id)
    preferences = get_session_preferences(db, session_id)
    
    return {
        "session_id": session_id,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "preferences": preferences,
        "message_count": len(messages),
        "recent_messages": [
            {
                "role": msg.role,
                "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                "intent": msg.intent,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages[-5:]  # Last 5 messages
        ],
        "active_requirements": [
            {
                "type": req.requirement_type,
                "key": req.key,
                "value": req.value,
                "context": req.context
            }
            for req in requirements
        ]
    }
