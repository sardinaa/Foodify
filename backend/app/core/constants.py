"""
Application-wide constants.
Centralizes all hardcoded values to prevent duplication and improve maintainability.
"""
from typing import List


class MenuConstants:
    """Constants related to menu planning and meal organization."""
    
    DAYS_OF_WEEK: List[str] = [
        "Monday", 
        "Tuesday", 
        "Wednesday", 
        "Thursday", 
        "Friday", 
        "Saturday", 
        "Sunday"
    ]
    
    MEAL_TYPES: List[str] = ["breakfast", "lunch", "dinner"]
    
    # Defaults for menu generation
    DEFAULT_DAYS: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    DEFAULT_MEALS: List[str] = ["dinner"]
    
    @classmethod
    def is_valid_day(cls, day: str) -> bool:
        """Check if day name is valid."""
        return day in cls.DAYS_OF_WEEK
    
    @classmethod
    def is_valid_meal(cls, meal: str) -> bool:
        """Check if meal type is valid."""
        return meal.lower() in cls.MEAL_TYPES


class LimitsConstants:
    """Limits and thresholds used throughout the application."""
    
    # Memory and history
    MEMORY_HISTORY_LIMIT: int = 10
    MEMORY_DEFAULT_LIMIT: int = 5
    
    # Recipe display and recommendations
    TOP_RECIPES_COUNT: int = 3
    MAX_RECIPES_DISPLAY: int = 10
    
    # HTTP and network
    HTTP_TIMEOUT_SECONDS: float = 30.0
    HTTP_MIN_CONTENT_LENGTH: int = 100
    HTTP_MAX_CONTENT_LENGTH: int = 500
    
    # Recipe preview (for display purposes)
    INGREDIENT_PREVIEW_COUNT: int = 10
    STEP_PREVIEW_COUNT: int = 3
    
    # RAG and vector search
    RAG_TOP_K_RESULTS: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.5


# Export all constants for easy import
__all__ = [
    'MenuConstants',
    'LimitsConstants'
]
