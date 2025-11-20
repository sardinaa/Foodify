"""
Vector store service for recipe embeddings and semantic search.
Uses ChromaDB for vector storage and sentence-transformers for embeddings.
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import logging
import json
import re
from functools import lru_cache

logger = logging.getLogger(__name__)


class RecipeVectorStore:
    """Manages recipe embeddings and vector-based similarity search."""
    
    def __init__(self, persist_directory: str, embedding_model: str):
        """
        Initialize the vector store.
        
        Args:
            persist_directory: Path to ChromaDB persistence directory
            embedding_model: Name of the sentence-transformers model
        """
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Load embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="recipes",
            metadata={"description": "Recipe embeddings for semantic search"}
        )
        
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
        if recipe.get("Name"):
            text_parts.append(f"Recipe: {recipe['Name']}")
        
        if recipe.get("Description"):
            text_parts.append(f"Description: {recipe['Description']}")
        
        # Category
        if recipe.get("RecipeCategory"):
            text_parts.append(f"Category: {recipe['RecipeCategory']}")
        
        # Keywords
        keywords = self._parse_r_array(recipe.get("Keywords"))
        if keywords:
            text_parts.append(f"Tags: {', '.join(keywords)}")
        
        # Ingredients
        ingredients = self._parse_r_array(recipe.get("RecipeIngredientParts"))
        if ingredients:
            text_parts.append(f"Ingredients: {', '.join(ingredients)}")
        
        # Instructions
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
        ingredients = self._parse_r_array(recipe.get("RecipeIngredientParts"))
        
        # Parse instructions
        instructions = self._parse_r_array(recipe.get("RecipeInstructions"))
        
        # Parse time values
        cook_time = recipe.get("CookTime", "")
        prep_time = recipe.get("PrepTime", "")
        total_time = recipe.get("TotalTime", "")
        
        # Extract minutes from ISO 8601 duration format (e.g., "PT30M" -> 30, "PT2H20M" -> 140)
        time_minutes = 0
        if total_time and "PT" in total_time:
            import re
            # Extract hours and convert to minutes
            hours_match = re.search(r'(\d+)H', total_time)
            if hours_match:
                time_minutes += int(hours_match.group(1)) * 60
            # Extract minutes
            minutes_match = re.search(r'(\d+)M', total_time)
            if minutes_match:
                time_minutes += int(minutes_match.group(1))
        
        return {
            "recipe_id": str(recipe.get("RecipeId", "")),
            "name": recipe.get("Name", ""),
            "category": recipe.get("RecipeCategory", ""),
            "keywords": json.dumps(keywords),  # Store as JSON string
            "ingredients": json.dumps(ingredients),  # Store as JSON string
            "instructions": json.dumps(instructions),  # Store as JSON string
            "servings": float(recipe.get("RecipeServings", 0)) if recipe.get("RecipeServings") else 0.0,
            "calories": float(recipe.get("Calories", 0)) if recipe.get("Calories") else 0.0,
            "protein": float(recipe.get("ProteinContent", 0)) if recipe.get("ProteinContent") else 0.0,
            "carbs": float(recipe.get("CarbohydrateContent", 0)) if recipe.get("CarbohydrateContent") else 0.0,
            "fat": float(recipe.get("FatContent", 0)) if recipe.get("FatContent") else 0.0,
            "time": float(time_minutes) if time_minutes else 0.0,
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
                    recipe_id_raw = recipe.get("RecipeId")
                    if recipe_id_raw is not None and recipe_id_raw != "":
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
                    # Generate embeddings
                    embeddings = self.embedding_model.encode(
                        documents,
                        show_progress_bar=False,
                        convert_to_numpy=True
                    ).tolist()
                    
                    # Add to ChromaDB
                    self.collection.add(
                        embeddings=embeddings,
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    
                    added += len(documents)
                    logger.info(f"Added batch {i//batch_size + 1}, total: {added} recipes")
                    
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
            # Generate query embedding
            query_embedding = self.embedding_model.encode(
                query,
                convert_to_numpy=True
            ).tolist()
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_dict
            )
            
            # Format results
            recipes = []
            for i in range(len(results['ids'][0])):
                recipe = {
                    "id": results['ids'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None,
                    **results['metadatas'][0][i]
                }
                # Parse JSON fields back to lists
                if 'keywords' in recipe:
                    try:
                        recipe['keywords'] = json.loads(recipe['keywords'])
                    except:
                        recipe['keywords'] = []
                
                if 'ingredients' in recipe:
                    try:
                        recipe['ingredients'] = json.loads(recipe['ingredients'])
                    except:
                        recipe['ingredients'] = []
                
                if 'instructions' in recipe:
                    try:
                        recipe['instructions'] = json.loads(recipe['instructions'])
                    except:
                        recipe['instructions'] = []
                
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
        self.client.delete_collection("recipes")
        self.collection = self.client.get_or_create_collection(
            name="recipes",
            metadata={"description": "Recipe embeddings for semantic search"}
        )
        logger.info("Vector store cleared")
    
    def get_unique_categories(self) -> List[str]:
        """
        Get all unique recipe categories from the vector store.
        
        Returns:
            Sorted list of unique category names
        """
        try:
            # Query all recipes to get their categories
            results = self.collection.get(
                include=['metadatas']
            )
            
            # Extract unique categories
            categories = set()
            for metadata in results['metadatas']:
                category = metadata.get('category', '')
                if category and category.strip():
                    categories.add(category)
            
            # Return sorted list
            return sorted(list(categories))
            
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return []
    
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
                # Parse keywords back to list
                if 'keywords' in recipe:
                    try:
                        recipe['keywords'] = json.loads(recipe['keywords'])
                    except:
                        recipe['keywords'] = []
                
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
            
            # Parse keywords back to list
            if 'keywords' in recipe:
                try:
                    recipe['keywords'] = json.loads(recipe['keywords'])
                except:
                    recipe['keywords'] = []
            
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
