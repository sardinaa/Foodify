"""
Pydantic schemas for API request/response models.
These define the structure of data flowing through the API.
"""
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class IngredientBase(BaseModel):
    """Base ingredient model."""
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None


class RecipeStepBase(BaseModel):
    """Recipe step model."""
    step_number: int
    instruction: str


class RecipeBase(BaseModel):
    """Base recipe model."""
    name: str
    description: Optional[str] = None
    servings: Optional[int] = 4  # Default to 4 servings if not specified
    total_time_minutes: Optional[int] = None
    ingredients: List[IngredientBase]
    steps: List[RecipeStepBase]


class RecipeCreate(RecipeBase):
    """Recipe creation schema."""
    source_type: str  # "image", "url", "chat"
    source_ref: Optional[str] = None
    tags: List[str] = []


class Recipe(RecipeBase):
    """Complete recipe with ID and metadata."""
    id: int
    source_type: str
    source_ref: Optional[str]
    tags: List[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class NutritionBase(BaseModel):
    """Nutrition information."""
    kcal: float
    protein: float
    carbs: float
    fat: float


class NutritionSummary(BaseModel):
    """Complete nutrition summary for a recipe."""
    recipe_id: int
    total: NutritionBase
    per_serving: NutritionBase
    
    model_config = {"from_attributes": True}


class AnalyzeImageRequest(BaseModel):
    """Request schema for image analysis (multipart handled separately)."""
    title: Optional[str] = None


class AnalyzeImageResponse(BaseModel):
    """Response schema for image analysis."""
    recipe: Recipe
    nutrition: NutritionSummary
    tags: List[str]
    debug: Optional[Dict] = None


class AnalyzeUrlRequest(BaseModel):
    """Request schema for URL analysis."""
    url: str


class AnalyzeUrlResponse(BaseModel):
    """Response schema for URL analysis."""
    recipe: Recipe
    nutrition: NutritionSummary
    tags: List[str]


class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    session_id: str
    message: str
    image_present: bool = False


class WeeklyMenuDay(BaseModel):
    """Single day in a weekly menu."""
    day_of_week: int  # 0-6
    day_name: str
    breakfast: Optional[Recipe] = None
    lunch: Optional[Recipe] = None
    dinner: Optional[Recipe] = None


class WeeklyMenu(BaseModel):
    """Weekly menu plan."""
    name: str
    week_start_date: str
    days: List[WeeklyMenuDay]


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""
    reply: str
    suggested_recipes: List[Dict] = []  # Changed to Dict to support extra fields like day_name/meal_type
    weekly_menu: Optional[WeeklyMenu] = None


class UserPreferences(BaseModel):
    """User preferences for recipe recommendations."""
    dietary_restrictions: List[str] = []
    favorite_cuisines: List[str] = []
    disliked_ingredients: List[str] = []
    preferred_meal_types: List[str] = []
    cooking_skill_level: Optional[str] = None
    time_constraints: Optional[int] = None


class UserRequirement(BaseModel):
    """Individual user requirement tracked during conversation."""
    id: int
    requirement_type: str  # "ingredient", "dietary", "modification", "preference"
    key: str
    value: str
    context: Optional[str] = None
    created_at: datetime
    is_active: bool = True
    
    model_config = {"from_attributes": True}


class ChatMessage(BaseModel):
    """Chat message in a conversation."""
    id: int
    role: str  # "user" or "assistant"
    content: str
    intent: Optional[str] = None
    recipe_ids: Optional[List[int]] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    """Summary of a conversation session."""
    session_id: str
    created_at: str
    updated_at: str
    preferences: UserPreferences
    message_count: int
    recent_messages: List[Dict]
    active_requirements: List[Dict]
