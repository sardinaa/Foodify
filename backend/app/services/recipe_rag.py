"""
RAG service for recipe recommendations.
Retrieves relevant recipes from vector store and generates personalized recommendations.
"""
from typing import List, Dict, Any, Optional
import logging
from app.services.recipe_vectorstore import RecipeVectorStore
from app.core.llm_client import LLMClient
from app.core.config import get_settings
from app.utils.prompt_loader import get_prompt_loader
import json

logger = logging.getLogger(__name__)


class RecipeRAGService:
    """Service for RAG-based recipe recommendations."""
    
    def __init__(self):
        """Initialize the RAG service with vector store and LLM."""
        self.settings = get_settings()
        
        # Initialize vector store
        self.vector_store = RecipeVectorStore(
            persist_directory=self.settings.vector_store_path,
            embedding_model=self.settings.embedding_model
        )
        
        # Initialize LLM client
        self.llm_client = LLMClient()
        
        # Initialize prompt loader
        self.prompt_loader = get_prompt_loader()
        
        logger.info(f"RAG service initialized with {self.vector_store.count()} recipes")
    
    async def get_recipe_recommendations(
        self,
        user_query: str,
        dietary_restrictions: Optional[List[str]] = None,
        max_calories: Optional[float] = None,
        n_results: int = 5
    ) -> Dict[str, Any]:
        """
        Get recipe recommendations based on user preferences.
        
        Args:
            user_query: Natural language description of what user wants
            dietary_restrictions: List of dietary restrictions (e.g., ["vegetarian", "gluten-free"])
            max_calories: Maximum calories per serving
            n_results: Number of recipes to retrieve
            
        Returns:
            Dictionary with recommendations and explanations
        """
        logger.info(f"Getting recommendations for query: {user_query}")
        
        # Build filter for vector search
        filter_dict = {}
        if max_calories:
            filter_dict["calories"] = {"$lte": max_calories}
        
        # Search for similar recipes
        similar_recipes = self.vector_store.search_recipes(
            query=user_query,
            n_results=n_results * 2,  # Get more results to filter
            filter_dict=filter_dict if filter_dict else None
        )
        
        logger.info(f"Found {len(similar_recipes)} similar recipes")
        
        # Filter by dietary restrictions if specified
        if dietary_restrictions:
            filtered_recipes = []
            for recipe in similar_recipes:
                keywords = recipe.get('keywords', [])
                keywords_lower = [k.lower() for k in keywords]
                
                # Check if recipe matches restrictions
                matches = True
                for restriction in dietary_restrictions:
                    restriction_lower = restriction.lower()
                    if restriction_lower not in keywords_lower:
                        # Check if it's a negative restriction (e.g., "no meat")
                        if "vegetarian" in restriction_lower or "vegan" in restriction_lower:
                            # Check if recipe contains meat keywords
                            meat_keywords = ["chicken", "beef", "pork", "meat", "fish", "seafood"]
                            if any(mk in keywords_lower for mk in meat_keywords):
                                matches = False
                                break
                
                if matches:
                    filtered_recipes.append(recipe)
                    
                if len(filtered_recipes) >= n_results:
                    break
            
            similar_recipes = filtered_recipes[:n_results]
        else:
            similar_recipes = similar_recipes[:n_results]
        
        # Generate personalized recommendations using LLM
        recommendations = await self._generate_recommendations_with_llm(
            user_query=user_query,
            recipes=similar_recipes,
            dietary_restrictions=dietary_restrictions,
            max_calories=max_calories
        )
        
        return recommendations
    
    async def _generate_recommendations_with_llm(
        self,
        user_query: str,
        recipes: List[Dict[str, Any]],
        dietary_restrictions: Optional[List[str]],
        max_calories: Optional[float]
    ) -> Dict[str, Any]:
        """
        Use LLM to generate personalized recommendations and explanations.
        
        Args:
            user_query: User's original query
            recipes: Retrieved recipes from vector store
            dietary_restrictions: User's dietary restrictions
            max_calories: Maximum calorie constraint
            
        Returns:
            Recommendations with explanations
        """
        # Load prompt templates from JSON
        prompt_config = self.prompt_loader.get_rag_prompt("recipe_recommendations")
        recipe_item_config = self.prompt_loader.get_rag_prompt("recipe_context_item")
        constraints_config = self.prompt_loader.get_rag_prompt("constraints")
        
        # Prepare context with recipe information
        recipes_context = []
        for i, recipe in enumerate(recipes, 1):
            keywords = recipe.get('keywords', [])
            if isinstance(keywords, str):
                try:
                    keywords = json.loads(keywords)
                except:
                    keywords = []
            
            recipe_info = self.prompt_loader.format_prompt(
                recipe_item_config.get("template", ""),
                index=i,
                name=recipe['name'],
                category=recipe['category'],
                calories=f"{recipe['calories']:.0f}",
                protein=f"{recipe['protein']:.1f}",
                carbs=f"{recipe['carbs']:.1f}",
                fat=f"{recipe['fat']:.1f}",
                servings=recipe.get('servings', 'N/A'),
                tags=', '.join(keywords[:5])
            )
            recipes_context.append(recipe_info)
        
        # Build constraints text
        constraints = []
        if dietary_restrictions:
            dietary_template = constraints_config.get("dietary_restrictions_template", "")
            constraints.append(
                self.prompt_loader.format_prompt(
                    dietary_template,
                    dietary_restrictions=', '.join(dietary_restrictions)
                )
            )
        if max_calories:
            calories_template = constraints_config.get("max_calories_template", "")
            constraints.append(
                self.prompt_loader.format_prompt(
                    calories_template,
                    max_calories=max_calories
                )
            )
        
        constraints_text = "\n".join(constraints) if constraints else constraints_config.get("no_constraints", "No specific constraints")
        
        # Create prompt for LLM
        main_template = prompt_config.get("template", "")
        prompt = self.prompt_loader.format_prompt(
            main_template,
            user_query=user_query,
            constraints_text=constraints_text,
            recipes_context="\n\n".join(recipes_context)
        )

        # Get LLM response
        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            explanation = response
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            explanation = "Unable to generate personalized recommendations at this time."
        
        return {
            "query": user_query,
            "recipes": recipes,
            "explanation": explanation,
            "total_results": len(recipes)
        }
    
    def search_by_ingredients(
        self,
        ingredients: List[str],
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for recipes by ingredients.
        
        Args:
            ingredients: List of ingredient names
            n_results: Number of results to return
            
        Returns:
            List of matching recipes
        """
        # Create search query from ingredients
        query = f"recipes with {', '.join(ingredients)}"
        
        return self.vector_store.search_recipes(
            query=query,
            n_results=n_results
        )
    
    def search_by_category(
        self,
        category: str,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for recipes by category.
        
        Args:
            category: Recipe category (e.g., "Desserts", "Main Dish")
            n_results: Number of results to return
            
        Returns:
            List of matching recipes
        """
        return self.vector_store.search_recipes(
            query=category,
            n_results=n_results,
            filter_dict={"category": category}
        )
    
    def get_recipe_count(self) -> int:
        """Get the total number of recipes in the vector store."""
        return self.vector_store.count()
    
    def get_all_categories(self) -> List[str]:
        """
        Get all unique recipe categories from the vector store.
        
        Returns:
            Sorted list of unique category names
        """
        return self.vector_store.get_unique_categories()
    
    def get_all_keywords(self) -> List[str]:
        """
        Get all unique recipe keywords/tags from the vector store.
        
        Returns:
            Sorted list of unique keywords
        """
        return self.vector_store.get_unique_keywords()
    
    def search_recipes(
        self,
        query: str,
        metadata_filter: Optional[Dict[str, Any]] = None,
        n_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search recipes using semantic search with optional metadata filtering.
        
        Args:
            query: Search query text
            metadata_filter: Optional metadata filters
            n_results: Number of results to return
            
        Returns:
            List of recipe dictionaries
        """
        return self.vector_store.search_recipes(
            query=query,
            n_results=n_results,
            filter_dict=metadata_filter
        )
    
    def get_filtered_recipes(
        self,
        metadata_filter: Optional[Dict[str, Any]] = None,
        n_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recipes with metadata filtering (no semantic search).
        
        Args:
            metadata_filter: Metadata filters to apply
            n_results: Number of results to return
            
        Returns:
            List of recipe dictionaries
        """
        return self.vector_store.get_recipes_by_filter(
            filter_dict=metadata_filter,
            n_results=n_results
        )
    
    def get_recipe_by_id(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full recipe details by ID.
        
        Args:
            recipe_id: The unique recipe ID
            
        Returns:
            Full recipe dictionary with ingredients and instructions, or None if not found
        """
        return self.vector_store.get_recipe_by_id(recipe_id)
