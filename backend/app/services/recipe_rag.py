"""
RAG service for recipe recommendations.
Full RAG implementation: ChromaDB for semantic search + PostgreSQL for complete recipe context.
"""
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from app.services.recipe_vectorstore import get_vector_store
from app.core.llm_client import get_llm_client
from app.core.config import get_settings
from app.core.constants import LimitsConstants
from app.utils.prompt_loader import get_prompt_loader
from app.db.crud_recipes import get_recipe
from app.db.serializers import RecipeSerializer
import json

logger = logging.getLogger(__name__)


class RecipeRAGService:
    """Service for RAG-based recipe recommendations."""
    
    def __init__(self):
        """Initialize the RAG service with vector store and LLM."""
        self.settings = get_settings()
        
        # Initialize cached vector store
        self.vector_store = get_vector_store(
            persist_directory=self.settings.vector_store_path,
            embedding_model=self.settings.embedding_model
        )
        
        # Initialize shared LLM client
        self.llm_client = get_llm_client()
        
        # Initialize prompt loader
        self.prompt_loader = get_prompt_loader()
        
        logger.info(f"RAG service initialized with {self.vector_store.count()} recipes")
    
    def _model_to_dict(self, recipe_model) -> Dict[str, Any]:
        """Convert recipe model from PostgreSQL to dictionary using unified serializer."""
        return RecipeSerializer.model_to_dict(recipe_model)
    
    def _metadata_to_dict(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Convert ChromaDB metadata to dictionary using unified serializer."""
        return RecipeSerializer.metadata_to_dict(metadata)
    
    async def get_recipe_recommendations(
        self,
        user_query: str,
        db: Session,
        dietary_restrictions: Optional[List[str]] = None,
        max_calories: Optional[float] = None,
        n_results: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get recipe recommendations based on user preferences with full recipe context.
        
        This implements TRUE RAG:
        1. Semantic search via ChromaDB (retrieval)
        2. Fetch full recipe details from PostgreSQL (augmentation)
        3. Generate personalized recommendations via LLM (generation)
        
        Args:
            user_query: Natural language description of what user wants
            db: Database session for fetching full recipe details
            dietary_restrictions: List of dietary restrictions (e.g., ["vegetarian", "gluten-free"])
            max_calories: Maximum calories per serving
            n_results: Number of recipes to retrieve
            metadata_filter: Optional metadata filter for ChromaDB (e.g., {"time": {"$lte": 30}})
            
        Returns:
            Dictionary with full recipe details, recommendations and explanations
        """
        logger.info(f"Getting recommendations for query: {user_query}")
        
        # Build filter for vector search - merge with provided metadata_filter
        filter_dict = metadata_filter.copy() if metadata_filter else {}
        if max_calories and "calories" not in filter_dict:
            filter_dict["calories"] = {"$lte": max_calories}
        
        # Step 1: RETRIEVAL - Semantic search for similar recipes
        similar_recipes_metadata = self.vector_store.search_recipes(
            query=user_query,
            n_results=n_results * 2,  # Get more results to filter
            filter_dict=filter_dict if filter_dict else None
        )
        
        logger.info(f"Found {len(similar_recipes_metadata)} similar recipes from vector search")
        
        # Post-filter by time constraint if specified (in case ChromaDB filter didn't work)
        if metadata_filter and "time" in metadata_filter:
            max_time = metadata_filter["time"].get("$lte")
            if max_time:
                time_filtered = []
                for recipe in similar_recipes_metadata:
                    recipe_time = recipe.get('time', 0)
                    # Convert to float if it's a string
                    try:
                        recipe_time = float(recipe_time) if recipe_time else 0
                    except:
                        recipe_time = 0
                    
                    if recipe_time > 0 and recipe_time <= max_time:
                        time_filtered.append(recipe)
                similar_recipes_metadata = time_filtered
                logger.info(f"After time filter (<= {max_time} min): {len(similar_recipes_metadata)} recipes")
        
        # Filter by dietary restrictions if specified
        if dietary_restrictions:
            filtered_recipes = []
            for recipe in similar_recipes_metadata:
                keywords = recipe.get('keywords', [])
                if isinstance(keywords, str):
                    try:
                        keywords = json.loads(keywords)
                    except:
                        keywords = []
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
            
            similar_recipes_metadata = filtered_recipes[:n_results]
        else:
            similar_recipes_metadata = similar_recipes_metadata[:n_results]
        
        # Step 2: AUGMENTATION - Fetch full recipe details from PostgreSQL
        full_recipes = []
        for recipe_meta in similar_recipes_metadata:
            recipe_id = recipe_meta.get('recipe_id')
            if recipe_id:
                try:
                    # Try to fetch from PostgreSQL (user-created recipes)
                    recipe_model = get_recipe(db, int(recipe_id))
                    if recipe_model:
                        # Convert to dict with full details
                        full_recipe = self._model_to_dict(recipe_model)
                        full_recipes.append(full_recipe)
                    else:
                        # Recipe only exists in ChromaDB (from dataset)
                        # Use metadata from vector store (already has ingredients/instructions as JSON)
                        full_recipes.append(self._metadata_to_dict(recipe_meta))
                except (ValueError, TypeError):
                    # Recipe ID is not numeric (dataset recipe), use metadata
                    full_recipes.append(self._metadata_to_dict(recipe_meta))
        
        logger.info(f"Retrieved {len(full_recipes)} full recipes with complete context")
        
        # Step 3: GENERATION - Use LLM with full recipe context
        recommendations = await self._generate_recommendations_with_llm(
            user_query=user_query,
            recipes=full_recipes,
            dietary_restrictions=dietary_restrictions,
            max_calories=max_calories,
            metadata_filter=filter_dict
        )
        
        return recommendations
    
    async def _generate_recommendations_with_llm(
        self,
        user_query: str,
        recipes: List[Dict[str, Any]],
        dietary_restrictions: Optional[List[str]],
        max_calories: Optional[float],
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to generate personalized recommendations with FULL recipe context.
        
        Args:
            user_query: User's original query
            recipes: Retrieved recipes WITH full ingredients and steps
            dietary_restrictions: User's dietary restrictions
            max_calories: Maximum calorie constraint
            metadata_filter: Optional metadata filter (e.g., {"time": {"$lte": 30}})
            
        Returns:
            Recommendations with explanations
        """
        # Build rich context with full recipe details
        recipes_context = []
        for i, recipe in enumerate(recipes, 1):
            # Format ingredients (limit to preview count)
            ingredients = recipe.get('ingredients', [])
            ingredients_text = "\n".join([
                f"    - {ing.get('quantity', '')} {ing.get('unit', '')} {ing.get('name', '')}".strip()
                for ing in ingredients[:LimitsConstants.INGREDIENT_PREVIEW_COUNT]
            ]) if ingredients else "    (No ingredients listed)"
            
            # Format steps (brief overview)
            steps = recipe.get('steps', [])
            steps_text = "\n".join([
                f"    {step.get('step_number', i)}. {step.get('instruction', '')[:100]}..."
                for step in steps[:LimitsConstants.STEP_PREVIEW_COUNT]
            ]) if steps else "    (No instructions listed)"
            
            # Get keywords
            keywords = recipe.get('keywords', [])
            if isinstance(keywords, str):
                try:
                    keywords = json.loads(keywords)
                except:
                    keywords = []
            
            recipe_info = f"""Recipe {i}: {recipe['name']}
  Category: {recipe.get('category', 'Unknown')}
  Servings: {recipe.get('servings', 'N/A')} | Time: {recipe.get('total_time_minutes', 'N/A')} min
  Nutrition (per serving): {recipe.get('calories', 0):.0f} kcal, Protein: {recipe.get('protein', 0):.1f}g, Carbs: {recipe.get('carbs', 0):.1f}g, Fat: {recipe.get('fat', 0):.1f}g
  Tags: {', '.join(keywords[:5]) if keywords else 'None'}
  
  Ingredients:
{ingredients_text}
  
  Steps (preview):
{steps_text}"""
            
            recipes_context.append(recipe_info)
        
        # Build constraints text
        constraints = []
        if dietary_restrictions:
            constraints.append(f"Dietary restrictions: {', '.join(dietary_restrictions)}")
        if max_calories:
            constraints.append(f"Maximum calories per serving: {max_calories}")
        if metadata_filter and "time" in metadata_filter:
            max_time = metadata_filter["time"].get("$lte")
            if max_time:
                constraints.append(f"Maximum cooking time: {max_time} minutes")
        
        constraints_text = "\n".join(constraints) if constraints else "No specific constraints"
        
        # Create prompt for LLM with full context
        prompt = f"""I have retrieved the following recipes based on the user's request. Each recipe includes full ingredients and cooking steps.

User's request: "{user_query}"

Constraints:
{constraints_text}

Retrieved Recipes:

{chr(10).join(['-' * 80 + chr(10) + rc for rc in recipes_context])}

{'-' * 80}

Based on these recipes with their full ingredients and cooking methods, provide a helpful, conversational recommendation. Explain:
1. Why these recipes match the user's request
2. Highlight key ingredients or cooking techniques
3. Suggest which recipe(s) might be best and why
4. Any tips for customization based on the user's needs

Keep your response friendly and concise (2-3 paragraphs)."""

        # Get LLM response
        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            explanation = response
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            explanation = f"I found {len(recipes)} great recipes for you! Check out the details below."
        
        return {
            "query": user_query,
            "recipes": recipes,  # Now includes FULL ingredients and steps!
            "explanation": explanation,
            "total_results": len(recipes)
        }
    
    def get_recipe_count(self) -> int:
        """Get the total number of recipes in the vector store."""
        return self.vector_store.count()
    
    async def search_recipes_with_full_context(
        self,
        query: str,
        db: Session,
        metadata_filter: Optional[Dict[str, Any]] = None,
        n_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search recipes using semantic search and return with FULL context.
        This is the unified method that replaces search_by_ingredients, search_by_category, etc.
        
        Args:
            query: Search query text (can be ingredients, category, cooking style, etc.)
            db: Database session for fetching full recipe details
            metadata_filter: Optional metadata filters
            n_results: Number of results to return
            
        Returns:
            List of recipe dictionaries with full ingredients and steps
        """
        # Step 1: Semantic search
        recipes_metadata = self.vector_store.search_recipes(
            query=query,
            n_results=n_results,
            filter_dict=metadata_filter
        )
        
        # Step 2: Augment with full recipe details
        full_recipes = []
        for recipe_meta in recipes_metadata:
            recipe_id = recipe_meta.get('recipe_id')
            if recipe_id:
                try:
                    # Try PostgreSQL first
                    recipe_model = get_recipe(db, int(recipe_id))
                    if recipe_model:
                        full_recipes.append(self._model_to_dict(recipe_model))
                    else:
                        full_recipes.append(self._metadata_to_dict(recipe_meta))
                except (ValueError, TypeError):
                    # Dataset recipe - use metadata
                    full_recipes.append(self._metadata_to_dict(recipe_meta))
        
        return full_recipes
    
    def get_recipe_by_id(self, recipe_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        Get full recipe details by ID with complete context.
        
        Args:
            recipe_id: The unique recipe ID
            db: Database session for fetching full recipe details
            
        Returns:
            Full recipe dictionary with ingredients and instructions, or None if not found
        """
        try:
            # Try PostgreSQL first
            recipe_model = get_recipe(db, int(recipe_id))
            if recipe_model:
                return self._model_to_dict(recipe_model)
        except (ValueError, TypeError):
            pass
        
        # Fallback to vector store
        recipe_meta = self.vector_store.get_recipe_by_id(recipe_id)
        if recipe_meta:
            return self._metadata_to_dict(recipe_meta)
        
        return None
