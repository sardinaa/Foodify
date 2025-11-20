"""
Application-wide constants.
Centralizes all hardcoded values to prevent duplication and improve maintainability.
"""
from typing import List, Dict


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


class HTTPConstants:
    """HTTP headers and user agents for web scraping."""
    
    USER_AGENTS: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    DEFAULT_HEADERS: Dict[str, str] = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://www.google.com/"
    }
    
    @classmethod
    def get_headers_with_user_agent(cls, user_agent: str) -> Dict[str, str]:
        """Get default headers with specified user agent."""
        return {**cls.DEFAULT_HEADERS, "User-Agent": user_agent}


class PromptConstants:
    """Constants for LLM prompts and responses."""
    
    # Temperature settings
    TEMPERATURE_CREATIVE: float = 0.7
    TEMPERATURE_PRECISE: float = 0.1
    TEMPERATURE_BALANCED: float = 0.5
    
    # Token limits
    MAX_PROMPT_TOKENS: int = 4000
    MAX_RESPONSE_TOKENS: int = 2000


class DatabaseConstants:
    """Database-related constants."""
    
    # Default values
    DEFAULT_SERVINGS: int = 4
    DEFAULT_TOTAL_TIME: int = 30
    
    # Batch sizes
    BATCH_INSERT_SIZE: int = 100
    BATCH_UPDATE_SIZE: int = 50


# Export all constants for easy import
__all__ = [
    'MenuConstants',
    'LimitsConstants', 
    'HTTPConstants',
    'PromptConstants',
    'DatabaseConstants'
]
