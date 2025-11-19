#!/usr/bin/env python3
"""
Test script to verify prompt loading functionality.
"""
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.utils.prompt_loader import get_prompt_loader

def test_prompt_loading():
    """Test that all prompts can be loaded correctly."""
    loader = get_prompt_loader()
    
    print("Testing Prompt Loader...")
    print("=" * 60)
    
    # Test LLM prompts
    print("\n1. Testing LLM Prompts:")
    print("-" * 60)
    
    recipe_extraction = loader.get_llm_prompt("recipe_extraction")
    print(f"✓ Recipe Extraction System Prompt: {len(recipe_extraction.get('system', ''))} chars")
    
    dish_norm = loader.get_llm_prompt("dish_normalization")
    print(f"✓ Dish Normalization Template: {len(dish_norm.get('template', ''))} chars")
    
    ingredients = loader.get_llm_prompt("ingredients_to_recipes")
    print(f"✓ Ingredients to Recipes Template: {len(ingredients.get('template', ''))} chars")
    
    weekly_menu = loader.get_llm_prompt("weekly_menu_planning")
    print(f"✓ Weekly Menu Planning Template: {len(weekly_menu.get('template', ''))} chars")
    
    # Test VLM prompts
    print("\n2. Testing VLM Prompts:")
    print("-" * 60)
    
    dish_desc = loader.get_vlm_prompt("dish_description")
    print(f"✓ Dish Description Template: {len(dish_desc.get('template', ''))} chars")
    
    # Test RAG prompts
    print("\n3. Testing RAG Prompts:")
    print("-" * 60)
    
    rag_recs = loader.get_rag_prompt("recipe_recommendations")
    print(f"✓ Recipe Recommendations Template: {len(rag_recs.get('template', ''))} chars")
    
    recipe_item = loader.get_rag_prompt("recipe_context_item")
    print(f"✓ Recipe Context Item Template: {len(recipe_item.get('template', ''))} chars")
    
    constraints = loader.get_rag_prompt("constraints")
    print(f"✓ Constraints Config: {len(str(constraints))} chars")
    
    # Test prompt formatting
    print("\n4. Testing Prompt Formatting:")
    print("-" * 60)
    
    formatted = loader.format_prompt(
        "Hello {name}, you have {count} items.",
        name="Chef",
        count=5
    )
    expected = "Hello Chef, you have 5 items."
    assert formatted == expected, f"Expected '{expected}', got '{formatted}'"
    print(f"✓ Format test passed: '{formatted}'")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! Prompts are loading correctly.")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_prompt_loading()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
