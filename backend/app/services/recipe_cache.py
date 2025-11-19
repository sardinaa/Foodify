"""
Recipe cache for quick lookup of full recipe details.
Loads dataset lazily and caches lookups.
"""
from typing import Dict, Any, Optional
from datasets import load_dataset
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)


class RecipeCache:
    """Singleton cache for recipe dataset."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._dataset = None
            cls._instance._recipe_map = None
        return cls._instance
    
    def _load_dataset(self):
        """Load the dataset if not already loaded."""
        if self._dataset is None:
            logger.info("Loading recipe dataset for cache...")
            settings = get_settings()
            self._dataset = load_dataset(settings.recipes_dataset, split="train")
            
            # Build recipe ID map for fast lookup
            self._recipe_map = {}
            for idx, item in enumerate(self._dataset):
                recipe_id = str(item.get("RecipeId"))
                self._recipe_map[recipe_id] = idx
            
            logger.info(f"Recipe cache loaded: {len(self._recipe_map)} recipes")
    
    def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """
        Get recipe from dataset by ID.
        
        Args:
            recipe_id: The recipe ID to look up
            
        Returns:
            Recipe dictionary or None if not found
        """
        self._load_dataset()
        
        if recipe_id not in self._recipe_map:
            return None
        
        idx = self._recipe_map[recipe_id]
        return self._dataset[idx]
