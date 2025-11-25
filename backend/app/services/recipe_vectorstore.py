"""
Vector store service for recipe embeddings and semantic search.
Uses LangChain with ChromaDB for vector storage and HuggingFace for embeddings.
"""
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from typing import List, Dict, Any, Optional
import logging
import json
from functools import lru_cache

logger = logging.getLogger(__name__)


class RecipeVectorStore:
    """Manages recipe embeddings and vector-based similarity search using LangChain."""
    
    def __init__(self, persist_directory: str, embedding_model: str):
        """
        Initialize the vector store.
        
        Args:
            persist_directory: Path to ChromaDB persistence directory
            embedding_model: Name of the sentence-transformers model
        """
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model
        
        # Initialize Embedding Model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_function = HuggingFaceEmbeddings(model_name=embedding_model)
        
        # Initialize ChromaDB via LangChain
        self.vectorstore = Chroma(
            collection_name="recipes",
            embedding_function=self.embedding_function,
            persist_directory=persist_directory,
            collection_metadata={"description": "Recipe embeddings for semantic search"}
        )
        
        # Access underlying client for direct operations if needed
        self.client = self.vectorstore._client
        self.collection = self.vectorstore._collection
        
        logger.info(f"Vector store initialized with {self.collection.count()} recipes")
    
    def _parse_r_array(self, value: Any) -> List[str]:
        """Parse R-style c() array strings to Python lists."""
        if not value or value is None:
            return []
        
        if isinstance(value, list):
            return value
        
        # Remove c(" and ") wrapper and split
        value_str = str(value)
        if value_str.startswith('c('):
            value_str = value_str[2:-1]  # Remove c( and )
            # Split by comma, strip quotes and whitespace
            items = [item.strip().strip('"').strip("'") for item in value_str.split('",')]
            return [item for item in items if item]
        
        return [value_str] if value_str else []
    
    def _create_recipe_text(self, recipe: Dict[str, Any]) -> str:
        """
        Create searchable text representation of a recipe.
        Combines name, description, category, keywords, ingredients, and instructions.
        """
        text_parts = []
        
        # Recipe name and description
        if recipe.get("name"):
            text_parts.append(f"Recipe: {recipe['name']}")
        elif recipe.get("Name"):
             text_parts.append(f"Recipe: {recipe['Name']}")
        
        if recipe.get("description"):
            text_parts.append(f"Description: {recipe['description']}")
        elif recipe.get("Description"):
            text_parts.append(f"Description: {recipe['Description']}")
        
        # Category / Dish Type
        if recipe.get("dish_type"):
             text_parts.append(f"Dish Type: {recipe['dish_type']}")
        if recipe.get("cuisine_type"):
             text_parts.append(f"Cuisine: {recipe['cuisine_type']}")
        if recipe.get("meal_type"):
             text_parts.append(f"Meal Type: {recipe['meal_type']}")
        
        # Tags (Diet/Health labels or Keywords)
        tags = []
        if recipe.get("diet_labels"):
            tags.extend(recipe["diet_labels"])
        if recipe.get("health_labels"):
            tags.extend(recipe["health_labels"])
        
        keywords = self._parse_r_array(recipe.get("Keywords"))
        if keywords:
            tags.extend(keywords)
            
        if tags:
            text_parts.append(f"Tags: {', '.join(tags)}")

        # Ingredients
        ingredients = recipe.get("ingredients", [])
        if not ingredients:
            ingredients = self._parse_r_array(recipe.get("RecipeIngredientParts"))
            
        if ingredients:
            text_parts.append(f"Ingredients: {', '.join(ingredients)}")
        
        # Instructions
        instructions = recipe.get("instructions", [])
        if not instructions:
            instructions = self._parse_r_array(recipe.get("RecipeInstructions"))
            
        if instructions:
            # Join instructions with periods
            inst_text = ". ".join(instructions[:10])  # Limit to first 10 steps
            text_parts.append(f"Instructions: {inst_text}")
            
        return "\n".join(text_parts)
    
    def _create_recipe_metadata(self, recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for a recipe."""
        # Parse keywords
        keywords = self._parse_r_array(recipe.get("Keywords"))
        
        # Parse ingredients
        ingredients = recipe.get("ingredients", [])
        if not ingredients:
            ingredients = self._parse_r_array(recipe.get("RecipeIngredientParts"))
        
        # Parse instructions
        instructions = recipe.get("instructions", [])
        if not instructions:
            instructions = self._parse_r_array(recipe.get("RecipeInstructions"))
        
        # Calculate servings for normalization
        servings = float(recipe.get("servings", 0) or recipe.get("RecipeServings", 1))
        if servings <= 0:
            servings = 1
            
        # Helper to get nutrient value (prefer pre-calculated lowercase, else raw divided by servings)
        def get_nutrient(key_lower, key_raw):
            if key_lower in recipe:
                return float(recipe[key_lower])
            return float(recipe.get(key_raw, 0)) / servings

        return {
            "recipe_id": str(recipe.get("id", "") or recipe.get("RecipeId", "")),
            "name": recipe.get("name", "") or recipe.get("Name", ""),
            "cuisine_type": recipe.get("cuisine_type", ""),
            "meal_type": recipe.get("meal_type", ""),
            "dish_type": recipe.get("dish_type", ""),
            "diet_labels": json.dumps(recipe.get("diet_labels", [])),
            "health_labels": json.dumps(recipe.get("health_labels", [])),
            "keywords": json.dumps(keywords),  # Store as JSON string
            "ingredients": json.dumps(ingredients),  # Store as JSON string
            "instructions": json.dumps(instructions),  # Store as JSON string
            "servings": servings,
            "calories": get_nutrient("calories", "Calories"),
            "protein": get_nutrient("protein", "ProteinContent"),
            "carbs": get_nutrient("carbs", "CarbohydrateContent"),
            "fat": get_nutrient("fat", "FatContent"),
            "fiber": get_nutrient("fiber", "FiberContent"),
            "sugar": get_nutrient("sugar", "SugarContent"),
            "saturated_fat": get_nutrient("saturated_fat", "SaturatedFatContent"),
            "cholesterol": get_nutrient("cholesterol", "CholesterolContent"),
            "sodium": get_nutrient("sodium", "SodiumContent"),
            "source": "dataset",  # Default source for dataset recipes
            "source_type": "dataset",  # For filtering
        }

    def add_recipes(self, recipes: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """
        Add recipes to the vector store.
        
        Args:
            recipes: List of recipe dictionaries
            batch_size: Number of recipes to process in each batch
            
        Returns:
            Number of recipes added
        """
        added = 0
        
        for i in range(0, len(recipes), batch_size):
            batch = recipes[i:i + batch_size]
            
            # Prepare data for this batch
            documents = []
            metadatas = []
            ids = []
            
            for idx, recipe in enumerate(batch):
                try:
                    # Use RecipeId if available, otherwise create unique ID from batch position
                    recipe_id_raw = recipe.get("id") or recipe.get("RecipeId")
                    if recipe_id_raw is not None and str(recipe_id_raw) != "":
                        recipe_id = str(recipe_id_raw)
                    else:
                        # Generate unique ID based on global position
                        recipe_id = f"recipe_{i + idx}"
                    
                    # Create searchable text
                    doc_text = self._create_recipe_text(recipe)
                    
                    # Create metadata
                    metadata = self._create_recipe_metadata(recipe)
                    metadata["recipe_id"] = recipe_id  # Ensure ID is in metadata
                    
                    documents.append(doc_text)
                    metadatas.append(metadata)
                    ids.append(recipe_id)
                    
                except Exception as e:
                    logger.warning(f"Failed to process recipe {recipe.get('RecipeId')}: {e}")
                    continue
            
            # Add batch to collection
            if documents:
                try:
                    # Add to ChromaDB via LangChain
                    self.vectorstore.add_texts(
                        texts=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    
                    added += len(documents)
                    # Calculate current batch number correctly based on total processed so far
                    current_batch_num = (i // batch_size) + 1
                    logger.info(f"Added batch {current_batch_num}, total: {added} recipes")
                    
                except Exception as e:
                    logger.error(f"Failed to add batch: {e}")
        
        return added
    
    def search_recipes(
        self,
        query: str,
        n_results: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for recipes using semantic similarity.
        
        Args:
            query: Natural language search query
            n_results: Number of results to return
            filter_dict: Optional metadata filters (e.g., {"category": "Desserts"})
            
        Returns:
            List of recipe metadata with similarity scores
        """
        try:
            # Search ChromaDB via LangChain
            # similarity_search_with_score returns List[Tuple[Document, float]]
            results = self.vectorstore.similarity_search_with_score(
                query=query,
                k=n_results,
                filter=filter_dict
            )
            
            # Format results
            recipes = []
            for doc, score in results:
                recipe = {
                    "id": doc.metadata.get("recipe_id"),
                    "distance": score,
                    **doc.metadata
                }
                # Parse JSON fields back to lists
                json_fields = ['keywords', 'ingredients', 'instructions', 'diet_labels', 'health_labels', 'dish_type', 'cuisine_type', 'meal_type']
                for field in json_fields:
                    if field in recipe:
                        try:
                            recipe[field] = json.loads(recipe[field]) if isinstance(recipe[field], str) else recipe[field]
                        except:
                            recipe[field] = []
                
                # Combine all tags/labels into keywords for frontend compatibility
                if not recipe.get('keywords'):
                    all_tags = []
                    all_tags.extend(recipe.get('diet_labels', []))
                    all_tags.extend(recipe.get('health_labels', []))
                    all_tags.extend(recipe.get('dish_type', []))
                    all_tags.extend(recipe.get('cuisine_type', []))
                    all_tags.extend(recipe.get('meal_type', []))
                    recipe['keywords'] = all_tags
                
                recipes.append(recipe)
            
            return recipes
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def count(self) -> int:
        """Get the number of recipes in the vector store."""
        return self.collection.count()
    
    def clear(self):
        """Clear all recipes from the vector store."""
        # Delete and recreate collection
        self.vectorstore.delete_collection()
        # Re-initialize
        self.vectorstore = Chroma(
            collection_name="recipes",
            embedding_function=self.embedding_function,
            persist_directory=self.persist_directory,
            collection_metadata={"description": "Recipe embeddings for semantic search"}
        )
        self.client = self.vectorstore._client
        self.collection = self.vectorstore._collection
        logger.info("Vector store cleared")
    
    def get_unique_keywords(self) -> List[str]:
        """
        Get all unique recipe keywords/tags from the vector store.
        
        Returns:
            Sorted list of unique keywords
        """
        try:
            # Query all recipes to get their keywords
            results = self.collection.get(
                include=['metadatas']
            )
            
            # Extract unique keywords
            keywords = set()
            for metadata in results['metadatas']:
                keyword_str = metadata.get('keywords', '[]')
                try:
                    keyword_list = json.loads(keyword_str)
                    for keyword in keyword_list:
                        if keyword and keyword.strip():
                            keywords.add(keyword.strip())
                except:
                    pass
            
            # Return sorted list
            return sorted(list(keywords))
            
        except Exception as e:
            logger.error(f"Failed to get keywords: {e}")
            return []
    
    def get_recipes_by_filter(
        self,
        filter_dict: Optional[Dict[str, Any]] = None,
        n_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recipes by metadata filter without semantic search.
        
        Args:
            filter_dict: ChromaDB metadata filter
            n_results: Maximum number of results
            
        Returns:
            List of recipe dictionaries
        """
        try:
            # Query collection with filters
            results = self.collection.get(
                where=filter_dict,
                limit=n_results,
                include=['metadatas', 'documents']
            )
            
            # Format results
            recipes = []
            for i in range(len(results['ids'])):
                recipe = {
                    "id": results['ids'][i],
                    **results['metadatas'][i]
                }
                # Parse JSON fields back to lists
                json_fields = ['keywords', 'ingredients', 'instructions', 'diet_labels', 'health_labels', 'dish_type', 'cuisine_type', 'meal_type']
                for field in json_fields:
                    if field in recipe:
                        try:
                            recipe[field] = json.loads(recipe[field]) if isinstance(recipe[field], str) else recipe[field]
                        except:
                            recipe[field] = []
                
                # Combine all tags/labels into keywords for frontend compatibility
                if not recipe.get('keywords'):
                    all_tags = []
                    all_tags.extend(recipe.get('diet_labels', []))
                    all_tags.extend(recipe.get('health_labels', []))
                    all_tags.extend(recipe.get('dish_type', []))
                    all_tags.extend(recipe.get('cuisine_type', []))
                    all_tags.extend(recipe.get('meal_type', []))
                    recipe['keywords'] = all_tags
                
                recipes.append(recipe)
            
            return recipes
            
        except Exception as e:
            logger.error(f"Failed to get filtered recipes: {e}")
            return []
    
    def get_recipe_by_id(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full recipe details by ID including ingredients and instructions.
        
        Args:
            recipe_id: The unique recipe ID
            
        Returns:
            Full recipe dictionary or None if not found
        """
        try:
            # Try with the original ID first
            results = self.collection.get(
                ids=[recipe_id],
                include=['metadatas', 'documents']
            )
            
            # If not found, try with .0 suffix (ChromaDB stores numeric IDs as floats)
            if not results['ids'] or len(results['ids']) == 0:
                try:
                    float_id = f"{float(recipe_id)}"
                    results = self.collection.get(
                        ids=[float_id],
                        include=['metadatas', 'documents']
                    )
                except (ValueError, TypeError):
                    pass
            
            if not results['ids'] or len(results['ids']) == 0:
                return None
            
            metadata = results['metadatas'][0]
            document = results['documents'][0]
            
            # Parse ingredients from metadata (if available)
            ingredients = []
            if 'ingredients' in metadata:
                try:
                    ingredient_list = json.loads(metadata['ingredients'])
                    ingredients = [{"name": ing, "quantity": "", "unit": ""} for ing in ingredient_list]
                except:
                    pass
            
            # If not in metadata, try to parse from document
            if not ingredients and "Ingredients:" in document:
                try:
                    # Extract ingredients section
                    ing_section = document.split("Ingredients:")[1]
                    if "Instructions:" in ing_section:
                        ing_section = ing_section.split("Instructions:")[0]
                    
                    # Split by comma and clean up
                    ing_parts = [part.strip() for part in ing_section.split(',') if part.strip()]
                    ingredients = [{"name": ing, "quantity": "", "unit": ""} for ing in ing_parts]
                except Exception as e:
                    logger.warning(f"Could not parse ingredients from document: {e}")
            
            # Parse instructions from metadata (if available)
            steps = []
            if 'instructions' in metadata:
                try:
                    instruction_list = json.loads(metadata['instructions'])
                    steps = [{"number": i+1, "instruction": inst} for i, inst in enumerate(instruction_list)]
                except:
                    pass
            
            # If not in metadata, try to parse from document
            if not steps and "Instructions:" in document:
                try:
                    # Extract instructions section
                    inst_section = document.split("Instructions:")[1]
                    
                    # Split by period and clean up
                    inst_parts = [part.strip() for part in inst_section.split('.') if part.strip() and len(part.strip()) > 10]
                    steps = [{"number": i+1, "instruction": inst} for i, inst in enumerate(inst_parts)]
                except Exception as e:
                    logger.warning(f"Could not parse instructions from document: {e}")
            
            # Build full recipe object
            recipe = {
                "id": recipe_id,
                **metadata,
                "ingredients": ingredients if ingredients else [{"name": "Recipe details not available", "quantity": "", "unit": ""}],
                "steps": steps if steps else [{"number": 1, "instruction": "Recipe instructions not available. Please visit the original source."}],
            }
            
            # Parse all JSON fields back to lists
            json_fields = ['keywords', 'diet_labels', 'health_labels', 'dish_type', 'cuisine_type', 'meal_type']
            for field in json_fields:
                if field in recipe:
                    try:
                        recipe[field] = json.loads(recipe[field]) if isinstance(recipe[field], str) else recipe[field]
                    except:
                        recipe[field] = []
            
            # Combine all tags/labels into keywords for frontend compatibility
            if not recipe.get('keywords'):
                all_tags = []
                all_tags.extend(recipe.get('diet_labels', []))
                all_tags.extend(recipe.get('health_labels', []))
                all_tags.extend(recipe.get('dish_type', []))
                all_tags.extend(recipe.get('cuisine_type', []))
                all_tags.extend(recipe.get('meal_type', []))
                recipe['keywords'] = all_tags
            
            # Also populate 'tags' field for compatibility
            recipe['tags'] = recipe.get('keywords', [])
            
            # Clean up - remove the JSON string versions if they exist
            recipe.pop('instructions', None)
            
            return recipe
            
        except Exception as e:
            logger.error(f"Failed to get recipe by ID: {e}")
            return None


@lru_cache(maxsize=None)
def get_vector_store(persist_directory: str, embedding_model: str) -> "RecipeVectorStore":
    """Return a cached RecipeVectorStore instance for the given settings."""
    return RecipeVectorStore(persist_directory=persist_directory, embedding_model=embedding_model)
