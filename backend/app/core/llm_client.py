"""
LLM client for text-based AI operations.
Model-agnostic interface for recipe generation and chat.
"""
import json
from typing import List, Dict, Optional, Tuple
import httpx

from app.core.config import get_settings
from app.db.schema import RecipeBase, IngredientBase, RecipeStepBase
from app.utils.prompt_loader import get_prompt_loader


class LLMClient:
    """Client for interacting with Language Models."""
    
    def __init__(self):
        self.settings = get_settings()
        self.prompt_loader = get_prompt_loader()
    
    async def _call_ollama(self, prompt: str, system: Optional[str] = None) -> str:
        """Call Ollama API."""
        url = f"{self.settings.llm_base_url}/api/generate"
        print(f"[LLM Client] Calling {url} with model {self.settings.llm_model}")
        print(f"[LLM Client] Prompt preview: {prompt[:200]}...")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": self.settings.llm_model,
                "prompt": prompt,
                "stream": False
            }
            
            if system:
                payload["system"] = system
            
            response = await client.post(url, json=payload)
            print(f"[LLM Client] Response status: {response.status_code}")
            if response.status_code != 200:
                print(f"[LLM Client] Error response: {response.text[:500]}")
            response.raise_for_status()
            return response.json()["response"]
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        system: Optional[str] = None
    ) -> str:
        """
        Chat-style interaction with the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-1.0)
            system: Optional system prompt
            
        Returns:
            LLM response text
        """
        # Convert messages to a single prompt
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt = "\n\n".join(prompt_parts)
        
        # Call Ollama with temperature
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": self.settings.llm_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            
            if system:
                payload["system"] = system
            
            response = await client.post(
                f"{self.settings.llm_base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            return response.json()["response"]
    
    async def generate_recipe_from_text(self, raw_text: str) -> RecipeBase:
        """
        Extract a structured recipe from raw text.
        
        Args:
            raw_text: Text containing recipe information
        
        Returns:
            RecipeBase object with structured data
        """
        # Load prompts from JSON
        prompt_config = self.prompt_loader.get_llm_prompt("recipe_extraction")
        system_config = prompt_config.get("system", "")
        # Join array into string if needed
        system_prompt = "\n".join(system_config) if isinstance(system_config, list) else system_config
        user_template = prompt_config.get("user_template", "Extract recipe from this text:\n\n{raw_text}")
        
        user_prompt = self.prompt_loader.format_prompt(user_template, raw_text=raw_text[:3000])
        
        response = await self._call_ollama(user_prompt, system_prompt)
        
        # Parse JSON response
        try:
            # Extract JSON from response (in case there's extra text)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
            else:
                json_str = response
            
            data = json.loads(json_str)
            
            # Convert to RecipeBase
            ingredients = [IngredientBase(**ing) for ing in data.get("ingredients", [])]
            steps = [RecipeStepBase(**step) for step in data.get("steps", [])]
            
            return RecipeBase(
                name=data.get("name", "Unknown Recipe"),
                description=data.get("description"),
                servings=data.get("servings", 4),
                total_time_minutes=data.get("total_time_minutes", 30),
                ingredients=ingredients,
                steps=steps
            )
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback if parsing fails
            return RecipeBase(
                name="Recipe (parsing error)",
                description="Could not parse recipe details",
                servings=4,
                total_time_minutes=30,
                ingredients=[],
                steps=[]
            )
    
    async def normalize_dish_name_and_tags(
        self,
        description: str,
        user_title: Optional[str] = None
    ) -> Tuple[str, List[str]]:
        """
        Generate a canonical dish name and tags from description.
        
        Args:
            description: Dish description
            user_title: Optional user-provided title
        
        Returns:
            Tuple of (canonical_name, list_of_tags)
        """
        # Load prompts from JSON
        prompt_config = self.prompt_loader.get_llm_prompt("dish_normalization")
        template = prompt_config.get("template", "")
        user_title_line_template = prompt_config.get("user_title_line_template", "")
        
        # Format user title line if provided
        user_title_line = ""
        if user_title:
            user_title_line = self.prompt_loader.format_prompt(user_title_line_template, user_title=user_title)
        
        # Format the main prompt
        prompt = self.prompt_loader.format_prompt(
            template,
            description=description,
            user_title_line=user_title_line
        )
        
        response = await self._call_ollama(prompt)
        
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                return data.get("name", user_title or "Unknown Dish"), data.get("tags", [])
        except:
            pass
        
        return user_title or "Unknown Dish", []
    
    async def suggest_recipes_from_ingredients(
        self,
        ingredients: List[str],
        existing_recipes: Optional[List[RecipeBase]] = None
    ) -> List[RecipeBase]:
        """
        Suggest recipes based on available ingredients.
        
        Args:
            ingredients: List of available ingredients
            existing_recipes: Optional list of existing recipes to consider
        
        Returns:
            List of suggested RecipeBase objects
        """
        # Load prompts from JSON
        prompt_config = self.prompt_loader.get_llm_prompt("ingredients_to_recipes")
        template = prompt_config.get("template", "")
        
        ingredients_str = ", ".join(ingredients)
        prompt = self.prompt_loader.format_prompt(template, ingredients_str=ingredients_str)
        
        response = await self._call_ollama(prompt)
        
        try:
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start >= 0:
                json_str = response[json_start:json_end]
                recipes_data = json.loads(json_str)
                
                recipes = []
                for data in recipes_data[:3]:  # Max 3 recipes
                    ingredients = [IngredientBase(**ing) for ing in data.get("ingredients", [])]
                    steps = [RecipeStepBase(**step) for step in data.get("steps", [])]
                    
                    recipes.append(RecipeBase(
                        name=data.get("name", "Recipe"),
                        description=data.get("description"),
                        servings=data.get("servings", 4),
                        total_time_minutes=data.get("total_time_minutes", 30),
                        ingredients=ingredients,
                        steps=steps
                    ))
                
                return recipes
        except:
            pass
        
        return []
    
    async def plan_weekly_menu(
        self,
        constraints: Dict,
        available_recipes: Optional[List[RecipeBase]] = None
    ) -> Dict:
        """
        Plan a weekly menu based on constraints.
        
        Args:
            constraints: Dict with planning constraints
            available_recipes: Optional list of available recipes
        
        Returns:
            Weekly menu structure
        """
        # Load prompts from JSON
        prompt_config = self.prompt_loader.get_llm_prompt("weekly_menu_planning")
        template = prompt_config.get("template", "")
        
        constraints_str = ", ".join(f"{k}: {v}" for k, v in constraints.items())
        prompt = self.prompt_loader.format_prompt(template, constraints_str=constraints_str)
        
        response = await self._call_ollama(prompt)
        
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        
        return {"name": "Weekly Plan", "days": []}


# Global instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create global LLMClient instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
