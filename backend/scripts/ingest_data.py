#!/usr/bin/env python3
"""
Data ingestion script for loading recipe dataset into ChromaDB and SQL Database.
Loads recipes from HuggingFace dataset: datahiveai/recipes-with-nutrition
"""
import sys
import os
import ast
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from datasets import load_dataset
from sqlalchemy.orm import Session
from app.services.recipe_vectorstore import get_vector_store
from app.core.config import get_settings
from app.db.session import SessionLocal, engine, init_db
from app.db.models import (
    Base, RecipeModel, RecipeIngredientModel, RecipeStepModel, 
    NutritionSummaryModel, RecipeTagModel
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_list(value):
    """Parse stringified list or return list."""
    if not value: return []
    if isinstance(value, list): return value
    try:
        return ast.literal_eval(value)
    except:
        return []

def parse_dict(value):
    """Parse stringified dict or return dict."""
    if not value: return {}
    if isinstance(value, dict): return value
    try:
        return ast.literal_eval(value)
    except:
        return {}

def get_nutrient(nutrients: Dict, key: str) -> float:
    """Extract nutrient quantity safely."""
    if not nutrients: return 0.0
    
    # Try direct key
    if key in nutrients:
        return float(nutrients[key].get('quantity', 0.0))
        
    # Try finding by label
    for k, v in nutrients.items():
        if v.get('label') == key:
            return float(v.get('quantity', 0.0))
            
    return 0.0

def main(reset: bool = False, max_recipes: int = None):
    """
    Load recipes from HuggingFace dataset and ingest into ChromaDB and SQL DB.
    """
    settings = get_settings()
    
    logger.info(f"Loading dataset: datahiveai/recipes-with-nutrition")
    logger.info(f"Max recipes: {max_recipes or 'ALL'}")
    
    # Reset Database if requested
    if reset:
        logger.info("⚠️  Resetting SQL Database...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("✅ SQL Database reset complete.")

    # Load dataset from HuggingFace
    try:
        dataset = load_dataset("datahiveai/recipes-with-nutrition", split="train")
        logger.info(f"Dataset loaded: {len(dataset)} recipes available")
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        return 1
    
    # Limit if specified
    if max_recipes and max_recipes < len(dataset):
        dataset = dataset.select(range(max_recipes))
        logger.info(f"Limited to {len(dataset)} recipes")
    
    # Initialize vector store
    vector_store = get_vector_store(
        persist_directory=settings.vector_store_path,
        embedding_model=settings.embedding_model
    )
    
    if reset:
        logger.info("⚠️  Clearing Vector Store...")
        vector_store.clear()
        logger.info("✅ Vector Store cleared.")
    
    db = SessionLocal()
    recipes_for_vector = []
    
    try:
        logger.info("Processing recipes...")
        count = 0
        
        for i, item in enumerate(dataset):
            try:
                # Parse fields
                name = item.get('recipe_name') or item.get('name') or item.get('Name')
                if not name: continue
                
                description = item.get('description') or item.get('Description')
                
                # Parse lists
                ingredients_raw = item.get('ingredients')
                ingredient_names = []
                
                instructions = parse_list(item.get('instructions'))
                if not instructions:
                    instructions = parse_list(item.get('RecipeInstructions'))
                
                diet_labels = parse_list(item.get('diet_labels'))
                health_labels = parse_list(item.get('health_labels'))
                
                # Parse nutrition
                nutrients = parse_dict(item.get('total_nutrients'))
                
                # Create RecipeModel
                recipe = RecipeModel(
                    name=name,
                    description=description,
                    servings=int(float(item.get('servings') or item.get('RecipeServings') or 4)),
                    source_type="dataset",
                    category=item.get('category') or item.get('RecipeCategory'),
                    cuisine_type=item.get('cuisine_type'),
                    meal_type=item.get('meal_type'),
                    dish_type=item.get('dish_type')
                )
                db.add(recipe)
                db.flush() # Get ID
                
                # Add Ingredients
                if ingredients_raw:
                    if isinstance(ingredients_raw, str):
                         ingredients_raw = parse_list(ingredients_raw)
                    
                    for ing in ingredients_raw:
                        if isinstance(ing, dict):
                            ing_name = ing.get('food')
                            quantity = ing.get('quantity')
                            unit = ing.get('measure')
                            if ing_name:
                                db.add(RecipeIngredientModel(
                                    recipe_id=recipe.id,
                                    ingredient_name=str(ing_name)[:255],
                                    quantity=float(quantity) if quantity else None,
                                    unit=str(unit)[:20] if unit else None
                                ))
                                ingredient_names.append(ing_name)
                
                # Fallback to ingredient lines if no structured ingredients found
                if not ingredient_names:
                    lines = parse_list(item.get('ingredient_lines'))
                    if not lines:
                        lines = parse_list(item.get('RecipeIngredientParts'))
                        
                    for line in lines:
                        if line:
                            db.add(RecipeIngredientModel(
                                recipe_id=recipe.id,
                                ingredient_name=str(line)[:255],
                                quantity=None,
                                unit=None
                            ))
                            ingredient_names.append(line)
                
                # Add Steps
                for i, step in enumerate(instructions):
                    if step:
                        db.add(RecipeStepModel(
                            recipe_id=recipe.id,
                            step_number=i+1,
                            instruction=step
                        ))
                
                # Add Tags
                all_tags = set(diet_labels + health_labels)
                for tag in all_tags:
                    if tag:
                        db.add(RecipeTagModel(
                            recipe_id=recipe.id,
                            tag=tag[:50]
                        ))
                
                # Add Nutrition
                # Map fields based on dataset's actual nutrient labels
                nutrition = NutritionSummaryModel(
                    recipe_id=recipe.id,
                    kcal_total=get_nutrient(nutrients, 'Energy'),
                    protein_total=get_nutrient(nutrients, 'Protein'),
                    fat_total=get_nutrient(nutrients, 'Fat'),
                    carbs_total=get_nutrient(nutrients, 'Carbs'),
                    fiber=get_nutrient(nutrients, 'Fiber'),
                    sugar=get_nutrient(nutrients, 'Sugars'),
                    saturated_fat=get_nutrient(nutrients, 'Saturated'),
                    cholesterol=get_nutrient(nutrients, 'Cholesterol'),
                    sodium=get_nutrient(nutrients, 'Sodium'),
                    # Per serving calculations (approximate)
                    kcal_per_serving=get_nutrient(nutrients, 'Energy') / (recipe.servings or 1),
                    protein_per_serving=get_nutrient(nutrients, 'Protein') / (recipe.servings or 1),
                    fat_per_serving=get_nutrient(nutrients, 'Fat') / (recipe.servings or 1),
                    carbs_per_serving=get_nutrient(nutrients, 'Carbs') / (recipe.servings or 1),
                )
                db.add(nutrition)
                
                # Prepare for Vector Store
                # We pass the parsed data to avoid re-parsing in vector store
                vector_recipe = {
                    "id": recipe.id,
                    "name": recipe.name,
                    "description": recipe.description,
                    "category": recipe.category,
                    "cuisine_type": recipe.cuisine_type,
                    "meal_type": recipe.meal_type,
                    "dish_type": recipe.dish_type,
                    "ingredients": ingredient_names,
                    "instructions": instructions,
                    "diet_labels": diet_labels,
                    "health_labels": health_labels,
                    "servings": recipe.servings,
                    "calories": nutrition.kcal_per_serving,
                    "protein": nutrition.protein_per_serving,
                    "carbs": nutrition.carbs_per_serving,
                    "fat": nutrition.fat_per_serving,
                    "fiber": nutrition.fiber / (recipe.servings or 1),
                    "sugar": nutrition.sugar / (recipe.servings or 1),
                    "saturated_fat": nutrition.saturated_fat / (recipe.servings or 1),
                    "cholesterol": nutrition.cholesterol / (recipe.servings or 1),
                    "sodium": nutrition.sodium / (recipe.servings or 1),
                }
                recipes_for_vector.append(vector_recipe)
                
                count += 1
                if count % 100 == 0:
                    db.commit()
                    logger.info(f"Processed {count} recipes...")
                    
            except Exception as e:
                logger.warning(f"Error processing recipe index {count}: {e}")
                db.rollback()
                continue
        
        db.commit()
        logger.info(f"✅ SQL Ingestion complete. Total: {count}")
        
        # Ingest into Vector Store
        logger.info("Ingesting into Vector Store...")
        vector_store.add_recipes(recipes_for_vector, batch_size=100)
        logger.info("✅ Vector Store Ingestion complete.")
        
        # Copy databases to backend directory
        logger.info("Copying databases to backend directory...")
        import shutil
        repo_root = Path(__file__).parent.parent.parent
        backend_dir = repo_root / "backend"
        
        # Copy SQLite database
        src_db = repo_root / "foodify.db"
        dst_db = backend_dir / "foodify.db"
        if src_db.exists():
            shutil.copy2(src_db, dst_db)
            logger.info(f"✅ Copied {src_db} -> {dst_db}")
        
        # Copy ChromaDB directory
        src_chroma = repo_root / "chroma_db"
        dst_chroma = backend_dir / "chroma_db"
        if src_chroma.exists():
            if dst_chroma.exists():
                shutil.rmtree(dst_chroma)
            shutil.copytree(src_chroma, dst_chroma)
            logger.info(f"✅ Copied {src_chroma} -> {dst_chroma}")
        
        logger.info("✅ Database sync complete.")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        db.rollback()
        return 1
    finally:
        db.close()
        
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest recipes into Foodify")
    parser.add_argument("--reset", action="store_true", help="Reset database and vector store")
    parser.add_argument("--max_recipes", type=int, default=None, help="Limit number of recipes")
    args = parser.parse_args()
    
    sys.exit(main(reset=args.reset, max_recipes=args.max_recipes))
