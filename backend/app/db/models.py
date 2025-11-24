"""
SQLAlchemy database models.
These define the database schema and relationships.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class RecipeModel(Base):
    """Recipe database model."""
    __tablename__ = "recipes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    servings = Column(Integer, nullable=True, default=4)
    total_time_minutes = Column(Integer, nullable=True)
    prep_time_minutes = Column(Integer, nullable=True)
    cook_time_minutes = Column(Integer, nullable=True)
    source_type = Column(String(50), nullable=False)  # "image", "url", "chat", "dataset"
    source_ref = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True)  # Recipe category from dataset
    
    # New metadata fields
    cuisine_type = Column(String(100), nullable=True)
    meal_type = Column(String(100), nullable=True)
    dish_type = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ingredients = relationship("RecipeIngredientModel", back_populates="recipe", cascade="all, delete-orphan")
    steps = relationship("RecipeStepModel", back_populates="recipe", cascade="all, delete-orphan")
    nutrition = relationship("NutritionSummaryModel", back_populates="recipe", uselist=False, cascade="all, delete-orphan")
    tags = relationship("RecipeTagModel", back_populates="recipe", cascade="all, delete-orphan")


class IngredientModel(Base):
    """Ingredient master data model."""
    __tablename__ = "ingredients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    name_norm = Column(String(255), nullable=False, index=True)
    unit_default = Column(String(20), nullable=True)
    kcal_per_100 = Column(Float, nullable=True)
    protein_per_100 = Column(Float, nullable=True)
    carbs_per_100 = Column(Float, nullable=True)
    fat_per_100 = Column(Float, nullable=True)


class RecipeIngredientModel(Base):
    """Recipe-ingredient junction with quantities."""
    __tablename__ = "recipe_ingredients"
    
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=True)
    unit = Column(String(20), nullable=True)
    
    # Relationships
    recipe = relationship("RecipeModel", back_populates="ingredients")


class RecipeStepModel(Base):
    """Recipe step model."""
    __tablename__ = "recipe_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    instruction = Column(Text, nullable=False)
    
    # Relationships
    recipe = relationship("RecipeModel", back_populates="steps")


class NutritionSummaryModel(Base):
    """Nutrition summary for a recipe."""
    __tablename__ = "nutrition_summaries"
    
    recipe_id = Column(Integer, ForeignKey("recipes.id"), primary_key=True)
    kcal_total = Column(Float, nullable=False)
    protein_total = Column(Float, nullable=False)
    carbs_total = Column(Float, nullable=False)
    fat_total = Column(Float, nullable=False)
    kcal_per_serving = Column(Float, nullable=False)
    protein_per_serving = Column(Float, nullable=False)
    carbs_per_serving = Column(Float, nullable=False)
    fat_per_serving = Column(Float, nullable=False)
    # Additional nutrition fields from dataset
    saturated_fat = Column(Float, nullable=True)
    cholesterol = Column(Float, nullable=True)
    sodium = Column(Float, nullable=True)
    fiber = Column(Float, nullable=True)
    sugar = Column(Float, nullable=True)
    
    # Relationships
    recipe = relationship("RecipeModel", back_populates="nutrition")


class RecipeTagModel(Base):
    """Recipe tags."""
    __tablename__ = "recipe_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    tag = Column(String(50), nullable=False)
    
    # Relationships
    recipe = relationship("RecipeModel", back_populates="tags")


class MenuModel(Base):
    """Weekly menu model."""
    __tablename__ = "menus"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    week_start_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    menu_recipes = relationship("MenuRecipeModel", back_populates="menu", cascade="all, delete-orphan")


class MenuRecipeModel(Base):
    """Menu-recipe junction for weekly planning."""
    __tablename__ = "menu_recipes"
    
    id = Column(Integer, primary_key=True, index=True)
    menu_id = Column(Integer, ForeignKey("menus.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0-6
    meal_type = Column(String(20), nullable=False)  # "breakfast", "lunch", "dinner"
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    
    # Relationships
    menu = relationship("MenuModel", back_populates="menu_recipes")
    recipe = relationship("RecipeModel")


class ChatSessionModel(Base):
    """Chat session model for conversation memory."""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # User preferences and context
    dietary_restrictions = Column(Text, nullable=True)  # JSON list
    favorite_cuisines = Column(Text, nullable=True)  # JSON list
    disliked_ingredients = Column(Text, nullable=True)  # JSON list
    preferred_meal_types = Column(Text, nullable=True)  # JSON list
    cooking_skill_level = Column(String(50), nullable=True)
    time_constraints = Column(Integer, nullable=True)  # Max cooking time in minutes
    
    # Relationships
    messages = relationship("ChatMessageModel", back_populates="session", cascade="all, delete-orphan")
    user_requirements = relationship("UserRequirementModel", back_populates="session", cascade="all, delete-orphan")


class ChatMessageModel(Base):
    """Individual chat message in a session."""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey("chat_sessions.session_id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    intent = Column(String(50), nullable=True)  # Detected intent
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Optional references to recipes suggested or discussed
    recipe_ids = Column(Text, nullable=True)  # JSON list of recipe IDs
    
    # Relationships
    session = relationship("ChatSessionModel", back_populates="messages")


class UserRequirementModel(Base):
    """User requirements and modifications tracked during conversation."""
    __tablename__ = "user_requirements"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey("chat_sessions.session_id"), nullable=False)
    requirement_type = Column(String(50), nullable=False)  # "ingredient", "dietary", "modification", "preference"
    key = Column(String(255), nullable=False)  # e.g., "exclude_ingredient", "add_ingredient", "cuisine_preference"
    value = Column(Text, nullable=False)  # The actual requirement value
    context = Column(Text, nullable=True)  # Additional context or reasoning
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive/overridden
    
    # Relationships
    session = relationship("ChatSessionModel", back_populates="user_requirements")
