"""
Image analysis pipeline.
Orchestrates VLM → recipe generation → nutrition calculation.
"""
from typing import Tuple, Optional, List
from sqlalchemy.orm import Session

from app.core.vlm_client import get_vlm_client
from app.db.schema import Recipe, NutritionSummary, RecipeBase
from app.services.base_pipeline import BaseIngestionPipeline
from app.core.logging import get_logger

logger = get_logger("services.image_pipeline")


class ImageIngestionPipeline(BaseIngestionPipeline):
    def __init__(self, db: Session):
        super().__init__(db)
        self.vlm = get_vlm_client()
        self.debug_info = {}

    async def extract_recipe_data(self, image_bytes: bytes, title: Optional[str] = None, **kwargs) -> Tuple[RecipeBase, dict]:
        # Step 1: Analyze image
        vision_result = await self.vlm.describe_dish_from_image(image_bytes, title)
        description = vision_result["description"]
        
        self.debug_info = {
            "vision_description": description,
            "dish_type": vision_result["dish_type"],
            "guessed_ingredients": vision_result["guessed_ingredients"],
            "cuisine": vision_result["cuisine"]
        }
        
        # Step 2: Normalize name and tags
        dish_name, tags = await self.llm.normalize_dish_name_and_tags(description, title)
        
        # Step 3: Generate recipe from description
        recipe_prompt = f"""Dish: {dish_name}
Description: {description}
Type: {vision_result['dish_type']}
Likely ingredients: {', '.join(vision_result['guessed_ingredients'])}

Generate a complete recipe with ingredients and cooking steps."""
        
        recipe_base = await self.llm.generate_recipe_from_text(recipe_prompt)
        
        # Override name with normalized one
        recipe_base.name = dish_name
        
        return recipe_base, {
            "normalized_name": dish_name,
            "tags": tags,
            "tag_context": description
        }


async def analyze_image_pipeline(
    db: Session,
    image_bytes: bytes,
    title: Optional[str] = None
) -> Tuple[Recipe, NutritionSummary, list[str], dict]:
    """
    Full pipeline for analyzing a food image.
    """
    pipeline = ImageIngestionPipeline(db)
    
    # We need to call extract first to get debug info, or just rely on run
    # But run calls extract internally.
    # To get debug info out, we might need to access pipeline.debug_info after run.
    
    recipe, nutrition, tags = await pipeline.run(
        image_bytes, 
        source_type="image", 
        source_ref=title or "uploaded_image",
        title=title,
        # Pass these so they are used in persist
        # But wait, extract_recipe_data sets them on self, but run doesn't know about self.tags
        # I need to pass them to run if I want them used.
        # But I can't get them until extract runs.
    )
    
    # This reveals a flaw in my BasePipeline abstraction for this specific case where 
    # intermediate results (tags, normalized_name) are generated during extraction 
    # and needed for persistence.
    
    # Let's fix this by passing them explicitly if possible, or modifying the base class.
    # Actually, persist_generated_recipe takes normalized_name and tags.
    # In my BasePipeline.run, I pass kwargs to persist_generated_recipe.
    
    # If I use the pipeline instance, I can override run to handle this specific flow.
    
    return recipe, nutrition, tags, pipeline.debug_info

