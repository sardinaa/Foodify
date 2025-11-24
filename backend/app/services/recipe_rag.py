"""
RAG service for recipe recommendations.
Full RAG pipeline: ChromaDB for semantic search + SQLite (via SQLAlchemy) for complete recipe context.
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
from app.db.schema import Recipe
from app.utils.json_parser import parse_llm_json
import json
import random

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
        """Convert recipe model from SQL database to dictionary."""
        return Recipe.model_validate(recipe_model).model_dump(mode="json")
    
    def _metadata_to_dict(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Convert ChromaDB metadata to dictionary with full nutrition and tags."""
        import json
        # Parse JSON fields from ChromaDB metadata
        ingredients = json.loads(metadata.get('ingredients', '[]')) if isinstance(metadata.get('ingredients'), str) else metadata.get('ingredients', [])
        instructions = json.loads(metadata.get('instructions', '[]')) if isinstance(metadata.get('instructions'), str) else metadata.get('instructions', [])
        keywords = json.loads(metadata.get('keywords', '[]')) if isinstance(metadata.get('keywords'), str) else metadata.get('keywords', [])
        
        # Parse other label fields
        diet_labels = json.loads(metadata.get('diet_labels', '[]')) if isinstance(metadata.get('diet_labels'), str) else metadata.get('diet_labels', [])
        health_labels = json.loads(metadata.get('health_labels', '[]')) if isinstance(metadata.get('health_labels'), str) else metadata.get('health_labels', [])
        dish_type = json.loads(metadata.get('dish_type', '[]')) if isinstance(metadata.get('dish_type'), str) else metadata.get('dish_type', [])
        cuisine_type = json.loads(metadata.get('cuisine_type', '[]')) if isinstance(metadata.get('cuisine_type'), str) else metadata.get('cuisine_type', [])
        meal_type = json.loads(metadata.get('meal_type', '[]')) if isinstance(metadata.get('meal_type'), str) else metadata.get('meal_type', [])
        
        # Combine all tags if keywords is empty
        if not keywords:
            keywords = []
            keywords.extend(diet_labels)
            keywords.extend(health_labels)
            keywords.extend(dish_type)
            keywords.extend(cuisine_type)
            keywords.extend(meal_type)
        
        return {
            "id": metadata.get('recipe_id', 0),
            "name": metadata.get('name', 'Unknown'),
            "description": metadata.get('description', ''),
            "category": metadata.get('category', '') or (dish_type[0] if dish_type else ''),
            "servings": int(metadata.get('servings', 4)),
            "ingredients": [{"name": i, "quantity": None, "unit": None} if isinstance(i, str) else i for i in ingredients],
            "steps": [{"step_number": idx+1, "instruction": s} if isinstance(s, str) else s for idx, s in enumerate(instructions)],
            "tags": keywords,
            "keywords": keywords,
            "calories": float(metadata.get('calories', 0)),
            "protein": float(metadata.get('protein', 0)),
            "carbs": float(metadata.get('carbs', 0)),
            "fat": float(metadata.get('fat', 0)),
            "fiber": float(metadata.get('fiber', 0)),
            "sugar": float(metadata.get('sugar', 0)),
            "saturated_fat": float(metadata.get('saturated_fat', 0)),
            "cholesterol": float(metadata.get('cholesterol', 0)),
            "sodium": float(metadata.get('sodium', 0)),
            "source_type": metadata.get('source_type', 'dataset'),
            "created_at": None
        }
    
    async def transform_query(self, user_query: str) -> str:
        """
        Transform conversational query into optimized search keywords.
        """
        try:
            config = self.prompt_loader.get_llm_prompt("query_transformation")
            system_prompt = "\n".join(config.get("system", []))
            user_template = "\n".join(config.get("user_template", []))
            
            prompt = self.prompt_loader.format_prompt(
                user_template,
                user_query=user_query
            )
            
            optimized_query = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                system=system_prompt
            )
            
            logger.info(f"Query transformation: '{user_query}' -> '{optimized_query}'")
            return optimized_query.strip()
        except Exception as e:
            logger.error(f"Query transformation failed: {e}")
            return user_query

    async def extract_constraints(self, user_query: str) -> Dict[str, Any]:
        """
        Extract constraints from user query using LLM.
        """
        try:
            config = self.prompt_loader.get_llm_prompt("recipe_constraint_parser")
            system_prompt = "\n".join(config.get("system", []))
            user_template = "\n".join(config.get("user_template", []))
            
            prompt = self.prompt_loader.format_prompt(
                user_template,
                user_query=user_query
            )
            
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                system=system_prompt
            )
            
            return parse_llm_json(response, fallback={
                "dietary": [],
                "max_calories": None,
                "quantity": None,
                "min_protein": None,
                "max_carbs": None,
                "max_fat": None,
                "included_ingredients": [],
                "excluded_ingredients": []
            })
        except Exception as e:
            logger.error(f"Constraint extraction failed: {e}")
            return {}

    async def rerank_results(self, user_query: str, recipes: List[Dict]) -> List[Dict]:
        """
        Re-rank recipes based on relevance to user query using LLM.
        """
        if not recipes:
            return []
            
        try:
            # Prepare simplified recipe list for LLM to save tokens
            candidates = []
            for r in recipes:
                candidates.append({
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "description": r.get("description", "")[:100],
                    "ingredients": [i["name"] for i in r.get("ingredients", [])[:5]]
                })
            
            config = self.prompt_loader.get_llm_prompt("recipe_reranking")
            system_prompt = "\n".join(config.get("system", []))
            user_template = "\n".join(config.get("user_template", []))
            
            prompt = self.prompt_loader.format_prompt(
                user_template,
                recipes_json=json.dumps(candidates),
                user_query=user_query
            )
            
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                system=system_prompt
            )
            
            rankings = parse_llm_json(response)
            if not isinstance(rankings, list):
                return recipes

            # Create a map of scores
            scores = {str(r.get("id")): r.get("score", 0) for r in rankings}
            
            # Sort original recipes by score
            recipes.sort(key=lambda x: scores.get(str(x.get("id")), 0), reverse=True)
            
            logger.info(f"Re-ranked {len(recipes)} recipes")
            return recipes
            
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            return recipes

    async def get_recipe_recommendations(
        self,
        user_query: str,
        db: Session,
        dietary_restrictions: Optional[List[str]] = None,
        max_calories: Optional[float] = None,
        n_results: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
        system_instruction: Optional[str] = None,
        min_protein: Optional[float] = None,
        max_carbs: Optional[float] = None,
        max_fat: Optional[float] = None,
        included_ingredients: Optional[List[str]] = None,
        excluded_ingredients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get recipe recommendations based on user preferences with full recipe context.
        
        This implements TRUE RAG:
        1. Query Transformation (LLM)
        2. Semantic search via ChromaDB (retrieval)
        3. Re-ranking (LLM)
        4. Fetch full recipe details from the SQL database (augmentation)
        5. Generate personalized recommendations via LLM (generation)
        """
        logger.info(f"Getting recommendations for query: {user_query}")
        
        # Step 0: Query Transformation
        search_query = await self.transform_query(user_query)
        
        # Build filter for vector search - merge with provided metadata_filter
        filter_dict = metadata_filter.copy() if metadata_filter else {}
        if max_calories and "calories" not in filter_dict:
            filter_dict["calories"] = {"$lte": max_calories}
        
        # Step 1: RETRIEVAL - Semantic search for similar recipes
        # Fetch more candidates for re-ranking (5x requested to allow for filtering)
        candidate_count = n_results * 5
        similar_recipes_metadata = self.vector_store.search_recipes(
            query=search_query,
            n_results=candidate_count,
            filter_dict=filter_dict if filter_dict else None
        )
        
        logger.info(f"Found {len(similar_recipes_metadata)} similar recipes from vector search")
        
        # Post-filter by time constraint if specified
        if metadata_filter and "time" in metadata_filter:
            max_time = metadata_filter["time"].get("$lte")
            if max_time:
                time_filtered = []
                for recipe in similar_recipes_metadata:
                    recipe_time = recipe.get('time', 0)
                    try:
                        recipe_time = float(recipe_time) if recipe_time else 0
                    except:
                        recipe_time = 0
                    
                    if recipe_time > 0 and recipe_time <= max_time:
                        time_filtered.append(recipe)
                similar_recipes_metadata = time_filtered

        # Post-filter by nutritional constraints
        if min_protein or max_carbs or max_fat:
            nutri_filtered = []
            for recipe in similar_recipes_metadata:
                matches = True
                if min_protein and recipe.get('protein', 0) < min_protein:
                    matches = False
                if max_carbs and recipe.get('carbs', 0) > max_carbs:
                    matches = False
                if max_fat and recipe.get('fat', 0) > max_fat:
                    matches = False
                
                if matches:
                    nutri_filtered.append(recipe)
            similar_recipes_metadata = nutri_filtered
            logger.info(f"After nutritional filtering: {len(similar_recipes_metadata)} recipes")

        # Post-filter by ingredient exclusions AND empty ingredients
        # We always filter out recipes with no ingredients as they are low quality
        excl_filtered = []
        for recipe in similar_recipes_metadata:
            ingredients = recipe.get('ingredients', [])
            instructions = recipe.get('instructions', [])
            
            # Normalize ingredients to string list if needed
            if isinstance(ingredients, str):
                try:
                    ingredients = json.loads(ingredients)
                except:
                    ingredients = []
            
            # Normalize instructions if needed
            if isinstance(instructions, str):
                try:
                    instructions = json.loads(instructions)
                except:
                    instructions = []
            
            # Filter out recipes with no ingredients (instructions are optional for this dataset)
            if not ingredients:
                continue

            # Check for exclusions
            has_excluded = False
            if excluded_ingredients:
                ing_text = " ".join([str(i).lower() for i in ingredients])
                for excluded in excluded_ingredients:
                    if excluded.lower() in ing_text:
                        has_excluded = True
                        break
            
            if not has_excluded:
                excl_filtered.append(recipe)
        
        similar_recipes_metadata = excl_filtered
        logger.info(f"After exclusion and quality filtering: {len(similar_recipes_metadata)} recipes")
        
        # Filter by dietary restrictions
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
                
                matches = True
                for restriction in dietary_restrictions:
                    restriction_lower = restriction.lower()
                    if restriction_lower not in keywords_lower:
                        if "vegetarian" in restriction_lower or "vegan" in restriction_lower:
                            meat_keywords = ["chicken", "beef", "pork", "meat", "fish", "seafood"]
                            if any(mk in keywords_lower for mk in meat_keywords):
                                matches = False
                                break
                
                if matches:
                    filtered_recipes.append(recipe)
            
            similar_recipes_metadata = filtered_recipes
        
        # Step 2: AUGMENTATION - Fetch full recipe details from the SQL database
        # We need full details for re-ranking
        full_recipes = []
        for recipe_meta in similar_recipes_metadata:
            recipe_id = recipe_meta.get('recipe_id')
            if recipe_id:
                try:
                    # Try to fetch from the SQL database (user-created recipes)
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
        
        # Step 3: RE-RANKING - Score recipes by relevance
        ranked_recipes = await self.rerank_results(user_query, full_recipes)
        
        # Take top N results after re-ranking with some randomness for variety
        if len(ranked_recipes) > n_results:
            # Select from a larger pool (top 2x requested) to ensure variety
            pool_size = min(len(ranked_recipes), n_results * 2)
            top_pool = ranked_recipes[:pool_size]
            
            # Randomly sample from the top pool
            final_recipes = random.sample(top_pool, n_results)
            
            # Sort back by original ranking (relevance)
            final_recipes.sort(key=lambda x: ranked_recipes.index(x))
        else:
            final_recipes = ranked_recipes
        
        # Step 4: GENERATION - Use LLM with full recipe context
        recommendations = await self._generate_recommendations_with_llm(
            user_query=user_query,
            recipes=final_recipes,
            dietary_restrictions=dietary_restrictions,
            max_calories=max_calories,
            metadata_filter=filter_dict,
            system_instruction=system_instruction,
            min_protein=min_protein,
            max_carbs=max_carbs,
            max_fat=max_fat,
            included_ingredients=included_ingredients,
            excluded_ingredients=excluded_ingredients
        )
        
        return recommendations
    
    async def _generate_recommendations_with_llm(
        self,
        user_query: str,
        recipes: List[Dict[str, Any]],
        dietary_restrictions: Optional[List[str]],
        max_calories: Optional[float],
        metadata_filter: Optional[Dict[str, Any]] = None,
        system_instruction: Optional[str] = None,
        min_protein: Optional[float] = None,
        max_carbs: Optional[float] = None,
        max_fat: Optional[float] = None,
        included_ingredients: Optional[List[str]] = None,
        excluded_ingredients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to generate personalized recommendations with FULL recipe context.
        
        Args:
            user_query: User's original query
            recipes: Retrieved recipes WITH full ingredients and steps
            dietary_restrictions: User's dietary restrictions
            max_calories: Maximum calorie constraint
            metadata_filter: Optional metadata filter (e.g., {"time": {"$lte": 30}})
            system_instruction: Optional instruction for the LLM (e.g. about result limits)
            min_protein: Minimum protein constraint
            max_carbs: Maximum carbs constraint
            max_fat: Maximum fat constraint
            included_ingredients: Ingredients to include
            excluded_ingredients: Ingredients to exclude
            
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
  Servings: {recipe.get('servings', 'N/A')}
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
        if min_protein:
            constraints.append(f"Minimum protein: {min_protein}g")
        if max_carbs:
            constraints.append(f"Maximum carbs: {max_carbs}g")
        if max_fat:
            constraints.append(f"Maximum fat: {max_fat}g")
        if included_ingredients:
            constraints.append(f"Must include: {', '.join(included_ingredients)}")
        if excluded_ingredients:
            constraints.append(f"Must exclude: {', '.join(excluded_ingredients)}")
        if metadata_filter and "time" in metadata_filter:
            max_time = metadata_filter["time"].get("$lte")
            if max_time:
                constraints.append(f"Maximum cooking time: {max_time} minutes")
        
        constraints_text = "\n".join(constraints) if constraints else "No specific constraints"
        
        # Create prompt for LLM with full context
        prompt = f"""I have retrieved the following recipes based on the user's request. Each recipe includes full ingredients and cooking steps.

User's request: "{user_query}"
{f"System Note: {system_instruction}" if system_instruction else ""}

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
                    # Try the SQL database first
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
            # Try the SQL database first
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
