"""
CRUD operations for menus.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import MenuModel, MenuRecipeModel


def create_menu(
    db: Session,
    name: str,
    week_start_date: str,
    menu_recipes: List[dict]
) -> MenuModel:
    """
    Create a new weekly menu.
    
    Args:
        db: Database session
        name: Menu name
        week_start_date: Start date (YYYY-MM-DD)
        menu_recipes: List of dicts with keys: day_of_week, meal_type, recipe_id
    """
    menu = MenuModel(
        name=name,
        week_start_date=week_start_date
    )
    db.add(menu)
    db.flush()
    
    for mr in menu_recipes:
        menu_recipe = MenuRecipeModel(
            menu_id=menu.id,
            day_of_week=mr["day_of_week"],
            meal_type=mr["meal_type"],
            recipe_id=mr["recipe_id"]
        )
        db.add(menu_recipe)
    
    db.commit()
    db.refresh(menu)
    return menu


def get_menu(db: Session, menu_id: int) -> Optional[MenuModel]:
    """Get a menu by ID."""
    return db.query(MenuModel).filter(MenuModel.id == menu_id).first()


def get_menus(db: Session, skip: int = 0, limit: int = 20) -> List[MenuModel]:
    """Get all menus with pagination."""
    return db.query(MenuModel).offset(skip).limit(limit).all()
