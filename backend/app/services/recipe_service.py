"""
Recipe service for business logic.
Handles recipe creation and nutrition calculation.
"""
from typing import Tuple
from sqlalchemy.orm import Session

from app.db.schema import RecipeBase, RecipeCreate, NutritionBase, Recipe, NutritionSummary
from app.db.crud_recipes import create_recipe as db_create_recipe
from app.db.models import RecipeModel, RecipeTagModel, RecipeIngredientModel, RecipeStepModel
from app.utils.nutrition_lookup import estimate_recipe_nutrition


def create_recipe_with_nutrition(
    db: Session,
    recipe_base: RecipeBase,
    source_type: str,
    source_ref: str = None,
    tags: list[str] = None
) -> Tuple[Recipe, NutritionSummary]:
    """
    Create a recipe and calculate its nutrition.
    
    Args:
        db: Database session
        recipe_base: Recipe data
        source_type: Source type ("image", "url", "chat")
        source_ref: Source reference (URL, filename, etc.)
        tags: List of tags
    
    Returns:
        Tuple of (Recipe, NutritionSummary)
    """
    # Calculate nutrition
    total_nutrition, per_serving_nutrition = estimate_recipe_nutrition(recipe_base)
    
    # Create RecipeCreate schema
    recipe_create = RecipeCreate(
        name=recipe_base.name,
        description=recipe_base.description,
        servings=recipe_base.servings,
        total_time_minutes=recipe_base.total_time_minutes,
        ingredients=recipe_base.ingredients,
        steps=recipe_base.steps,
        source_type=source_type,
        source_ref=source_ref,
        tags=tags or []
    )
    
    # Save to database
    recipe_model = db_create_recipe(
        db,
        recipe_create,
        total_nutrition,
        per_serving_nutrition
    )
    
    # Convert to response schemas
    recipe = model_to_recipe(recipe_model)
    nutrition = NutritionSummary(
        recipe_id=recipe_model.id,
        total=total_nutrition,
        per_serving=per_serving_nutrition
    )
    
    return recipe, nutrition


def model_to_recipe(model: RecipeModel) -> Recipe:
    """Convert RecipeModel to Recipe schema."""
    from app.db.schema import IngredientBase, RecipeStepBase
    
    # Convert ingredients
    ingredients = [
        IngredientBase(
            name=ing.ingredient_name,
            quantity=ing.quantity,
            unit=ing.unit
        )
        for ing in sorted(model.ingredients, key=lambda x: x.id)
    ]
    
    # Convert steps
    steps = [
        RecipeStepBase(
            step_number=step.step_number,
            instruction=step.instruction
        )
        for step in sorted(model.steps, key=lambda x: x.step_number)
    ]
    
    # Get tags
    tags = [tag.tag for tag in model.tags]
    
    return Recipe(
        id=model.id,
        name=model.name,
        description=model.description,
        servings=model.servings,
        total_time_minutes=model.total_time_minutes,
        ingredients=ingredients,
        steps=steps,
        source_type=model.source_type,
        source_ref=model.source_ref,
        tags=tags,
        created_at=model.created_at
    )
