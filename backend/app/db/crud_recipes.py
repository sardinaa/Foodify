"""
CRUD operations for recipes.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import (
    RecipeModel, RecipeIngredientModel, RecipeStepModel,
    NutritionSummaryModel, RecipeTagModel
)
from app.db.schema import RecipeCreate, NutritionBase


def create_recipe(
    db: Session,
    recipe_data: RecipeCreate,
    nutrition_total: NutritionBase,
    nutrition_per_serving: NutritionBase
) -> RecipeModel:
    """
    Create a new recipe with ingredients, steps, nutrition, and tags.
    """
    # Create recipe
    recipe = RecipeModel(
        name=recipe_data.name,
        description=recipe_data.description,
        servings=recipe_data.servings,
        source_type=recipe_data.source_type,
        source_ref=recipe_data.source_ref
    )
    db.add(recipe)
    db.flush()  # Get recipe.id
    
    # Add ingredients
    for ingredient in recipe_data.ingredients:
        recipe_ingredient = RecipeIngredientModel(
            recipe_id=recipe.id,
            ingredient_name=ingredient.name,
            quantity=ingredient.quantity,
            unit=ingredient.unit
        )
        db.add(recipe_ingredient)
    
    # Add steps
    for step in recipe_data.steps:
        recipe_step = RecipeStepModel(
            recipe_id=recipe.id,
            step_number=step.step_number,
            instruction=step.instruction
        )
        db.add(recipe_step)
    
    # Add nutrition
    nutrition = NutritionSummaryModel(
        recipe_id=recipe.id,
        kcal_total=nutrition_total.kcal,
        protein_total=nutrition_total.protein,
        carbs_total=nutrition_total.carbs,
        fat_total=nutrition_total.fat,
        kcal_per_serving=nutrition_per_serving.kcal,
        protein_per_serving=nutrition_per_serving.protein,
        carbs_per_serving=nutrition_per_serving.carbs,
        fat_per_serving=nutrition_per_serving.fat
    )
    db.add(nutrition)
    
    # Add tags
    for tag in recipe_data.tags:
        recipe_tag = RecipeTagModel(
            recipe_id=recipe.id,
            tag=tag
        )
        db.add(recipe_tag)
    
    db.commit()
    db.refresh(recipe)
    return recipe


def get_recipe(db: Session, recipe_id: int) -> Optional[RecipeModel]:
    """Get a recipe by ID."""
    return db.query(RecipeModel).filter(RecipeModel.id == recipe_id).first()
