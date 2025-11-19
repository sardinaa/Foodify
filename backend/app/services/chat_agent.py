"""
Chat agent for conversational recipe assistance.
Handles ingredient-based suggestions and weekly menu planning.
With conversation memory to track user preferences and requirements.
Uses LLM-based intent detection for flexible, context-aware classification.
"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.llm_client import get_llm_client
from app.db.schema import Recipe, WeeklyMenu, WeeklyMenuDay
from app.db.crud_recipes import get_recipes, search_recipes
from app.db.crud_menus import create_menu
from app.services.recipe_service import create_recipe_with_nutrition, model_to_recipe
from app.services.conversation_memory import ConversationMemory


async def analyze_conversation_context(
    message: str,
    memory: Optional[ConversationMemory] = None
) -> Dict:
    """
    Use LLM to intelligently analyze conversation context and understand what user is referring to.
    Returns structured information about user's intent and referenced items.
    
    Returns:
        Dict with:
        - action: "show_previous", "include_in_new", "modify_previous", or "new_request"
        - referenced_items: List of items from conversation the user is referring to
    """
    from app.core.llm_client import get_llm_client
    from app.utils.prompt_loader import get_prompt_loader
    import json
    
    llm = get_llm_client()
    prompt_loader = get_prompt_loader()
    
    # Build conversation history context
    conversation_history = "(No previous conversation)"
    previous_recipes = []
    
    if memory:
        history = memory.get_conversation_history(limit=8)
        if history:
            history_lines = []
            for msg in history:
                role = "User" if msg["role"] == "user" else "Assistant"
                content = msg["content"][:300]
                history_lines.append(f"{role}: {content}")
                
                # Extract recipes for matching
                if msg["role"] == "assistant" and "recipes" in msg:
                    previous_recipes.extend(msg["recipes"])
            
            conversation_history = "\n".join(history_lines)
    
    # Load context understanding prompt
    context_config = prompt_loader.get_llm_prompt("context_understanding")
    system_prompt = "\n".join(context_config.get("system", []))
    user_template = "\n".join(context_config.get("user_template", []))
    
    user_prompt = prompt_loader.format_prompt(
        user_template,
        conversation_history=conversation_history,
        user_message=message
    )
    
    response = await llm.chat(
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.1,
        system=system_prompt
    )
    
    # Parse JSON response
    try:
        # Clean up response - remove markdown code blocks if present
        cleaned_response = response.strip()
        if cleaned_response.startswith('```'):
            lines = cleaned_response.split('\n')
            cleaned_response = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned_response
        
        # Replace double curly braces with single (common LLM formatting issue)
        cleaned_response = cleaned_response.replace('{{', '{').replace('}}', '}')
        
        json_start = cleaned_response.find('{')
        json_end = cleaned_response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = cleaned_response[json_start:json_end]
            context_analysis = json.loads(json_str)
            
            print(f"[Context Analysis] Action: {context_analysis.get('action')}, Items: {len(context_analysis.get('referenced_items', []))}")
            
            # Match referenced items with actual recipes from conversation
            for item in context_analysis.get("referenced_items", []):
                item_name = item.get("name", "").lower()
                print(f"[Context Analysis] Looking for recipe matching: {item_name}")
                
                for prev_recipe in previous_recipes:
                    prev_name = prev_recipe.get("name", "").lower()
                    # Flexible matching - check if either name contains the other
                    if item_name in prev_name or prev_name in item_name or any(word in prev_name for word in item_name.split() if len(word) > 3):
                        item["matched_recipe"] = prev_recipe
                        print(f"[Context Analysis] Matched '{item_name}' to '{prev_recipe.get('name')}'")
                        break
            
            return context_analysis
    except Exception as e:
        print(f"Failed to parse context analysis: {e}")
        print(f"Raw response was: {response[:200]}")
    
    # Fallback - check if user is referencing "this", "it", "the recipe" etc
    message_lower = message.lower()
    
    # Check if this is a menu modification
    menu_modification_words = ["change", "replace", "swap", "modify", "remove", "update"]
    day_words = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    meal_words = ["breakfast", "lunch", "dinner"]
    
    has_menu_modification = any(word in message_lower for word in menu_modification_words)
    has_day_reference = any(word in message_lower for word in day_words)
    has_meal_reference = any(word in message_lower for word in meal_words)
    
    # Check if previous response was a menu (multiple recipes with day_name)
    is_previous_menu = previous_recipes and len(previous_recipes) > 1 and all(r.get("day_name") for r in previous_recipes)
    
    if has_menu_modification and (has_day_reference or has_meal_reference) and is_previous_menu:
        print(f"[Context Analysis] Fallback: Detected menu modification request")
        return {
            "action": "modify_menu",
            "referenced_items": [{
                "type": "menu",
                "name": "current menu",
                "context": message
            }]
        }
    
    # Check for general reference words
    reference_words = ["this", "it", "that", "the recipe", "include it", "add it", "use it"]
    
    if any(word in message_lower for word in reference_words) and previous_recipes:
        print(f"[Context Analysis] Fallback: Detected reference word, using most recent recipe")
        return {
            "action": "include_in_new",
            "referenced_items": [{
                "type": "recipe",
                "name": previous_recipes[-1].get("name", ""),
                "context": message,
                "matched_recipe": previous_recipes[-1]
            }]
        }
    
    return {"action": "new_request", "referenced_items": []}


async def detect_user_intent_with_llm(
    message: str, 
    memory: Optional[ConversationMemory] = None,
    image_present: bool = False,
    context_analysis: Optional[Dict] = None
) -> str:
    """
    Use LLM to detect user intent based on message and conversation context analysis.
    Much more flexible than hardcoded patterns.
    
    Returns:
        - "url_analysis": User wants to extract recipe from a URL
        - "modification": User wants to modify a previous recipe/menu
        - "ingredients": User wants recipes based on ingredients they have
        - "weekly_menu": User wants a weekly meal plan
        - "recipe_search": User wants to find specific recipes or recommendations
    """
    from app.core.llm_client import get_llm_client
    from app.utils.prompt_loader import get_prompt_loader
    
    # Use context analysis to help determine intent
    if context_analysis:
        action = context_analysis.get("action")
        if action == "show_previous" or action == "modify_previous":
            return "modification"
        elif action == "modify_menu":
            return "weekly_menu"
        elif action == "include_in_new":
            # Check if it's a menu request
            message_lower = message.lower()
            if "menu" in message_lower or "plan" in message_lower or any(day in message_lower for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                return "weekly_menu"
    
    # Build context from conversation history
    history_context = "(No previous conversation)"
    if memory:
        history = memory.get_conversation_history(limit=6)
        if history:
            history_lines = []
            for msg in history[-4:]:  # Last 2 exchanges
                role = "User" if msg["role"] == "user" else "Assistant"
                content = msg["content"][:150]
                history_lines.append(f"{role}: {content}")
            history_context = "\n".join(history_lines)
    
    image_context = "Note: User has attached an image." if image_present else ""
    
    # Load prompt from JSON template
    prompt_loader = get_prompt_loader()
    intent_config = prompt_loader.get_llm_prompt("intent_classification")
    system_prompt = "\n".join(intent_config.get("system", []))
    user_template = "\n".join(intent_config.get("user_template", []))
    
    # Format user prompt with context
    user_prompt = prompt_loader.format_prompt(
        user_template,
        history_context=history_context,
        image_context=image_context,
        user_message=message
    )

    llm = get_llm_client()
    response = await llm.chat(
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.1,
        system=system_prompt
    )
    
    # Extract intent from response
    intent = response.strip().lower()
    
    # Validate and normalize
    valid_intents = ["url_analysis", "weekly_menu", "modification", "nutrition", "ingredients", "recipe_search"]
    for valid in valid_intents:
        if valid in intent:
            return valid
    
    # Default fallback
    return "recipe_search"


async def handle_url_analysis_mode(
    db: Session,
    session_id: str,
    message: str,
    memory: Optional[ConversationMemory] = None
) -> Dict:
    """
    Handle URL analysis - extract recipe from a provided URL.
    
    Args:
        db: Database session
        session_id: Chat session ID
        message: User message containing URL
        memory: Conversation memory instance
    
    Returns:
        Dict with reply and extracted recipe
    """
    import re
    from app.services.url_pipeline import analyze_url_pipeline
    
    # Extract URL from message
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, message)
    
    if not urls:
        # Try to find www. patterns
        www_pattern = r'www\.[^\s]+'
        www_urls = re.findall(www_pattern, message)
        if www_urls:
            urls = [f"https://{url}" for url in www_urls]
    
    if not urls:
        return {
            "reply": "I couldn't find a valid URL in your message. Please provide a complete URL (e.g., https://example.com/recipe)",
            "suggested_recipes": [],
            "weekly_menu": None
        }
    
    url = urls[0]  # Use first URL found
    
    try:
        print(f"[URL Analysis] Extracting recipe from: {url}")
        
        # Use the URL pipeline to extract and save recipe
        recipe, nutrition, tags = await analyze_url_pipeline(db, url)
        
        # Convert to dict format expected by frontend
        recipe_dict = {
            "id": recipe.id,
            "name": recipe.name,
            "description": recipe.description or "",
            "servings": recipe.servings,
            "total_time_minutes": recipe.total_time_minutes,
            "ingredients": [
                {
                    "name": ing.name,
                    "quantity": ing.quantity,
                    "unit": ing.unit
                }
                for ing in recipe.ingredients
            ],
            "steps": [
                {
                    "step_number": step.step_number,
                    "instruction": step.instruction
                }
                for step in recipe.steps
            ],
            "source_type": "url",
            "source_ref": url,
            "tags": tags[:5],
            "calories": nutrition.per_serving.kcal if nutrition else None,
            "protein": nutrition.per_serving.protein if nutrition else None,
            "carbs": nutrition.per_serving.carbs if nutrition else None,
            "fat": nutrition.per_serving.fat if nutrition else None,
            "created_at": recipe.created_at.isoformat() if recipe.created_at else datetime.now().isoformat()
        }
        
        reply = f"Successfully extracted the recipe '{recipe.name}' from the URL! Here are the details:"
        
        return {
            "reply": reply,
            "suggested_recipes": [recipe_dict],
            "weekly_menu": None
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"[URL Analysis] Failed to extract recipe: {error_msg}")
        
        # Provide helpful error message
        if "Could not access content" in error_msg or "403" in error_msg or "401" in error_msg:
            reply = "I couldn't access the content from this URL. The website may require login or is blocking automated access. Try copying the recipe text directly and I can extract it from that!"
        elif "Could not extract a recipe" in error_msg:
            reply = "I couldn't find a recipe in the content from this URL. The page may not contain recipe information. Try copying the recipe text and pasting it directly!"
        else:
            reply = f"Sorry, I encountered an error while extracting the recipe from this URL: {error_msg}. Try copying the recipe text directly and I can help with that!"
        
        return {
            "reply": reply,
            "suggested_recipes": [],
            "weekly_menu": None
        }


async def handle_recipe_search_mode(
    db: Session,
    session_id: str,
    message: str,
    memory: Optional[ConversationMemory] = None
) -> Dict:
    """
    Handle general recipe search and recommendations using RAG.
    Uses conversation history for context continuity.
    
    Args:
        db: Database session
        session_id: Chat session ID
        message: User query for recipes
        memory: Conversation memory instance (for message history)
    
    Returns:
        Dict with reply and suggested_recipes
    """
    try:
        from app.services.recipe_rag import RecipeRAGService
        
        rag_service = RecipeRAGService()
        
        # Use RAG to get personalized recommendations
        # The message is used as-is; history provides context if needed
        recommendations = await rag_service.get_recipe_recommendations(
            user_query=message,
            n_results=5
        )
        
        # Convert to Recipe schema format
        # Note: ChromaDB only stores metadata, not full ingredients/steps
        # Frontend will fetch full details via /api/rag/recipe/{id} if needed
        suggested_recipes = []
        for rec in recommendations.get('recipes', [])[:3]:  # Top 3
            recipe_dict = {
                "id": rec.get('recipe_id', 0),  # Use actual recipe ID from ChromaDB
                "name": rec.get('name', 'Unknown Recipe'),
                "description": rec.get('description', ''),
                "servings": int(rec.get('servings', 4)),
                "total_time_minutes": int(rec.get('time', 30)),  # ChromaDB stores as 'time' not 'total_time_minutes'
                "ingredients": [],  # Empty - frontend fetches via API if needed
                "steps": [],  # Empty - frontend fetches via API if needed
                "source_type": "dataset",  # These are from the dataset in ChromaDB
                "source_ref": str(rec.get('recipe_id', '')),
                "tags": rec.get('keywords', [])[:3] if rec.get('keywords') else [],
                "created_at": datetime.now().isoformat()
            }
            suggested_recipes.append(recipe_dict)
        
        reply = recommendations.get('explanation', 
                                   f"I found {len(suggested_recipes)} great recipes for you!")
        
        return {
            "reply": reply,
            "suggested_recipes": suggested_recipes,
            "weekly_menu": None
        }
    except Exception as e:
        # Fallback to simple database search
        print(f"RAG search failed: {e}, falling back to simple search")
        recipes = search_recipes(db, message)
        
        # Limit to first 3 results and convert to dicts
        suggested_recipes = [model_to_recipe(r).model_dump() for r in recipes[:3]] if recipes else []
        
        if suggested_recipes:
            names = [r["name"] for r in suggested_recipes]
            reply = f"Here are some recipes I found: {', '.join(names)}. Would you like more details?"
        else:
            reply = "I couldn't find any recipes matching your request. Could you try rephrasing or being more specific?"
        
        return {
            "reply": reply,
            "suggested_recipes": suggested_recipes,
            "weekly_menu": None
        }


async def handle_modification_mode(
    db: Session,
    session_id: str,
    message: str,
    memory: Optional[ConversationMemory] = None
) -> Dict:
    """
    Handle recipe/menu modification requests OR requests to see full recipe details.
    Uses conversation history to find what to modify/show and applies the changes.
    
    Args:
        db: Database session
        session_id: Chat session ID
        message: User modification request or request to see full recipe
        memory: Conversation memory instance
    
    Returns:
        Dict with reply and modified/full recipe(s)
    """
    llm = get_llm_client()
    
    # Get conversation history to understand context
    history = memory.get_conversation_history(limit=10) if memory else []
    print(f"[Modification] Got {len(history)} messages from history")
    
    # Find the most recent recipes from assistant messages
    previous_recipes = []
    for msg in reversed(history):
        print(f"[Modification] Checking message: role={msg['role']}, has_recipes={'recipes' in msg}")
        if msg["role"] == "assistant" and "recipes" in msg:
            previous_recipes.extend(msg["recipes"])
            print(f"[Modification] Found {len(msg['recipes'])} recipes")
            break  # Just use the most recent assistant message with recipes
    
    print(f"[Modification] Total previous recipes: {len(previous_recipes)}")
    
    if not previous_recipes:
        return {
            "reply": "I don't see any recipes from our recent conversation to modify. Could you please ask me for a recipe first, then I can help you adapt it?",
            "suggested_recipes": [],
            "weekly_menu": None
        }
    
    # Use LLM to understand what the user wants to do with the previous recipe
    context_analysis = await analyze_conversation_context(message, memory)
    action = context_analysis.get("action", "modify_previous")
    
    print(f"[Modification] Context analysis: action={action}")
    
    if action == "show_previous":
        # User just wants to see the full recipe - return it as-is
        print(f"[Modification] User wants to see full recipe details, returning previous recipe")
        
        # Make sure the recipe has show_nutrition_only flag set to False
        for recipe in previous_recipes:
            recipe["show_nutrition_only"] = False
        
        reply = f"Here's the full recipe for **{previous_recipes[0]['name']}** with all ingredients and instructions!"
        
        return {
            "reply": reply,
            "suggested_recipes": previous_recipes,
            "weekly_menu": None
        }
    
    # Build prompt with the actual recipe data
    import json
    recipes_json = json.dumps(previous_recipes, indent=2)
    
    prompt = f"""I have the following recipe(s) from our conversation:

