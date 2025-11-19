"""
Utility to parse recipe data from various formats.
Converts JSON-LD Recipe schema directly to RecipeBase without LLM.
"""
import re
from typing import Optional
from app.db.schema import RecipeBase, IngredientBase, RecipeStepBase


def parse_iso_duration(duration_str: str) -> Optional[int]:
    """
    Parse ISO 8601 duration (e.g., 'P0DT0H36M') to minutes.
    
    Args:
        duration_str: ISO 8601 duration string
    
    Returns:
        Duration in minutes or None
    """
    if not duration_str:
        return None
    
    # Match pattern like PT30M, PT1H30M, P0DT0H36M
    pattern = r'PT?(?:(\d+)H)?(?:(\d+)M)?'
    match = re.search(pattern, duration_str)
    
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        return hours * 60 + minutes
    
    return None


def parse_ingredient(ingredient_str: str) -> IngredientBase:
    """
    Parse ingredient string like '400g Arroz arborio' or '2 cups flour' into components.
    
    Args:
        ingredient_str: Ingredient string with quantity, unit, and name
    
    Returns:
        IngredientBase object
    """
    ingredient_str = ingredient_str.strip()
    
    # Pattern: number + optional unit + name
    # Matches: "400g rice", "2 cups flour", "1.5l milk", "2 onions"
    pattern = r'^([\d./]+)\s*([a-zA-Z]+)?\s+(.+)$'
    match = re.match(pattern, ingredient_str)
    
    if match:
        quantity_str, unit, name = match.groups()
        try:
            # Handle fractions like "1/2"
            if '/' in quantity_str:
                parts = quantity_str.split('/')
                quantity = float(parts[0]) / float(parts[1])
            else:
                quantity = float(quantity_str)
        except (ValueError, ZeroDivisionError):
            quantity = None
        
        return IngredientBase(
            name=name.strip(),
            quantity=quantity,
            unit=unit.strip() if unit else None
        )
    else:
        # No quantity/unit found, entire string is the ingredient name
        return IngredientBase(
            name=ingredient_str,
            quantity=None,
            unit=None
        )


def json_ld_to_recipe(json_ld: dict) -> RecipeBase:
    """
    Convert JSON-LD Recipe schema to RecipeBase.
    
    Args:
        json_ld: JSON-LD Recipe object
    
    Returns:
        RecipeBase object
    """
    # Extract basic info
    name = json_ld.get('name', 'Unknown Recipe')
    description = json_ld.get('description', '')
    
    # Parse servings
    servings_raw = json_ld.get('recipeYield')
    servings = None
    if servings_raw:
        if isinstance(servings_raw, int):
            servings = servings_raw
        elif isinstance(servings_raw, str):
            # Try to extract number from string like "4 servings"
            match = re.search(r'\d+', str(servings_raw))
            if match:
                servings = int(match.group())
    
    # Parse time
    total_time_str = json_ld.get('totalTime') or json_ld.get('cookTime')
    total_time_minutes = parse_iso_duration(total_time_str) if total_time_str else None
    
    # Parse ingredients
    ingredients_raw = json_ld.get('recipeIngredient', [])
    if not isinstance(ingredients_raw, list):
        ingredients_raw = [ingredients_raw]
    
    ingredients = []
    for ing_str in ingredients_raw:
        # Filter out empty or whitespace-only strings
        if ing_str and str(ing_str).strip():
            ingredients.append(parse_ingredient(str(ing_str).strip()))
    
    # Parse instructions
    instructions_raw = json_ld.get('recipeInstructions', '')
    steps = []
    
    if isinstance(instructions_raw, list):
        # List of instruction objects or strings
        step_num = 1
        for ins in instructions_raw:
            if isinstance(ins, dict):
                text = ins.get('text', '') or ins.get('itemListElement', '') or ''
            else:
                text = str(ins)
            
            # Only add if there's actual text content
            text = text.strip()
            if text and len(text) > 3:  # Ignore empty or very short strings
                steps.append(RecipeStepBase(step_number=step_num, instruction=text))
                step_num += 1
    elif isinstance(instructions_raw, str):
        # Single string - split by paragraphs or sentences
        instr_text = instructions_raw.strip()
        # Split by double newline first
        paragraphs = instr_text.split('\n\n')
        if len(paragraphs) == 1:
            # Try splitting by single newline
            paragraphs = instr_text.split('\n')
        
        step_num = 1
        for para in paragraphs:
            para = para.strip()
            if para and len(para) > 10:  # Ignore very short lines
                steps.append(RecipeStepBase(step_number=step_num, instruction=para))
                step_num += 1
    
    return RecipeBase(
        name=name,
        description=description,
        servings=servings or 4,
        total_time_minutes=total_time_minutes,
        ingredients=ingredients,
        steps=steps
    )
