"""
Basic tests for nutrition lookup functionality.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.unit_conversion import convert_to_grams, normalize_unit


def test_convert_grams():
    """Test gram conversion."""
    assert convert_to_grams("flour", 100, "g") == 100
    assert convert_to_grams("flour", 1, "kg") == 1000
    

def test_convert_ml():
    """Test milliliter conversion."""
    assert convert_to_grams("water", 100, "ml") == 100
    assert convert_to_grams("water", 1, "l") == 1000


def test_convert_cups():
    """Test cup conversion."""
    result = convert_to_grams("flour", 1, "cup")
    assert result == 240  # 1 cup = 240g


def test_convert_pieces():
    """Test piece conversion."""
    # Known item
    egg_weight = convert_to_grams("egg", 1, "piece")
    assert egg_weight == 50
    
    # Unknown item - should default to 100g
    unknown_weight = convert_to_grams("unknown_food", 1, "piece")
    assert unknown_weight == 100


def test_normalize_unit():
    """Test unit normalization."""
    assert normalize_unit("gram") == "g"
    assert normalize_unit("grams") == "g"
    assert normalize_unit("cup") == "cup"
    assert normalize_unit("cups") == "cup"
    assert normalize_unit("tablespoon") == "tbsp"


if __name__ == "__main__":
    print("Running tests...")
    test_convert_grams()
    print("✓ Gram conversion tests passed")
    
    test_convert_ml()
    print("✓ ML conversion tests passed")
    
    test_convert_cups()
    print("✓ Cup conversion tests passed")
    
    test_convert_pieces()
    print("✓ Piece conversion tests passed")
    
    test_normalize_unit()
    print("✓ Unit normalization tests passed")
    
    print("\n✅ All tests passed!")