{recipes_json}

The user wants to modify them with this request: "{message}"

Please generate the modified recipe(s) in JSON format. Return a JSON object with this structure:
{{
    "recipes": [
        {{
            "name": "Recipe name (indicate it's modified, e.g., 'Vegetarian Pasta Carbonara')",
            "description": "Brief description of modifications made",
            "servings": 4,
            "total_time_minutes": 30,
            "ingredients": [
                {{"name": "ingredient", "quantity": 1.0, "unit": "cup"}}
            ],
            "steps": [
                {{"step_number": 1, "instruction": "Step instruction"}}
            ]
        }}
    ],
    "explanation": "Explain what changes were made and why"
}}

Make sure to apply the user's requested modifications (e.g., make vegetarian, reduce spice, add vegetables, etc.).
"""
    
    try:
        response = await llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        # Extract JSON from response
        import json
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            result = json.loads(json_str)
            
            # Convert to our format WITHOUT saving to database
            # Just return the modified recipe as a dictionary
            modified_recipes = []
            for idx, recipe_data in enumerate(result.get("recipes", [])):
                recipe_dict = {
                    "id": f"modified_{session_id}_{idx}",  # Temporary ID
                    "name": recipe_data.get("name", "Modified Recipe"),
                    "description": recipe_data.get("description", ""),
                    "servings": recipe_data.get("servings", 4),
                    "total_time_minutes": recipe_data.get("total_time_minutes", 30),
                    "ingredients": recipe_data.get("ingredients", []),
                    "steps": recipe_data.get("steps", []),
                    "source_type": "modified",
                    "source_ref": f"session_{session_id}",
                    "tags": ["modified", "ai-adapted"],
                    "created_at": datetime.now().isoformat()
                }
                modified_recipes.append(recipe_dict)
            
            explanation = result.get("explanation", "I've modified the recipe(s) based on your request.")
            explanation += "\n\nThis is a modified version. If you'd like to save it to your collection, let me know!"
            
            return {
                "reply": explanation,
                "suggested_recipes": modified_recipes,
                "weekly_menu": None
            }
    
    except Exception as e:
        print(f"Error modifying recipe: {e}")
        import traceback
        traceback.print_exc()
    
    return {
        "reply": "I had trouble modifying the recipe. Could you be more specific about what changes you'd like?",
        "suggested_recipes": [],
        "weekly_menu": None
    }


async def handle_ingredients_mode(
    db: Session,
    session_id: str,
    message: str,
    memory: Optional[ConversationMemory] = None
) -> Dict:
    """
    Handle ingredient-based recipe suggestions.
    Uses conversation history to understand context (e.g., follow-up modifications).
    
    Args:
        db: Database session
        session_id: Chat session ID
        message: User message with ingredients
        memory: Conversation memory instance (for message history)
    
    Returns:
        Dict with reply and suggested_recipes
    """
    llm = get_llm_client()
    
    # Extract ingredients from message (simple approach)
    # In production, you'd use NER or better parsing
    ingredients = [
        word.strip().lower()
        for word in message.replace(",", " ").split()
        if len(word.strip()) > 2
    ]
    
    # Get existing recipes from database
    existing_recipes = get_recipes(db, limit=50)
    existing_recipe_bases = [
        # Convert models to bases (simplified)
    ]
    
    # Get AI suggestions
    suggested_recipe_bases = await llm.suggest_recipes_from_ingredients(
        ingredients,
        existing_recipe_bases if existing_recipes else None
    )
    
    # Convert to full recipes by saving them
    suggested_recipes = []
    for recipe_base in suggested_recipe_bases:
        recipe, _ = create_recipe_with_nutrition(
            db,
            recipe_base,
            source_type="chat",
            source_ref=f"session_{session_id}",
            tags=["ai-suggested", "from-ingredients"]
        )
        suggested_recipes.append(recipe.model_dump())
    
    # Generate natural language reply
    recipe_names = [r["name"] for r in suggested_recipes]
    reply = f"Based on your ingredients, I suggest these {len(recipe_names)} recipes: {', '.join(recipe_names)}. Would you like to see any of them in detail?"
    
    return {
        "reply": reply,
        "suggested_recipes": suggested_recipes,
        "weekly_menu": None
    }


async def handle_weekly_menu_mode(
    db: Session,
    session_id: str,
    message: str,
    memory: Optional[ConversationMemory] = None
) -> Dict:
    """
    Handle weekly menu planning mode.
    Generate flexible menu based on user constraints (days, meals, dietary needs).
    Uses LLM to parse constraints in any language.
    Uses conversation history for context (e.g., "make it vegetarian" refers to previous request).
    
    Args:
        db: Database session
        session_id: Chat session ID
        message: User message with constraints
        memory: Conversation memory instance (for message history)
    
    Returns:
        Dict with reply and suggested_recipes (variable count based on request)
    """
    try:
        from app.services.recipe_rag import RecipeRAGService
        from app.core.llm_client import get_llm_client
        from app.utils.prompt_loader import get_prompt_loader
        import json
        
        rag_service = RecipeRAGService()
        llm = get_llm_client()
        prompt_loader = get_prompt_loader()
        
        # Get conversation history for context and extract previous recipes/menu
        history_context = ""
        previous_recipes = []
        existing_menu = None  # Track if there's an existing menu to modify
        
        if memory:
            history = memory.get_conversation_history(limit=6)
            if history:
                history_lines = []
                for msg in history[-4:]:  # Last 2 exchanges
                    role = "User" if msg["role"] == "user" else "Assistant"
                    content = msg["content"][:200]  # Truncate long responses
                    history_lines.append(f"{role}: {content}")
                    
                    # Extract recipes from conversation
                    if msg["role"] == "assistant" and "recipes" in msg:
                        recipes_in_msg = msg["recipes"]
                        # Check if this is a menu (multiple recipes with day_name and meal_type)
                        if recipes_in_msg and len(recipes_in_msg) > 1 and all(r.get("day_name") for r in recipes_in_msg):
                            existing_menu = recipes_in_msg  # This is a menu
                            print(f"[Weekly Menu] Found existing menu with {len(existing_menu)} items")
                        previous_recipes.extend(recipes_in_msg)
                
                history_context = "\n\nPrevious conversation:\n" + "\n".join(history_lines)
        
        # Use LLM to parse user constraints (works in any language)
        parser_config = prompt_loader.get_llm_prompt("menu_constraint_parser")
        system_prompt = "\n".join(parser_config.get("system", []))
        user_template = "\n".join(parser_config.get("user_template", []))
        user_prompt = prompt_loader.format_prompt(user_template, user_message=message) + history_context
        
        llm_response = await llm.chat(
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.1,  # Low temperature for structured output
            system=system_prompt
        )
        
        # Parse LLM response
        try:
            # Clean up response
            cleaned_llm_response = llm_response.strip()
            if cleaned_llm_response.startswith('```'):
                lines = cleaned_llm_response.split('\n')
                cleaned_llm_response = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned_llm_response
            
            # Replace double curly braces with single
            cleaned_llm_response = cleaned_llm_response.replace('{{', '{').replace('}}', '}')
            
            # Extract JSON from response
            json_start = cleaned_llm_response.find('{')
            json_end = cleaned_llm_response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = cleaned_llm_response[json_start:json_end]
                constraints = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            print(f"Failed to parse LLM response: {e}")
            print(f"LLM response was: {llm_response[:200]}")
            # Fallback to defaults
            constraints = {
                "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                "meals": ["breakfast", "lunch", "dinner"],
                "dietary": []
            }
        
        # Extract parsed values
        day_names = constraints.get("days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        meal_types = constraints.get("meals", ["breakfast", "lunch", "dinner"])
        dietary_restrictions = constraints.get("dietary", [])
        
        all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        print(f"Parsed constraints - Days: {day_names}, Meals: {meal_types}, Dietary: {dietary_restrictions}")
        
        # Check if this is a menu modification request
        is_menu_modification = existing_menu is not None and any(
            word in message.lower() for word in ["change", "replace", "swap", "modify", "update", "remove"]
        )
        
        print(f"[Weekly Menu] Is menu modification: {is_menu_modification}")
        
        # Use LLM-based context analysis to find specific recipes user wants to include
        context_analysis = await analyze_conversation_context(message, memory)
        referenced_items = context_analysis.get("referenced_items", [])
        
        print(f"[Weekly Menu] Context analysis action: {context_analysis.get('action')}")
        print(f"[Weekly Menu] Context analysis found {len(referenced_items)} referenced items")
        for item in referenced_items:
            print(f"[Weekly Menu] Referenced item: {item.get('name')} - has match: {'matched_recipe' in item}")
        
        # Build a map of (day, meal) -> specific recipe to include
        specific_recipe_map = {}
        
        for item in referenced_items:
            if item.get("type") == "recipe" and "matched_recipe" in item:
                matched_recipe = item["matched_recipe"]
                context_text = item.get("context", "").lower()
                message_lower = message.lower()
                
                print(f"[Weekly Menu] Processing referenced item: {item.get('name')}")
                print(f"[Weekly Menu] Context text: {context_text}")
                print(f"[Weekly Menu] User message: {message_lower}")
                
                # Extract day from user message - look for "in/on [day]" pattern first
                target_day = None
                
                # First, check for explicit "in/on Wednesday" pattern (most specific)
                for day in all_days:
                    day_lower = day.lower()
                    # Look for patterns like "in wednesday", "on wednesday", "wednesday for"
                    if f"in {day_lower}" in message_lower or f"on {day_lower}" in message_lower or f"{day_lower} for" in message_lower:
                        target_day = day
                        print(f"[Weekly Menu] Found day '{day}' with position indicator in user message")
                        break
                
                # If not found with position indicator, look in context (LLM understood context better)
                if not target_day:
                    for day in all_days:
                        if day.lower() in context_text:
                            target_day = day
                            print(f"[Weekly Menu] Found day '{day}' in context")
                            break
                
                # Last resort: find any day mention in message (but this catches "Monday to Friday" incorrectly)
                if not target_day:
                    for day in all_days:
                        if day.lower() in message_lower:
                            # Only use if it appears isolated (not part of range)
                            # Check it's not part of "monday to friday" by seeing if "to" follows
                            day_pos = message_lower.find(day.lower())
                            if day_pos >= 0:
                                after_day = message_lower[day_pos:day_pos+20]
                                if " to " not in after_day:
                                    target_day = day
                                    print(f"[Weekly Menu] Found isolated day '{day}' in user message")
                                    break
                
                # Extract meal type from user message first, then context
                target_meal = None
                
                # Check for explicit meal mentions in message
                if "dinner" in message_lower or "diner" in message_lower:  # Handle typo "diner"
                    target_meal = "dinner"
                    print(f"[Weekly Menu] Found 'dinner' in user message")
                elif "lunch" in message_lower:
                    target_meal = "lunch"
                    print(f"[Weekly Menu] Found 'lunch' in user message")
                elif "breakfast" in message_lower:
                    target_meal = "breakfast"
                    print(f"[Weekly Menu] Found 'breakfast' in user message")
                
                # If not in message, check context
                if not target_meal:
                    if "dinner" in context_text:
                        target_meal = "dinner"
                    elif "lunch" in context_text:
                        target_meal = "lunch"
                    elif "breakfast" in context_text:
                        target_meal = "breakfast"
                
                # If still no meal type, infer from recipe name or requested meals
                if not target_meal:
                    recipe_name_lower = matched_recipe.get("name", "").lower()
                    if any(word in recipe_name_lower for word in ["oatmeal", "pancake", "breakfast", "eggs", "smoothie"]):
                        target_meal = "breakfast"
                    elif any(word in recipe_name_lower for word in ["salad", "sandwich", "lunch"]):
                        target_meal = "lunch"
                    else:
                        # Default to first requested meal type
                        target_meal = meal_types[0] if meal_types else "dinner"
                    print(f"[Weekly Menu] Inferred meal type: {target_meal}")
                
                # Only add if the target meal is in the requested meals
                if target_meal not in meal_types:
                    print(f"[Weekly Menu] Meal type '{target_meal}' not in requested meals {meal_types}, adjusting to first requested meal")
                    target_meal = meal_types[0] if meal_types else "dinner"
                
                if target_day and target_day in day_names:
                    specific_recipe_map[(target_day, target_meal)] = matched_recipe
                    print(f"[Weekly Menu] Will use '{matched_recipe.get('name')}' for {target_day} {target_meal}")
                elif not target_day:
                    # User didn't specify day, but wants it included - use first available slot
                    for day in day_names:
                        if (day, target_meal) not in specific_recipe_map:
                            specific_recipe_map[(day, target_meal)] = matched_recipe
                            print(f"[Weekly Menu] Will use '{matched_recipe.get('name')}' for {day} {target_meal} (auto-assigned)")
                            break
        
        # Define search queries for each meal type
        meal_search_queries = {
            'breakfast': ['breakfast', 'brunch', 'morning meal', 'oatmeal', 'eggs', 'pancakes', 'smoothie'],
            'lunch': ['lunch', 'salad', 'sandwich', 'soup', 'light meal', 'midday meal'],
            'dinner': ['dinner', 'main dish', 'pasta', 'rice', 'chicken', 'fish', 'beef', 'vegetarian dinner']
        }
        
        # Add dietary restrictions to search queries
        dietary_query_suffix = ''
        if dietary_restrictions:
            dietary_query_suffix = f" {' '.join(dietary_restrictions)}"
        
        recipes_by_meal = {}
        
        # Get recipes for each requested meal type
        needed_per_meal = len(day_names)  # One recipe per day
        
        for meal_type in meal_types:
            meal_recipes = []
            queries = meal_search_queries.get(meal_type, [meal_type])
            
            # Try multiple diverse queries to get variety
            for query in queries[:3]:  # Use first 3 query variations
                search_query = query + dietary_query_suffix
                results = rag_service.search_recipes(
                    query=search_query,
                    n_results=5
                )
                
                # Add recipes we haven't seen yet
                for rec in results:
                    recipe_id = rec.get('recipe_id', '')
                    if recipe_id and not any(r.get('recipe_id') == recipe_id for r in meal_recipes):
                        meal_recipes.append(rec)
                    
                    if len(meal_recipes) >= needed_per_meal + 2:  # Get a few extra for variety
                        break
                
                if len(meal_recipes) >= needed_per_meal:
                    break
            
            recipes_by_meal[meal_type] = meal_recipes[:needed_per_meal]
        
        # Check if we need to handle menu modifications (replace specific items)
        if is_menu_modification and existing_menu:
            # Start with the existing menu
            suggested_recipes = existing_menu.copy()
            
            # Use LLM to understand what to replace and with what - using JSON template
            mod_parser_config = prompt_loader.get_llm_prompt("menu_modification_parser")
            mod_system_prompt = "\n".join(mod_parser_config.get("system", []))
            mod_user_template = "\n".join(mod_parser_config.get("user_template", []))
            
            mod_user_prompt = prompt_loader.format_prompt(
                mod_user_template,
                user_message=message
            )

            llm_mod_response = await llm.chat(
                messages=[{"role": "user", "content": mod_user_prompt}],
                temperature=0.1,
                system=mod_system_prompt
            )
            
            # Parse response
            try:
                cleaned = llm_mod_response.strip()
                if cleaned.startswith('```'):
                    lines = cleaned.split('\n')
                    cleaned = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned
                cleaned = cleaned.replace('{{', '{').replace('}}', '}')
                
                json_start = cleaned.find('{')
                json_end = cleaned.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = cleaned[json_start:json_end]
                    mod_details = json.loads(json_str)
                    
                    replace_day = mod_details.get("day")
                    replace_meal = mod_details.get("meal")
                    replacement_query = mod_details.get("replacement_query", "")
                    
                    print(f"[Weekly Menu Modification] Day: {replace_day}, Meal: {replace_meal}")
                    print(f"[Weekly Menu Modification] Replacement query: {replacement_query}")
                else:
                    raise ValueError("No JSON in response")
            except Exception as e:
                print(f"[Weekly Menu Modification] Failed to parse LLM response: {e}")
                # Fallback to simple detection
                replace_day = None
                replace_meal = None
                replacement_query = None
                
                message_lower = message.lower()
                for day in all_days:
                    if day.lower() in message_lower:
                        replace_day = day
                        break
                for meal in ["breakfast", "lunch", "dinner"]:
                    if meal in message_lower:
                        replace_meal = meal
                        break
                replacement_query = replace_meal if replace_meal else "alternative"
            
            # Find and replace the specific item
            if replace_day and replace_meal and replacement_query:
                # Search for replacement recipe using LLM-generated query
                search_query = replacement_query
                if dietary_restrictions:
                    search_query += f" {' '.join(dietary_restrictions)}"
                
                replacement_results = rag_service.search_recipes(
                    query=search_query,
                    n_results=1
                )
                
                if replacement_results:
                    replacement_rec = replacement_results[0]
                    replacement_recipe = {
                        "id": replacement_rec.get('recipe_id', 0),
                        "name": replacement_rec.get('name', 'Unknown Recipe'),
                        "servings": int(replacement_rec.get('servings', 4)),
                        "total_time_minutes": int(replacement_rec.get('time', 30)),
                        "ingredients": [],
                        "steps": [],
                        "source_type": "dataset",
                        "source_ref": replacement_rec.get('recipe_id', ''),
                        "tags": replacement_rec.get('keywords', [])[:3] if replacement_rec.get('keywords') else [],
                        "created_at": datetime.now().isoformat(),
                        "day_name": replace_day,
                        "meal_type": replace_meal
                    }
                    
                    # Replace the item in the menu
                    for idx, recipe in enumerate(suggested_recipes):
                        if recipe.get("day_name") == replace_day and recipe.get("meal_type") == replace_meal:
                            suggested_recipes[idx] = replacement_recipe
                            print(f"[Weekly Menu Modification] Replaced {replace_day} {replace_meal} with {replacement_recipe['name']}")
                            break
        else:
            # Generate new menu from scratch
            suggested_recipes = []
        
        if not suggested_recipes:  # Only generate if not already populated by modification
            for day_idx, day_name in enumerate(day_names):
                # Select recipes for each requested meal on this day
                for meal_type in meal_types:
                    # Check if there's a specific recipe requested for this day/meal
                    specific_recipe = specific_recipe_map.get((day_name, meal_type))
                    
                    if specific_recipe:
                        # Use the specific recipe from conversation memory
                        recipe_dict = {
                            "id": specific_recipe.get('id', 0),
                            "name": specific_recipe.get('name', 'Unknown Recipe'),
                            "description": specific_recipe.get('description', ''),
                            "servings": specific_recipe.get('servings', 4),
                            "total_time_minutes": specific_recipe.get('total_time_minutes', 30),
                            "ingredients": specific_recipe.get('ingredients', []),
                            "steps": specific_recipe.get('steps', []),
                            "source_type": specific_recipe.get('source_type', 'conversation'),
                            "source_ref": specific_recipe.get('source_ref', ''),
                            "tags": specific_recipe.get('tags', [])[:3],
                            "calories": specific_recipe.get('calories'),
                            "protein": specific_recipe.get('protein'),
                            "carbs": specific_recipe.get('carbs'),
                            "fat": specific_recipe.get('fat'),
                            "created_at": specific_recipe.get('created_at', datetime.now().isoformat()),
                            "day_name": day_name,
                            "meal_type": meal_type
                        }
                        print(f"Using specific recipe '{recipe_dict['name']}' for {day_name} {meal_type}")
                    else:
                        # Use RAG search results
                        available = recipes_by_meal.get(meal_type, [])
                        if day_idx < len(available):
                            rec = available[day_idx]
                            
                            recipe_dict = {
                                "id": rec.get('recipe_id', 0),
                                "name": rec.get('name', 'Unknown Recipe'),
                                "servings": int(rec.get('servings', 4)),
                                "total_time_minutes": int(rec.get('time', 30)),
                                "ingredients": [],
                                "steps": [],
                                "source_type": "dataset",
                                "source_ref": rec.get('recipe_id', ''),
                                "tags": rec.get('keywords', [])[:3] if rec.get('keywords') else [],
                                "created_at": datetime.now().isoformat(),
                                "day_name": day_name,
                                "meal_type": meal_type
                            }
                        else:
                            continue  # Skip if no recipe available
                    
                    suggested_recipes.append(recipe_dict)
        
        # Generate dynamic explanation
        total_recipes = len(suggested_recipes)
        dietary_text = f" {', '.join(dietary_restrictions)}" if dietary_restrictions else ""
        
        # Build meal breakdown
        meal_breakdown = []
        for meal_type in meal_types:
            meal_count = len([r for r in suggested_recipes if r.get('meal_type') == meal_type])
            if meal_count > 0:
                meal_breakdown.append(f"- {meal_count} {meal_type} {'option' if meal_count == 1 else 'options'}")
        
        # Build day description
        if len(day_names) == 7:
            day_desc = "the full week"
        elif len(day_names) == 5 and day_names == all_days[:5]:
            day_desc = "weekdays (Monday-Friday)"
        elif len(day_names) == 2 and day_names == all_days[5:]:
            day_desc = "the weekend"
        elif len(day_names) == 1:
            day_desc = day_names[0]
        else:
            day_desc = f"{len(day_names)} days"
        
        reply = f"""I've created a{dietary_text} menu plan for {day_desc}! 

