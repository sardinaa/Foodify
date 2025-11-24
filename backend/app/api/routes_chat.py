"""
API routes for chat and planning.
"""
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from typing import Optional
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.schema import ChatRequest, ChatResponse
from app.services.chat_agent import chat_agent_handler

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    session_id: str = Form(...),
    message: str = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Chat endpoint for recipe suggestions and menu planning.
    Automatically detects user intent and provides appropriate responses.
    Now includes conversation memory to track user preferences.
    
    - **session_id**: Unique session identifier
    - **message**: User message (e.g., "I have chicken and rice", "plan my weekly meals", "healthy breakfast ideas")
    - **image**: Optional image file upload (for food photo analysis)
    
    The agent will automatically determine if you want:
    - Recipe suggestions based on ingredients you have
    - Recipe extraction from an uploaded food photo
    - A weekly meal plan
    - General recipe search and recommendations
    
    The agent remembers your preferences across conversations:
    - Dietary restrictions (vegetarian, vegan, gluten-free, etc.)
    - Disliked ingredients
    - Favorite cuisines
    - Time constraints
    
    Returns conversational reply with structured recipe suggestions or weekly menu.
    """
    # Read image bytes if provided
    image_bytes = None
    if image:
        image_bytes = await image.read()
    
    # Delegate to agent handler
    response = await chat_agent_handler(
        db, session_id, message, image_bytes
    )
    
    return response


@router.get("/chat/session/{session_id}")
async def get_session_summary(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get conversation summary for a session.
    
    Returns:
    - User preferences (dietary restrictions, favorite cuisines, etc.)
    - Recent conversation history
    - Active requirements and modifications
    
    Useful for debugging or displaying user preferences in the UI.
    """
    try:
        from app.services.conversation_memory import ConversationMemory
        
        memory = ConversationMemory(db, session_id)
        summary = await memory.get_summary()
        
        return summary
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session summary: {str(e)}")
