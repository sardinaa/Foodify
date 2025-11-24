"""
API routes for recipe search and filtering.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import logging
from sqlalchemy.orm import Session

from app.services.recipe_vectorstore import get_vector_store
from app.core.config import get_settings
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/recipes", tags=["Recipe Search"])

# Initialize vector store
settings = get_settings()
vector_store = get_vector_store(
    persist_directory=settings.vector_store_path,
    embedding_model=settings.embedding_model
)


@router.get("/keywords")
async def get_keywords():
    """
    Get all unique recipe keywords/tags from the database.
    
    Returns keywords grouped by type:
    - dietary: Vegetarian, Vegan, Gluten-Free, etc.
    - health: Low-Calorie, High-Protein, Healthy, etc.
    - time: <15 Mins, <30 Mins, Weeknight, etc.
    - difficulty: Easy, Beginner
    - cuisine: Asian, Indian, Mexican, etc.
    """
    try:
        keywords = vector_store.get_unique_keywords()
        
        return {
            "keywords": keywords,
            "total_count": len(keywords)
        }
        
    except Exception as e:
        logger.error(f"Error getting keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_recipes(
    search: Optional[str] = Query(None, description="Search query"),
    source_type: Optional[str] = Query(None, description="Filter by source type (dataset, image, url, chat)"),
    keywords: Optional[List[str]] = Query(None, description="Filter by keywords/tags (dish type, cuisine, diet labels, etc.)"),
    max_calories: Optional[float] = Query(None, description="Maximum calories"),
    min_protein: Optional[float] = Query(None, description="Minimum protein"),
    max_carbs: Optional[float] = Query(None, description="Maximum carbs"),
    max_fat: Optional[float] = Query(None, description="Maximum fat"),
    servings: Optional[int] = Query(None, description="Number of servings"),
    sort: Optional[str] = Query("relevance", description="Sort by (relevance, calories, protein, recent, alphabetical)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=1000, description="Results per page")
):
    """
    Search recipes with advanced filtering.
    
    Supports filtering by:
    - Text search query (semantic search across recipe names and descriptions)
    - Source type (dataset recipes vs user-added recipes)
    - Keywords/tags (e.g., Vegetarian, Low-Calorie, Quick, salad, american, lunch/dinner)
    - Nutritional constraints (max calories, min protein, etc.)
    - Servings
    
    Returns paginated results with recipe metadata.
    """
    try:
        # Build metadata filters
        metadata_filters = {}
        if source_type:
            metadata_filters["source_type"] = source_type
        
        # Fetch recipes from vector store with generous limit for filtering
        # Note: vector_store methods already parse JSON fields and populate keywords
        # Increased limit to allow for more extensive filtering and pagination
        fetch_limit = 2000
        
        if search:
            results = vector_store.search_recipes(
                query=search,
                filter_dict=metadata_filters if metadata_filters else None,
                n_results=fetch_limit
            )
        else:
            results = vector_store.get_recipes_by_filter(
                filter_dict=metadata_filters if metadata_filters else None,
                n_results=fetch_limit
            )
        
        # Apply filters and collect matching recipes
        filtered_recipes = []
        for recipe in results:
            # Keyword filter (keywords are already parsed by vector_store)
            if keywords:
                recipe_keywords = recipe.get("keywords", [])
                if not any(kw in recipe_keywords for kw in keywords):
                    continue
            
            # Nutrition filters
            if max_calories and recipe.get("calories", 0) > max_calories:
                continue
            if min_protein and recipe.get("protein", 0) < min_protein:
                continue
            if max_carbs and recipe.get("carbs", 0) > max_carbs:
                continue
            if max_fat and recipe.get("fat", 0) > max_fat:
                continue
            if servings and recipe.get("servings") != servings:
                continue
            
            filtered_recipes.append(recipe)
        
        # Sort
        if sort == "calories":
            filtered_recipes.sort(key=lambda x: x.get("calories", 0))
        elif sort == "protein":
            filtered_recipes.sort(key=lambda x: x.get("protein", 0), reverse=True)
        elif sort == "alphabetical":
            filtered_recipes.sort(key=lambda x: x.get("name", ""))
        
        # Paginate
        start = (page - 1) * limit
        end = start + limit
        
        return {
            "recipes": filtered_recipes[start:end],
            "total": len(filtered_recipes),
            "page": page,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error searching recipes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recipe/{recipe_id}")
async def get_recipe_details(recipe_id: str, session_id: str = None, db: Session = Depends(get_db)):
    """
    Get full recipe details including ingredients and instructions.
    Supports both database recipes (SQLite), dataset recipes (ChromaDB), 
    and modified/temporary recipes from conversation history.
    
    Args:
        recipe_id: The unique recipe ID
        session_id: Optional session ID for retrieving modified recipes from conversation
        
    Returns:
        Full recipe object with all details
    """
    try:
        # Check if this is a modified/temporary recipe (ID starts with "modified_" or "session_")
        if (recipe_id.startswith("modified_") or recipe_id.startswith("session_")) and session_id:
            # Try to retrieve from conversation history
            from app.services.conversation_memory import ConversationMemory
            import json
            
            memory = ConversationMemory(db, session_id)
            history = memory.get_conversation_history(limit=20)
            
            # Search through assistant messages for this recipe
            for msg in reversed(history):
                if msg["role"] == "assistant" and "recipes" in msg:
                    for recipe in msg["recipes"]:
                        if recipe.get("id") == recipe_id:
                            return recipe
            
            # If not found in conversation, return 404
            raise HTTPException(status_code=404, detail="Modified recipe not found in conversation history")
        
        # Try SQLite database first (for URL/image/chat extracted recipes)
        try:
            recipe_id_int = int(recipe_id)
            from app.db.crud_recipes import get_recipe
            
            db_recipe = get_recipe(db, recipe_id_int)
            if db_recipe:
                # Convert to response format - SQLAlchemy model with relationships
                from app.db.schema import Recipe
                recipe_response = Recipe.model_validate(db_recipe).model_dump(mode="json")
                
                # Add nutrition data if available
                if db_recipe.nutrition:
                    recipe_response["nutrition"] = {
                        "total": {
                            "kcal": db_recipe.nutrition.kcal_total,
                            "protein": db_recipe.nutrition.protein_total,
                            "carbs": db_recipe.nutrition.carbs_total,
                            "fat": db_recipe.nutrition.fat_total
                        },
                        "per_serving": {
                            "kcal": db_recipe.nutrition.kcal_per_serving,
                            "protein": db_recipe.nutrition.protein_per_serving,
                            "carbs": db_recipe.nutrition.carbs_per_serving,
                            "fat": db_recipe.nutrition.fat_per_serving
                        }
                    }
                
                return recipe_response
        except (ValueError, TypeError):
            # Not a numeric ID, continue to ChromaDB lookup
            pass
        
        # Fall back to vector store lookup (for dataset recipes)
        recipe = vector_store.get_recipe_by_id(recipe_id)
        
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        return recipe
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching recipe details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