Here are {total_recipes} recipes organized by day and meal:
{chr(10).join(meal_breakdown)}

Each recipe is selected to provide variety and balance. Click on any recipe card below to see the full details, ingredients, and cooking instructions!"""
        
        return {
            "reply": reply,
            "suggested_recipes": suggested_recipes,  # Already dicts with day_name and meal_type
            "weekly_menu": None
        }
        
    except Exception as e:
        print(f"Weekly menu generation failed: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "reply": "I encountered an error generating your weekly menu. Please try again or rephrase your request.",
            "suggested_recipes": [],
            "weekly_menu": None
        }


async def chat_agent_handler(
    db: Session,
    session_id: str,
    message: str,
    image_bytes: bytes = None
) -> Dict:
    """
    Main chat agent entry point with automatic intent detection.
    Tracks conversation history for context continuity (e.g., "what about that recipe", "make it spicier").
    
    Args:
        db: Database session
        session_id: Chat session ID
        message: User message
        image_bytes: Optional image data for food photo analysis
    
    Returns:
        Dict with reply, suggested_recipes, and weekly_menu
    """
    # Initialize conversation memory (simple message tracking)
    memory = ConversationMemory(db, session_id)
    
    # First, analyze conversation context to understand what user is referring to
    context_analysis = await analyze_conversation_context(message, memory)
    
    # Use LLM-based intent detection with conversation context
    image_present = image_bytes is not None
    intent = await detect_user_intent_with_llm(message, memory, image_present, context_analysis)
    
    # Record user message
    memory.record_user_message(message, intent)
    
    print(f"[Chat Agent] LLM detected intent: {intent} for message: '{message[:50]}...'")
    
    # If image is provided, handle image analysis first
    if image_bytes:
        from app.services.image_pipeline import analyze_image_pipeline
        
        try:
            print("[Chat Agent] Processing uploaded image...")
            recipe, nutrition, tags, debug_info = await analyze_image_pipeline(
                db, image_bytes, title=message if message and message.strip() else None
            )
            
            # Convert to response format
            recipe_dict = {
                "id": recipe.id,
                "name": recipe.name,
                "description": recipe.description or "",
                "servings": recipe.servings,
                "total_time_minutes": recipe.total_time_minutes,
                "ingredients": [
                    {
                        "name": ing.name,
                        "quantity": ing.quantity,
                        "unit": ing.unit
                    }
                    for ing in recipe.ingredients
                ],
                "steps": [
                    {
                        "step_number": step.step_number,
                        "instruction": step.instruction
                    }
                    for step in recipe.steps
                ],
                "source_type": "image",
                "source_ref": "uploaded_image",
                "tags": tags[:5],
                "calories": nutrition.per_serving.kcal if nutrition else None,
                "protein": nutrition.per_serving.protein if nutrition else None,
                "carbs": nutrition.per_serving.carbs if nutrition else None,
                "fat": nutrition.per_serving.fat if nutrition else None,
                "created_at": recipe.created_at.isoformat() if recipe.created_at else datetime.now().isoformat()
            }
            
            # Determine what user wants based on LLM-detected intent
            if intent == "nutrition" and nutrition:
                # User specifically asked for nutrition info only
                reply = f"I analyzed your photo and identified: **{recipe.name}**!"
                # Add a flag so frontend knows to show only nutrition
                recipe_dict["show_nutrition_only"] = True
            else:
                # User wants the recipe (ingredients intent)
                reply = f"I analyzed your food photo and identified: **{recipe.name}**! Here's a complete recipe with ingredients and instructions."
                recipe_dict["show_nutrition_only"] = False
            
            result = {
                "reply": reply,
                "suggested_recipes": [recipe_dict],
                "weekly_menu": None
            }
            
            # Record assistant response
            memory.record_assistant_response(result["reply"], [recipe.id], [recipe_dict])
            return result
            
        except Exception as e:
            print(f"[Chat Agent] Image analysis failed: {str(e)}")
            result = {
                "reply": f"Sorry, I couldn't analyze the image. Error: {str(e)}. Please try uploading a clearer photo or describe what you'd like to cook!",
                "suggested_recipes": [],
                "weekly_menu": None
            }
            memory.record_assistant_response(result["reply"], None, None)
            return result
    
    # Handle based on intent, passing memory for history context
    if intent == "url_analysis":
        result = await handle_url_analysis_mode(db, session_id, message, memory)
    elif intent == "modification":
        result = await handle_modification_mode(db, session_id, message, memory)
    elif intent == "ingredients":
        result = await handle_ingredients_mode(db, session_id, message, memory)
    elif intent == "weekly_menu":
        result = await handle_weekly_menu_mode(db, session_id, message, memory)
    else:  # recipe_search
        result = await handle_recipe_search_mode(db, session_id, message, memory)
    
    # Record assistant response with full recipe data for modification context
    recipe_ids = [r.get("id") if isinstance(r, dict) else r.id for r in result.get("suggested_recipes", [])]
    recipes = result.get("suggested_recipes", []) if result.get("suggested_recipes") else None
    memory.record_assistant_response(result["reply"], recipe_ids if recipe_ids else None, recipes)
    
    return result
