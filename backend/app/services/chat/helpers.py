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


async def get_recipes_from_history(memory, limit: int = 10) -> List[Dict]:
    """
    Extract recipes from conversation history.
    
    Args:
        memory: ConversationMemory instance
        limit: Number of messages to check
        
    Returns:
        List of recipe dictionaries found in history
    """
    history = await memory.get_conversation_history(limit=limit)
    recipes = []
    seen_ids = set()
    
    # Iterate through history
    for msg in history:
        if "recipes" in msg and isinstance(msg["recipes"], list):
            for recipe in msg["recipes"]:
                # Use ID or name as unique identifier
                recipe_id = recipe.get("id") or recipe.get("recipe_id") or recipe.get("name")
                
                if recipe_id and recipe_id not in seen_ids:
                    seen_ids.add(recipe_id)
                    recipes.append(recipe)
                    
    return recipes


def create_error_response(message: str) -> Dict:
    """Create standardized error response with markdown formatting."""
    return {
        "reply": message,
        "suggested_recipes": [],
        "weekly_menu": None
    }
