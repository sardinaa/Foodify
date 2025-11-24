"""
CRUD operations for recipes.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import (
    RecipeModel, RecipeIngredientModel, RecipeStepModel,
    NutritionSummaryModel, RecipeTagModel
)
from app.db.schema import RecipeCreate, IngredientBase, RecipeStepBase, NutritionBase
from app.db.base_crud import CRUDBase


class CRUDRecipe(CRUDBase[RecipeModel, RecipeCreate, RecipeCreate]):
    def create_with_details(
        self,
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
            total_time_minutes=recipe_data.total_time_minutes,
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

    def get_by_tag(self, db: Session, tag: str) -> List[RecipeModel]:
        """Get recipes with a specific tag."""
        return (
            db.query(RecipeModel)
            .join(RecipeTagModel)
            .filter(RecipeTagModel.tag == tag)
            .all()
        )

    def search(self, db: Session, query: str) -> List[RecipeModel]:
        """Search recipes by name or description."""
        return (
            db.query(RecipeModel)
            .filter(
                (RecipeModel.name.ilike(f"%{query}%")) |
                (RecipeModel.description.ilike(f"%{query}%"))
            )
            .all()
        )


recipe = CRUDRecipe(RecipeModel)

from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import (
    RecipeModel, RecipeIngredientModel, RecipeStepModel,
    NutritionSummaryModel, RecipeTagModel
)
from app.db.schema import RecipeCreate, IngredientBase, RecipeStepBase, NutritionBase


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
        total_time_minutes=recipe_data.total_time_minutes,
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


def get_recipes(db: Session, skip: int = 0, limit: int = 100) -> List[RecipeModel]:
    """Get all recipes with pagination."""
    return db.query(RecipeModel).offset(skip).limit(limit).all()


def get_recipes_by_tag(db: Session, tag: str) -> List[RecipeModel]:
    """Get recipes with a specific tag."""
    return (
        db.query(RecipeModel)
        .join(RecipeTagModel)
        .filter(RecipeTagModel.tag == tag)
        .all()
    )


def search_recipes(db: Session, query: str) -> List[RecipeModel]:
    """Search recipes by name or description."""
    search_pattern = f"%{query}%"
    return (
        db.query(RecipeModel)
        .filter(
            (RecipeModel.name.ilike(search_pattern)) |
            (RecipeModel.description.ilike(search_pattern))
        )
        .all()
    )
