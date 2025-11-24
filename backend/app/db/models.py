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
    source_type = Column(String(50), nullable=False)  # "chat", "dataset"
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
    """Recipe tag model for categorization."""
    __tablename__ = "recipe_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    tag = Column(String(100), nullable=False)
    
    # Relationships
    recipe = relationship("RecipeModel", back_populates="tags")
