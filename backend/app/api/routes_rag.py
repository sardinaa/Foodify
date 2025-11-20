"""
API routes for RAG-based recipe recommendations.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
from sqlalchemy.orm import Session

from app.services.recipe_rag import RecipeRAGService
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["RAG Recipe Recommendations"])

# Initialize RAG service
rag_service = RecipeRAGService()


class RecipeRecommendationRequest(BaseModel):
    """Request model for recipe recommendations."""
    query: str = Field(..., description="User's recipe search query")
    dietary_restrictions: Optional[List[str]] = Field(
        None,
        description="List of dietary restrictions (e.g., vegetarian, vegan, gluten-free)"
    )
    max_calories: Optional[float] = Field(
        None,
        description="Maximum calories per serving"
    )
    n_results: int = Field(
        5,
        description="Number of recipe recommendations to return",
        ge=1,
        le=20
    )


class RecipeRecommendationResponse(BaseModel):
    """Response model for recipe recommendations."""
    query: str
    recipes: List[Dict[str, Any]]
    explanation: str
    total_results: int


class IngredientSearchRequest(BaseModel):
    """Request model for ingredient-based search."""
    ingredients: List[str] = Field(..., description="List of ingredients to search for")
    n_results: int = Field(10, ge=1, le=50)


@router.post("/recommend", response_model=RecipeRecommendationResponse)
async def get_recipe_recommendations(
    request: RecipeRecommendationRequest,
    db: Session = Depends(get_db)
):
    """
    Get personalized recipe recommendations based on user preferences.
    
    Uses FULL RAG (Retrieval Augmented Generation):
    - Semantic search via ChromaDB
    - Full recipe retrieval from PostgreSQL
    - LLM-generated personalized recommendations
    
    Returns complete recipes with ingredients and steps.
    """
    try:
        recommendations = await rag_service.get_recipe_recommendations(
            user_query=request.query,
            db=db,
            dietary_restrictions=request.dietary_restrictions,
            max_calories=request.max_calories,
            n_results=request.n_results
        )
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-by-ingredients")
async def search_by_ingredients(
    request: IngredientSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search for recipes by ingredients with FULL context.
    
    Returns complete recipes (with ingredients & steps) that contain or work well 
    with the specified ingredients. Uses unified RAG search.
    """
    try:
        # Create natural language query from ingredients
        query = f"recipes with {', '.join(request.ingredients)}"
        
        recipes = await rag_service.search_recipes_with_full_context(
            query=query,
            db=db,
            n_results=request.n_results
        )
        
        return {
            "ingredients": request.ingredients,
            "recipes": recipes,
            "total_results": len(recipes)
        }
        
    except Exception as e:
        logger.error(f"Error searching by ingredients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-by-category")
async def search_by_category(
    category: str = Query(..., description="Recipe category to search for"),
    n_results: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Search for recipes by category with FULL context.
    
    Categories include: Desserts, Main Dish, Breakfast, Lunch/Snacks, etc.
    Returns complete recipes with ingredients and steps.
    """
    try:
        recipes = await rag_service.search_recipes_with_full_context(
            query=category,
            db=db,
            n_results=n_results,
            metadata_filter={"category": category}
        )
        
        return {
            "category": category,
            "recipes": recipes,
            "total_results": len(recipes)
        }
        
    except Exception as e:
        logger.error(f"Error searching by category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    Get statistics about the recipe database.
    """
    try:
        return {
            "total_recipes": rag_service.get_recipe_count(),
            "vector_store_initialized": rag_service.get_recipe_count() > 0
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_categories():
    """
    Get all unique recipe categories from the database.
    
    Returns a list of all recipe categories available in the dataset
    (e.g., Dessert, Chicken, Breakfast, Asian, etc.)
    """
    try:
        categories = rag_service.vector_store.get_unique_categories()
        
        return {
            "categories": categories,
            "total_count": len(categories)
        }
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        keywords = rag_service.vector_store.get_unique_keywords()
        
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
    categories: Optional[List[str]] = Query(None, description="Filter by categories"),
    keywords: Optional[List[str]] = Query(None, description="Filter by keywords"),
    max_calories: Optional[float] = Query(None, description="Maximum calories"),
    min_protein: Optional[float] = Query(None, description="Minimum protein"),
    max_carbs: Optional[float] = Query(None, description="Maximum carbs"),
    max_fat: Optional[float] = Query(None, description="Maximum fat"),
    servings: Optional[int] = Query(None, description="Number of servings"),
    sort: Optional[str] = Query("relevance", description="Sort by (relevance, calories, protein, recent, alphabetical)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page")
):
    """
    Search recipes with advanced filtering.
    
    Supports filtering by:
    - Text search query (semantic search across recipe names and descriptions)
    - Source type (dataset recipes vs user-added recipes)
    - Categories (e.g., Dessert, Chicken, Breakfast)
    - Keywords (e.g., Vegetarian, Low-Calorie, Quick)
    - Nutritional constraints (max calories, min protein, etc.)
    - Servings
    
    Returns paginated results with recipe metadata.
    """
    try:
        # Build metadata filters
        metadata_filters = {}
        
        if source_type:
            metadata_filters["source_type"] = source_type
            
        if categories:
            metadata_filters["category"] = {"$in": categories}
            
        # Determine how many results to fetch based on filters
        # Always fetch enough for multiple pages, more if we have post-filters
        has_post_filters = bool(keywords or max_calories or min_protein or max_carbs or max_fat or servings)
        fetch_multiplier = 5 if has_post_filters else 4  # 4 pages normally, 5 with filters
        fetch_limit = min(limit * fetch_multiplier, 2000)  # Cap at 500 to avoid overload
        
        # Search with RAG service using vector store directly
        if search:
            # Use semantic search with query
            results = rag_service.vector_store.search_recipes(
                query=search,
                filter_dict=metadata_filters if metadata_filters else None,
                n_results=fetch_limit
            )
        else:
            # Get all recipes matching filters
            results = rag_service.vector_store.get_recipes_by_filter(
                filter_dict=metadata_filters if metadata_filters else None,
                n_results=fetch_limit
            )
        
        # Apply additional filters (keywords, nutrition)
        filtered_recipes = []
        for recipe in results:
            # Keyword filtering
            if keywords:
                recipe_keywords = recipe.get("keywords", [])
                if isinstance(recipe_keywords, str):
                    import json
                    try:
                        recipe_keywords = json.loads(recipe_keywords)
                    except:
                        recipe_keywords = []
                        
                if not any(kw in recipe_keywords for kw in keywords):
                    continue
            
            # Nutrition filtering
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
        
        # Sort results
        if sort == "calories":
            filtered_recipes.sort(key=lambda x: x.get("calories", 0))
        elif sort == "protein":
            filtered_recipes.sort(key=lambda x: x.get("protein", 0), reverse=True)
        elif sort == "alphabetical":
            filtered_recipes.sort(key=lambda x: x.get("name", ""))
        # relevance and recent are already sorted by the RAG service
        
        # Paginate
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_recipes = filtered_recipes[start_idx:end_idx]
        
        return {
            "recipes": paginated_recipes,
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
                # Convert to response format matching ChromaDB structure
                # Use RecipeSerializer for consistency
                from app.db.serializers import RecipeSerializer
                recipe_response = RecipeSerializer.model_to_dict(db_recipe)
                
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
        
        # Fall back to full RAG lookup (for dataset recipes)
        recipe = rag_service.get_recipe_by_id(recipe_id, db)
        
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        return recipe
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching recipe details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
