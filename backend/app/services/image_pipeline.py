"""
Image analysis pipeline.
Orchestrates VLM → recipe generation → nutrition calculation.
"""
from typing import Tuple, Optional
from sqlalchemy.orm import Session

from app.core.vlm_client import get_vlm_client
from app.core.llm_client import get_llm_client
from app.db.schema import Recipe, NutritionSummary
from app.services.ingestion.base import persist_generated_recipe


async def analyze_image_pipeline(
    db: Session,
    image_bytes: bytes,
    title: Optional[str] = None
) -> Tuple[Recipe, NutritionSummary, list[str], dict]:
    """
    Full pipeline for analyzing a food image.
    
    Steps:
    1. Use VLM to describe the dish
    2. Normalize dish name and generate tags
    3. Generate structured recipe
    4. Calculate nutrition
    5. Persist to database
    
    Args:
        db: Database session
        image_bytes: Image data
        title: Optional user-provided title
    
    Returns:
        Tuple of (Recipe, NutritionSummary, tags, debug_info)
    """
    vlm = get_vlm_client()
    llm = get_llm_client()
    
    # Step 1: Analyze image
    vision_result = await vlm.describe_dish_from_image(image_bytes, title)
    description = vision_result["description"]
    
    # Step 2: Normalize name and tags
    dish_name, tags = await llm.normalize_dish_name_and_tags(description, title)
    
    # Step 3: Generate recipe from description
    # Create a prompt that includes vision results
    recipe_prompt = f"""Dish: {dish_name}
Description: {description}
Type: {vision_result['dish_type']}
Likely ingredients: {', '.join(vision_result['guessed_ingredients'])}

Generate a complete recipe with ingredients and cooking steps."""
    
    recipe_base = await llm.generate_recipe_from_text(recipe_prompt)
    
    # Override name with normalized one
    recipe_base.name = dish_name
    
    # Step 4 & 5: Calculate nutrition and save
    print(f"[Image Pipeline] Generated recipe with {len(recipe_base.ingredients)} ingredients")
    for ing in recipe_base.ingredients[:5]:  # Show first 5
        print(f"  - {ing.name}: {ing.quantity} {ing.unit}")
    
    recipe, nutrition, tags = await persist_generated_recipe(
        db,
        llm,
        recipe_base,
        source_type="image",
        source_ref=title or "uploaded_image",
        normalized_name=dish_name,
        tags=tags,
        tag_context=description,
    )
    
    print(f"[Image Pipeline] Nutrition calculated - Calories: {nutrition.per_serving.kcal}, Protein: {nutrition.per_serving.protein}g")
    
    # Debug info
    debug = {
        "vision_description": description,
        "dish_type": vision_result["dish_type"],
        "guessed_ingredients": vision_result["guessed_ingredients"],
        "cuisine": vision_result["cuisine"]
    }
    
    return recipe, nutrition, tags, debug
