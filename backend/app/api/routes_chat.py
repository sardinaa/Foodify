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
    db: Session = Depends(get_db)
):
    """
    Chat endpoint for recipe suggestions and menu planning.
    Automatically detects user intent and provides appropriate responses.
    Now includes conversation memory to track user preferences.
    
    - **session_id**: Unique session identifier
    - **message**: User message (e.g., "I have chicken and rice", "plan my weekly meals", "healthy breakfast ideas")
    
    The agent will automatically determine if you want:
    - Recipe suggestions based on ingredients you have
    - A weekly meal plan
    - General recipe search and recommendations
    
    The agent remembers your preferences across conversations:
    - Dietary restrictions (vegetarian, vegan, gluten-free, etc.)
    - Disliked ingredients
    - Favorite cuisines
    - Time constraints
    
    Returns conversational reply with structured recipe suggestions or weekly menu.
    """
    # Delegate to agent handler
    response = await chat_agent_handler(
        db, session_id, message
    )
    
    return response



