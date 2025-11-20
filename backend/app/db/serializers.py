"""
Recipe serializers for converting between database models and dictionaries.
Centralizes all recipe-to-dict conversion logic to eliminate duplication.
"""
from typing import Dict, Any, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


class RecipeSerializer:
    """Serializes recipe data from various sources into standardized dictionaries."""
    
    @staticmethod
    def model_to_dict(
        recipe_model,
        include_nutrition: bool = True,
        include_tags: bool = True
    ) -> Dict[str, Any]:
        """
        Convert SQLAlchemy recipe model to dictionary with full context.
        
        Args:
            recipe_model: RecipeModel instance from database
            include_nutrition: Whether to include nutrition data
            include_tags: Whether to include tags/keywords
            
        Returns:
            Dictionary with complete recipe information
        """
        if not recipe_model:
            return {}
        
        recipe_dict = {
            "id": recipe_model.id,
            "recipe_id": str(recipe_model.id),
            "name": recipe_model.name,
            "description": recipe_model.description or "",
            "category": getattr(recipe_model, 'category', 'Unknown'),
            "servings": recipe_model.servings or 4,
            "total_time_minutes": recipe_model.total_time_minutes,
            "time": recipe_model.total_time_minutes,
            "prep_time_minutes": getattr(recipe_model, 'prep_time_minutes', None),
            "cook_time_minutes": getattr(recipe_model, 'cook_time_minutes', None),
            "source_type": recipe_model.source_type,
            "source_ref": recipe_model.source_ref,
            "created_at": recipe_model.created_at.isoformat() if recipe_model.created_at else None,
        }
        
        # Serialize ingredients (handle both database models and Pydantic models)
        recipe_dict["ingredients"] = [
            {
                "name": getattr(ing, 'ingredient_name', None) or getattr(ing, 'name', 'Unknown'),
                "quantity": ing.quantity,
                "unit": ing.unit
            }
            for ing in recipe_model.ingredients
        ]
        
        # Serialize steps
        recipe_dict["steps"] = [
            {
                "step_number": step.step_number,
                "instruction": step.instruction
            }
            for step in sorted(recipe_model.steps, key=lambda s: s.step_number)
        ]
        
        # Add nutrition if requested and available
        if include_nutrition and recipe_model.nutrition:
            recipe_dict.update({
                "calories": recipe_model.nutrition.kcal_per_serving,
                "protein": recipe_model.nutrition.protein_per_serving,
                "carbs": recipe_model.nutrition.carbs_per_serving,
                "fat": recipe_model.nutrition.fat_per_serving,
                "kcal_total": recipe_model.nutrition.kcal_total,
                "protein_total": recipe_model.nutrition.protein_total,
                "carbs_total": recipe_model.nutrition.carbs_total,
                "fat_total": recipe_model.nutrition.fat_total,
            })
            
            # Add optional nutrition fields if present
            if recipe_model.nutrition.saturated_fat is not None:
                recipe_dict["saturated_fat"] = recipe_model.nutrition.saturated_fat
            if recipe_model.nutrition.cholesterol is not None:
                recipe_dict["cholesterol"] = recipe_model.nutrition.cholesterol
            if recipe_model.nutrition.sodium is not None:
                recipe_dict["sodium"] = recipe_model.nutrition.sodium
            if recipe_model.nutrition.fiber is not None:
                recipe_dict["fiber"] = recipe_model.nutrition.fiber
            if recipe_model.nutrition.sugar is not None:
                recipe_dict["sugar"] = recipe_model.nutrition.sugar
        else:
            # Set default nutrition values
            recipe_dict.update({
                "calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0
            })
        
        # Add tags if requested and available
        if include_tags and recipe_model.tags:
            tags_list = [tag.tag for tag in recipe_model.tags]
            recipe_dict["tags"] = tags_list
            recipe_dict["keywords"] = tags_list  # Alias for backwards compatibility
        else:
            recipe_dict["tags"] = []
            recipe_dict["keywords"] = []
        
        return recipe_dict
    
    @staticmethod
    def metadata_to_dict(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert ChromaDB metadata to standardized dictionary format.
        
        Args:
            metadata: Metadata dictionary from ChromaDB
            
        Returns:
            Dictionary with complete recipe information
        """
        if not metadata:
            return {}
        
        # Parse JSON fields from metadata (ChromaDB stores complex types as JSON strings)
        ingredients_json = metadata.get('ingredients', '[]')
        instructions_json = metadata.get('instructions', '[]')
        keywords_json = metadata.get('keywords', '[]')
        
        # Safely parse ingredients
        try:
            ingredients_list = json.loads(ingredients_json) if isinstance(ingredients_json, str) else ingredients_json
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse ingredients: {e}")
            ingredients_list = []
        
        # Safely parse instructions
        try:
            instructions_list = json.loads(instructions_json) if isinstance(instructions_json, str) else instructions_json
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse instructions: {e}")
            instructions_list = []
        
        # Safely parse keywords
        try:
            keywords_list = json.loads(keywords_json) if isinstance(keywords_json, str) else keywords_json
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse keywords: {e}")
            keywords_list = []
        
        # Convert ingredients to structured format
        structured_ingredients = RecipeSerializer._normalize_ingredients(ingredients_list)
        
        # Convert instructions to structured format
        structured_steps = RecipeSerializer._normalize_steps(instructions_list)
        
        return {
            "id": metadata.get('recipe_id', 0),
            "recipe_id": metadata.get('recipe_id', ''),
            "name": metadata.get('name', 'Unknown Recipe'),
            "description": metadata.get('description', ''),
            "category": metadata.get('category', 'Unknown'),
            "servings": int(metadata.get('servings', 4)),
            "total_time_minutes": int(metadata.get('time', 30)),
            "time": int(metadata.get('time', 30)),
            "ingredients": structured_ingredients,
            "steps": structured_steps,
            "source_type": metadata.get('source_type', 'dataset'),
            "source_ref": metadata.get('recipe_id', ''),
            "tags": keywords_list[:5],  # Top 5 tags
            "keywords": keywords_list,  # All keywords
            "calories": float(metadata.get('calories', 0)),
            "protein": float(metadata.get('protein', 0)),
            "carbs": float(metadata.get('carbs', 0)),
            "fat": float(metadata.get('fat', 0)),
            "created_at": None
        }
    
    @staticmethod
    def _normalize_ingredients(ingredients_list: List) -> List[Dict[str, Any]]:
        """
        Normalize ingredients to structured format.
        Handles both string and dictionary formats.
        """
        structured_ingredients = []
        
        for ing in ingredients_list:
            if isinstance(ing, str):
                # Plain string ingredient
                structured_ingredients.append({
                    "name": ing,
                    "quantity": None,
                    "unit": None
                })
            elif isinstance(ing, dict):
                # Already structured
                structured_ingredients.append({
                    "name": ing.get("name", ""),
                    "quantity": ing.get("quantity"),
                    "unit": ing.get("unit")
                })
        
        return structured_ingredients
    
    @staticmethod
    def _normalize_steps(instructions_list: List) -> List[Dict[str, Any]]:
        """
        Normalize instructions to structured format.
        Handles both string and dictionary formats.
        """
        structured_steps = []
        
        for idx, instruction in enumerate(instructions_list, 1):
            if isinstance(instruction, str):
                # Plain string instruction
                structured_steps.append({
                    "step_number": idx,
                    "instruction": instruction
                })
            elif isinstance(instruction, dict):
                # Already structured
                structured_steps.append({
                    "step_number": instruction.get("step_number", idx),
                    "instruction": instruction.get("instruction", "")
                })
        
        return structured_steps
    
    @staticmethod
    def to_api_response(
        recipe: Dict[str, Any],
        include_full_details: bool = True,
        **extras
    ) -> Dict[str, Any]:
        """
        Convert recipe dictionary to API response format.
        Allows adding extra fields for specific endpoints.
        
        Args:
            recipe: Recipe dictionary (from model_to_dict or metadata_to_dict)
            include_full_details: Whether to include full ingredients/steps
            **extras: Additional fields to add to response
            
        Returns:
            Dictionary formatted for API response
        """
        if not recipe:
            return {}
        
        response = {
            "id": recipe.get("id"),
            "name": recipe.get("name"),
            "description": recipe.get("description", ""),
            "servings": recipe.get("servings", 4),
            "time": recipe.get("time") or recipe.get("total_time_minutes"),
            "calories": recipe.get("calories", 0),
            "protein": recipe.get("protein", 0),
            "carbs": recipe.get("carbs", 0),
            "fat": recipe.get("fat", 0),
            "category": recipe.get("category", "Unknown"),
            "tags": recipe.get("tags", []),
        }
        
        if include_full_details:
            response["ingredients"] = recipe.get("ingredients", [])
            response["steps"] = recipe.get("steps", [])
            response["source_type"] = recipe.get("source_type")
            response["source_ref"] = recipe.get("source_ref")
        
        # Add any extra fields
        response.update(extras)
        
        return response
    
    @staticmethod
    def batch_to_dict(
        recipe_models: List,
        include_nutrition: bool = True,
        include_tags: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Convert multiple recipe models to dictionaries.
        
        Args:
            recipe_models: List of RecipeModel instances
            include_nutrition: Whether to include nutrition data
            include_tags: Whether to include tags
            
        Returns:
            List of recipe dictionaries
        """
        return [
            RecipeSerializer.model_to_dict(
                recipe,
                include_nutrition=include_nutrition,
                include_tags=include_tags
            )
            for recipe in recipe_models
        ]
