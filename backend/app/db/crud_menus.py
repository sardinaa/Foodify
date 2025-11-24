"""
CRUD operations for menus.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.models import MenuModel, MenuRecipeModel
from app.db.base_crud import CRUDBase


class MenuCreate(BaseModel):
    name: str
    week_start_date: str


class CRUDMenu(CRUDBase[MenuModel, MenuCreate, MenuCreate]):
    def create_with_items(
        self,
        db: Session,
        name: str,
        week_start_date: str,
        menu_recipes: List[dict]
    ) -> MenuModel:
        """
        Create a new weekly menu.
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


menu = CRUDMenu(MenuModel)

