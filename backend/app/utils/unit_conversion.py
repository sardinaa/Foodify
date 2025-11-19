"""
Unit conversion utilities for recipe ingredients.
Simple hard-coded mappings for common units and pieces.
"""
from typing import Optional


# Approximate weights for common "piece" items (in grams)
PIECE_WEIGHTS = {
    "egg": 50,
    "eggs": 50,
    "onion": 150,
    "onions": 150,
    "tomato": 123,
    "tomatoes": 123,
    "potato": 170,
    "potatoes": 170,
    "carrot": 61,
    "carrots": 61,
    "apple": 182,
    "apples": 182,
    "banana": 118,
    "bananas": 118,
    "garlic clove": 3,
    "garlic cloves": 3,
    "lemon": 58,
    "lemons": 58,
    "lime": 67,
    "limes": 67,
    "orange": 131,
    "oranges": 131,
    "bell pepper": 119,
    "bell peppers": 119,
    "chicken breast": 174,
    "chicken breasts": 174,
}


def convert_to_grams(ingredient_name: str, quantity: float, unit: str) -> Optional[float]:
    """
    Convert ingredient quantity to grams.
    
    Args:
        ingredient_name: Name of the ingredient
        quantity: Amount
        unit: Unit of measurement
    
    Returns:
        Weight in grams, or None if conversion not possible
    """
    # Handle None values
    if not unit or not ingredient_name:
        return None
    
    unit_lower = unit.lower().strip()
    ingredient_lower = ingredient_name.lower().strip()
    
    # Already in grams
    if unit_lower in ["g", "gram", "grams"]:
        return quantity
    
    # Kilograms
    if unit_lower in ["kg", "kilogram", "kilograms"]:
        return quantity * 1000
    
    # Milliliters (assume 1:1 with grams for liquids - rough approximation)
    if unit_lower in ["ml", "milliliter", "milliliters", "cc"]:
        return quantity
    
    # Liters
    if unit_lower in ["l", "liter", "liters", "litre", "litres"]:
        return quantity * 1000
    
    # Cups (US cup = ~240ml = ~240g for water-like liquids)
    if unit_lower in ["cup", "cups"]:
        return quantity * 240
    
    # Tablespoons (~15g)
    if unit_lower in ["tbsp", "tablespoon", "tablespoons"]:
        return quantity * 15
    
    # Teaspoons (~5g)
    if unit_lower in ["tsp", "teaspoon", "teaspoons"]:
        return quantity * 5
    
    # Ounces (28.35g per oz)
    if unit_lower in ["oz", "ounce", "ounces"]:
        return quantity * 28.35
    
    # Pounds (453.6g per lb)
    if unit_lower in ["lb", "lbs", "pound", "pounds"]:
        return quantity * 453.6
    
    # Pieces - check if we have a weight mapping
    if unit_lower in ["piece", "pieces", "whole", "item", "items", "unit", "units", ""]:
        # Try to find the ingredient in our piece weights
        for key, weight in PIECE_WEIGHTS.items():
            if key in ingredient_lower:
                return quantity * weight
        
        # Default for unknown pieces (100g)
        return quantity * 100
    
    # Unknown unit - return None
    return None


def normalize_unit(unit: str) -> str:
    """Normalize unit name to a standard form."""
    if not unit:
        return ""
    
    unit_lower = unit.lower().strip()
    
    # Map to standard units
    unit_map = {
        "g": "g", "gram": "g", "grams": "g",
        "kg": "kg", "kilogram": "kg", "kilograms": "kg",
        "ml": "ml", "milliliter": "ml", "milliliters": "ml",
        "l": "l", "liter": "l", "liters": "l",
        "cup": "cup", "cups": "cup",
        "tbsp": "tbsp", "tablespoon": "tbsp", "tablespoons": "tbsp",
        "tsp": "tsp", "teaspoon": "tsp", "teaspoons": "tsp",
        "oz": "oz", "ounce": "oz", "ounces": "oz",
        "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
        "piece": "piece", "pieces": "piece", "whole": "piece",
    }
    
    return unit_map.get(unit_lower, unit_lower)
