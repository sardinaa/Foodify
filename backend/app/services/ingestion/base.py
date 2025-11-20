"""Shared helpers for recipe ingestion pipelines."""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.schema import NutritionSummary, Recipe, RecipeBase
from app.services.recipe_service import create_recipe_with_nutrition


async def persist_generated_recipe(
    db: Session,
    llm_client,
    recipe_base: RecipeBase,
    *,
    source_type: str,
    source_ref: str,
    normalized_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    tag_context: Optional[str] = None,
) -> Tuple[Recipe, NutritionSummary, List[str]]:
    """Normalize tags/name and persist a generated recipe."""
    computed_tags = tags or []
    effective_name = normalized_name or recipe_base.name

    if not computed_tags:
        context = tag_context or recipe_base.description or recipe_base.name
        dish_name, computed_tags = await llm_client.normalize_dish_name_and_tags(
            context,
            recipe_base.name,
        )
        if dish_name and dish_name != "Unknown Dish":
            effective_name = dish_name

    if effective_name:
        recipe_base.name = effective_name

    recipe, nutrition = create_recipe_with_nutrition(
        db,
        recipe_base,
        source_type=source_type,
        source_ref=source_ref,
        tags=computed_tags,
    )

    return recipe, nutrition, computed_tags
