"""
Nutrition lookup from CSV data with fuzzy matching.
Estimates macronutrients for ingredients and complete recipes.
"""
import pandas as pd
from typing import Optional, Dict
from functools import lru_cache
from rapidfuzz import fuzz, process

from app.core.config import get_settings
from app.utils.unit_conversion import convert_to_grams
from app.db.schema import RecipeBase, NutritionBase


class NutritionLookup:
    """Handles nutrition data loading and ingredient matching."""
    
    def __init__(self):
        self._df: Optional[pd.DataFrame] = None
    
    @property
    def df(self) -> pd.DataFrame:
        """Lazy-load nutrition DataFrame."""
        if self._df is None:
            settings = get_settings()
            self._df = pd.read_csv(settings.nutrition_data_path)
            
            # Normalize names for matching
            # Try 'name' first (our CSV format), then 'Food', then first column
            if 'name' in self._df.columns:
                self._df['name_norm'] = self._df['name'].str.lower().str.strip()
            elif 'Food' in self._df.columns:
                self._df['name_norm'] = self._df['Food'].str.lower().str.strip()
            else:
                self._df['name_norm'] = self._df.iloc[:, 0].str.lower().str.strip()
            
            # Ensure numeric columns (handle both column name formats)
            # Our CSV uses: kcal, protein, carbs, fat
            numeric_cols = ['kcal', 'protein', 'carbs', 'fat']
            for col in numeric_cols:
                if col in self._df.columns:
                    self._df[col] = pd.to_numeric(self._df[col], errors='coerce').fillna(0)
        
        return self._df
    
    def find_best_match(self, ingredient_name: str, threshold: int = 60) -> Optional[pd.Series]:
        """
        Find the best matching ingredient in the database using fuzzy matching.
        
        Args:
            ingredient_name: Name to search for
            threshold: Minimum similarity score (0-100)
        
        Returns:
            Pandas Series with nutrition data, or None if no good match
        """
        ingredient_norm = ingredient_name.lower().strip()
        
        # Try exact match first
        exact_match = self.df[self.df['name_norm'] == ingredient_norm]
        if not exact_match.empty:
            return exact_match.iloc[0]
        
        # Fuzzy matching
        choices = self.df['name_norm'].tolist()
        result = process.extractOne(
            ingredient_norm,
            choices,
            scorer=fuzz.ratio,
            score_cutoff=threshold
        )
        
        if result:
            match_name, score, idx = result
            return self.df.iloc[idx]
        
        return None
    
    def estimate_macros(self, ingredient_name: str, grams: float) -> Optional[Dict[str, float]]:
        """
        Estimate macronutrients for a given amount of an ingredient.
        
        Args:
            ingredient_name: Name of the ingredient
            grams: Amount in grams
        
        Returns:
            Dict with kcal, protein, carbs, fat or None if no match found
        """
        match = self.find_best_match(ingredient_name)
        
        if match is None:
            return None
        
        # Get per-100g values (our CSV uses lowercase column names)
        kcal_per_100 = match.get('kcal', 0)
        protein_per_100 = match.get('protein', 0)
        carbs_per_100 = match.get('carbs', 0)
        fat_per_100 = match.get('fat', 0)
        
        # Scale to actual amount
        factor = grams / 100.0
        
        return {
            "kcal": round(kcal_per_100 * factor, 1),
            "protein": round(protein_per_100 * factor, 1),
            "carbs": round(carbs_per_100 * factor, 1),
            "fat": round(fat_per_100 * factor, 1)
        }


# Global instance
_nutrition_lookup: Optional[NutritionLookup] = None


def get_nutrition_lookup() -> NutritionLookup:
    """Get or create global NutritionLookup instance."""
    global _nutrition_lookup
    if _nutrition_lookup is None:
        _nutrition_lookup = NutritionLookup()
    return _nutrition_lookup


def estimate_recipe_nutrition(recipe: RecipeBase) -> tuple[NutritionBase, NutritionBase]:
    """
    Estimate total and per-serving nutrition for a recipe.
    
    Args:
        recipe: Recipe with ingredients list
    
    Returns:
        Tuple of (total_nutrition, per_serving_nutrition)
    """
    lookup = get_nutrition_lookup()
    
    # Accumulate totals
    total_kcal = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0
    
    for ingredient in recipe.ingredients:
        # Convert to grams
        grams = convert_to_grams(
            ingredient.name,
            ingredient.quantity,
            ingredient.unit
        )
        
        if grams is None:
            # Skip if we can't convert
            continue
        
        # Get macros
        macros = lookup.estimate_macros(ingredient.name, grams)
        
        if macros:
            total_kcal += macros["kcal"]
            total_protein += macros["protein"]
            total_carbs += macros["carbs"]
            total_fat += macros["fat"]
    
    # Calculate per-serving
    servings = recipe.servings if recipe.servings and recipe.servings > 0 else 1
    
    total = NutritionBase(
        kcal=round(total_kcal, 1),
        protein=round(total_protein, 1),
        carbs=round(total_carbs, 1),
        fat=round(total_fat, 1)
    )
    
    per_serving = NutritionBase(
        kcal=round(total_kcal / servings, 1),
        protein=round(total_protein / servings, 1),
        carbs=round(total_carbs / servings, 1),
        fat=round(total_fat / servings, 1)
    )
    
    return total, per_serving
