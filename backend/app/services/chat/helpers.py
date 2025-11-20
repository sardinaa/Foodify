"""
Helper functions for chat agent to reduce code duplication.
"""
import re
from typing import Dict, List, Optional
from datetime import datetime
from app.db.serializers import RecipeSerializer
from app.core.constants import LimitsConstants


def extract_urls(message: str) -> List[str]:
    """Extract URLs from message text."""
    urls = re.findall(r'https?://[^\s]+', message)
    if not urls:
        www_urls = re.findall(r'www\.[^\s]+', message)
        urls = [f"https://{url}" for url in www_urls]
    return urls


def format_recipe_dict(recipe_model, nutrition=None, tags=None) -> Dict:
    """
    Convert recipe model to dictionary for API response.
    Handles both database models (RecipeModel) and Pydantic schemas (Recipe).
    """
    # Check if it's a Pydantic model (has model_dump) or database model
    if hasattr(recipe_model, 'model_dump'):
        # Pydantic schema - convert to dict directly
        recipe_dict = recipe_model.model_dump(mode="json")
        # Ensure consistent format
        recipe_dict["recipe_id"] = str(recipe_dict.get("id", ""))
        recipe_dict["time"] = recipe_dict.get("total_time_minutes")
        recipe_dict["keywords"] = recipe_dict.get("tags", [])
    else:
        # Database model - use the unified serializer
        recipe_dict = RecipeSerializer.model_to_dict(recipe_model)
    
    # Override with custom nutrition if provided
    if nutrition:
        recipe_dict.update({
            "calories": nutrition.per_serving.kcal,
            "protein": nutrition.per_serving.protein,
            "carbs": nutrition.per_serving.carbs,
            "fat": nutrition.per_serving.fat
        })
    
    # Override with custom tags if provided
    if tags:
        recipe_dict["tags"] = tags[:5]
        recipe_dict["keywords"] = tags
    
    return recipe_dict


def get_recipes_from_history(memory, limit: int = None) -> List[Dict]:
    """Extract recipes from conversation history."""
    if not memory:
        return []
    
    if limit is None:
        limit = LimitsConstants.MEMORY_HISTORY_LIMIT
    
    history = memory.get_conversation_history(limit=limit)
    for msg in reversed(history):
        if msg["role"] == "assistant" and "recipes" in msg:
            return msg["recipes"]
    return []


def create_error_response(message: str) -> Dict:
    """Create standardized error response with markdown formatting."""
    # Add emoji prefix if not already present
    if not any(message.startswith(emoji) for emoji in ['⚠️', '❌', '🔍', '💡']):
        message = f"⚠️ {message}"
    return {
        "reply": message,
        "suggested_recipes": [],
        "weekly_menu": None
    }
