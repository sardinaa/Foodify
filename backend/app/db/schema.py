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
    ingredients: List[IngredientBase]
    steps: List[RecipeStepBase]


class RecipeCreate(RecipeBase):
    """Recipe creation schema."""
    source_type: str  # "chat", "dataset"
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
