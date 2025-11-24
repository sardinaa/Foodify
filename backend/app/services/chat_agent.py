"""
Simplified chat agent for conversational recipe assistance.
Includes RAG helper functions for recipe recommendations.
"""
from typing import Dict, Optional, List, Any
from sqlalchemy.orm import Session
import logging
import json
import random

from app.services.conversation_memory import ConversationMemory
from app.services.chat.intent import analyze_conversation_context, detect_user_intent_with_llm
from app.services.chat.router import dispatch_intent
from app.services.chat.helpers import format_recipe_dict, create_error_response
from app.core.constants import MenuConstants, LimitsConstants
from app.utils.json_parser import parse_llm_json, safe_json_parse
from app.core.logging import get_logger
from app.services.recipe_vectorstore import get_vector_store
from app.core.llm_client import get_llm_client
from app.core.config import get_settings
from app.utils.prompt_loader import get_prompt_loader
from app.db.crud_recipes import get_recipe
from app.db.schema import Recipe

logger = get_logger("chat_agent")

# Initialize shared resources
_settings = get_settings()
_vector_store = get_vector_store(
    persist_directory=_settings.vector_store_path,
    embedding_model=_settings.embedding_model
)
_llm_client = get_llm_client()
_prompt_loader = get_prompt_loader()


# ============================================================================
# RAG HELPER FUNCTIONS
# ============================================================================

def _model_to_dict(recipe_model) -> Dict[str, Any]:
    """Convert recipe model from SQL database to dictionary."""
    return Recipe.model_validate(recipe_model).model_dump(mode="json")


def _metadata_to_dict(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Convert ChromaDB metadata to dictionary with full nutrition and tags."""
    # Parse JSON fields from ChromaDB metadata - handle both string and list formats
    ingredients = metadata.get('ingredients', [])
    if isinstance(ingredients, str):
        ingredients = safe_json_parse(ingredients, fallback=[])
    elif not isinstance(ingredients, list):
        ingredients = []
    
    instructions = metadata.get('instructions', [])
    if isinstance(instructions, str):
        instructions = safe_json_parse(instructions, fallback=[])
    elif not isinstance(instructions, list):
        instructions = []
    
    keywords = metadata.get('keywords', [])
    if isinstance(keywords, str):
        keywords = safe_json_parse(keywords, fallback=[])
    elif not isinstance(keywords, list):
        keywords = []
    
    # Parse other label fields - handle both string and list formats
    diet_labels = metadata.get('diet_labels', [])
    if isinstance(diet_labels, str):
        diet_labels = safe_json_parse(diet_labels, fallback=[])
    elif not isinstance(diet_labels, list):
        diet_labels = []
    
    health_labels = metadata.get('health_labels', [])
    if isinstance(health_labels, str):
        health_labels = safe_json_parse(health_labels, fallback=[])
    elif not isinstance(health_labels, list):
        health_labels = []
    
    dish_type = metadata.get('dish_type', [])
    if isinstance(dish_type, str):
        dish_type = safe_json_parse(dish_type, fallback=[])
    elif not isinstance(dish_type, list):
        dish_type = []
    
    cuisine_type = metadata.get('cuisine_type', [])
    if isinstance(cuisine_type, str):
        cuisine_type = safe_json_parse(cuisine_type, fallback=[])
    elif not isinstance(cuisine_type, list):
        cuisine_type = []
    
    meal_type = metadata.get('meal_type', [])
    if isinstance(meal_type, str):
        meal_type = safe_json_parse(meal_type, fallback=[])
    elif not isinstance(meal_type, list):
        meal_type = []
    
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


async def _extract_constraints(user_query: str) -> Dict[str, Any]:
    """Extract constraints from user query using LLM."""
    try:
        config = _prompt_loader.get_llm_prompt("recipe_constraint_parser")
        system_prompt = "\n".join(config.get("system", []))
        user_template = "\n".join(config.get("user_template", []))
        
        prompt = _prompt_loader.format_prompt(
            user_template,
            user_query=user_query
        )
        
        response = await _llm_client.chat(
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


def _apply_custom_filters(
    recipes: List[Dict[str, Any]],
    dietary_restrictions: Optional[List[str]] = None,
    excluded_ingredients: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Apply custom filters that ChromaDB can't handle (text matching, complex logic)."""
    filtered = []
    
    for recipe in recipes:
        # Quality check: must have ingredients
        ingredients = recipe.get('ingredients', [])
        if isinstance(ingredients, str):
            ingredients = safe_json_parse(ingredients, fallback=[])
        elif not isinstance(ingredients, list):
            ingredients = []
        if not ingredients:
            continue
        
        # Check ingredient exclusions
        if excluded_ingredients:
            ing_text = " ".join([str(i).lower() for i in ingredients])
            if any(excl.lower() in ing_text for excl in excluded_ingredients):
                continue
        
        # Check dietary restrictions
        if dietary_restrictions:
            keywords = recipe.get('keywords', [])
            # Handle both list and JSON string formats
            if isinstance(keywords, str):
                keywords = safe_json_parse(keywords, fallback=[])
            elif not isinstance(keywords, list):
                keywords = []
            keywords_lower = [k.lower() for k in keywords]
            
            matches = True
            for restriction in dietary_restrictions:
                restriction_lower = restriction.lower()
                if restriction_lower not in keywords_lower:
                    # Special handling for vegetarian/vegan
                    if "vegetarian" in restriction_lower or "vegan" in restriction_lower:
                        meat_keywords = ["chicken", "beef", "pork", "meat", "fish", "seafood"]
                        if any(mk in keywords_lower for mk in meat_keywords):
                            matches = False
                            break
            
            if not matches:
                continue
        
        filtered.append(recipe)
    
    return filtered


async def _generate_simple_explanation(
    user_query: str,
    recipes: List[Dict[str, Any]],
    system_instruction: Optional[str] = None,
    constraints: Optional[Dict[str, Any]] = None
) -> str:
    """Generate a simple conversational explanation using LLM with minimal context."""
    if not recipes:
        return "I couldn't find any recipes matching your criteria. Try adjusting your constraints?"
    
    # Build minimal recipe summary
    recipe_summaries = []
    for i, r in enumerate(recipes, 1):
        keywords = r.get('keywords', [])
        if isinstance(keywords, str):
            keywords = safe_json_parse(keywords, fallback=[])
        elif not isinstance(keywords, list):
            keywords = []
        recipe_summaries.append(
            f"{i}. {r['name']} ("
            f"{r.get('calories', 0):.0f} cal, {', '.join(keywords[:3]) if keywords else 'no tags'})"
        )
    
    # Build constraint summary
    constraint_parts = []
    if constraints:
        if constraints.get('dietary'):
            constraint_parts.append(f"dietary: {', '.join(constraints['dietary'])}")
        if constraints.get('max_calories'):
            constraint_parts.append(f"max {constraints['max_calories']} cal")
        if constraints.get('excluded_ingredients'):
            constraint_parts.append(f"without {', '.join(constraints['excluded_ingredients'])}")
    
    constraint_text = f" ({'; '.join(constraint_parts)})" if constraint_parts else ""
    
    # Simple prompt
    prompt = f"""User asked: "{user_query}"{constraint_text}

Found recipes:
{chr(10).join(recipe_summaries)}

{f'Note: {system_instruction}' if system_instruction else ''}

Provide a friendly 2-3 sentence recommendation explaining why these recipes match and which might be best."""
    
    try:
        return await _llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
    except Exception as e:
        logger.error(f"LLM explanation failed: {e}")
        return f"I found {len(recipes)} great recipes for you! Check out the details below."


async def _get_recipe_recommendations(
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
    Get recipe recommendations using streamlined RAG pipeline.
    
    Steps:
    1. Semantic search via ChromaDB with nutritional filters
    2. Apply custom filters (dietary, ingredients)
    3. Convert to recipe dicts
    4. Generate LLM explanation
    """
    logger.info(f"Getting recommendations for query: {user_query}")
    
    # Build filter for ChromaDB - let database do the heavy lifting
    filter_dict = metadata_filter.copy() if metadata_filter else {}
    if max_calories and "calories" not in filter_dict:
        filter_dict["calories"] = {"$lte": max_calories}
    if min_protein and "protein" not in filter_dict:
        filter_dict["protein"] = {"$gte": min_protein}
    if max_carbs and "carbs" not in filter_dict:
        filter_dict["carbs"] = {"$lte": max_carbs}
    if max_fat and "fat" not in filter_dict:
        filter_dict["fat"] = {"$lte": max_fat}
    
    # Semantic search with nutritional pre-filtering
    candidate_count = n_results * 2  # Small buffer for custom filtering
    recipes_metadata = _vector_store.search_recipes(
        query=user_query,  # Use user query directly - no transformation needed
        n_results=candidate_count,
        filter_dict=filter_dict if filter_dict else None
    )
    
    logger.info(f"Found {len(recipes_metadata)} recipes from ChromaDB")
    
    # Apply custom filters (dietary, ingredients)
    filtered_recipes = _apply_custom_filters(
        recipes_metadata,
        dietary_restrictions=dietary_restrictions,
        excluded_ingredients=excluded_ingredients
    )
    
    logger.info(f"After custom filtering: {len(filtered_recipes)} recipes")
    
    # Convert to full recipe dicts (use ChromaDB metadata directly - no SQL augmentation)
    recipes = [_metadata_to_dict(r) for r in filtered_recipes[:n_results]]
    
    # Generate LLM explanation
    explanation = await _generate_simple_explanation(
        user_query=user_query,
        recipes=recipes,
        system_instruction=system_instruction,
        constraints={
            "dietary": dietary_restrictions,
            "max_calories": max_calories,
            "min_protein": min_protein,
            "max_carbs": max_carbs,
            "max_fat": max_fat,
            "excluded_ingredients": excluded_ingredients
        }
    )
    
    return {
        "query": user_query,
        "recipes": recipes,
        "explanation": explanation,
        "total_results": len(recipes)
    }


# ============================================================================
# CHAT HANDLERS
# ============================================================================


async def handle_recipe_search_mode(
    db: Session,
    session_id: str,
    message: str,
    memory: Optional[ConversationMemory] = None
) -> Dict:
    """Search recipes using full RAG with LLM-extracted constraints."""
    try:
        # Use local constraint extraction
        constraints = await _extract_constraints(message)
        
        logger.debug(f"[Recipe Search] Extracted constraints: {constraints}")
        
        # Extract specific constraints
        dietary = constraints.get("dietary", [])
        max_calories = constraints.get("max_calories")
        quantity = constraints.get("quantity")
        min_protein = constraints.get("min_protein")
        max_carbs = constraints.get("max_carbs")
        max_fat = constraints.get("max_fat")
        included_ingredients = constraints.get("included_ingredients", [])
        excluded_ingredients = constraints.get("excluded_ingredients", [])
        
        logger.info(f"[Recipe Search] Extracted constraints - Calories: {max_calories}, Dietary: {dietary}, Quantity: {quantity}, Protein: {min_protein}, Carbs: {max_carbs}, Fat: {max_fat}, Inc: {included_ingredients}, Exc: {excluded_ingredients}")
        
        # Determine number of results
        # Default to 3 if not specified, but respect user's request
        n_results = 3
        system_instruction = None
        
        if quantity and isinstance(quantity, int) and quantity > 0:
            if quantity > 10:
                n_results = 10
                system_instruction = f"The user asked for {quantity} recipes, but the system is limited to displaying 10. Explicitly mention that you are showing the top 10 matches out of the requested {quantity}."
            else:
                n_results = quantity
                system_instruction = f"The user explicitly asked for {quantity} recipes. I have provided exactly {quantity} recipes. Ensure your response reflects this count."
        else:
             system_instruction = f"The user did not specify a quantity, so I have provided {n_results} top recommendations."
        
        # Build metadata filter
        metadata_filter = {}
        
        recommendations = await _get_recipe_recommendations(
            user_query=message,
            db=db,
            dietary_restrictions=dietary if dietary else None,
            max_calories=max_calories,
            n_results=n_results,
            metadata_filter=metadata_filter if metadata_filter else None,
            system_instruction=system_instruction,
            min_protein=min_protein,
            max_carbs=max_carbs,
            max_fat=max_fat,
            included_ingredients=included_ingredients,
            excluded_ingredients=excluded_ingredients
        )
        
        reply = recommendations.get('explanation', "Here are some great recipes!")
            
        return {
            "reply": reply,
            "suggested_recipes": recommendations.get('recipes', []),
            "weekly_menu": None
        }
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return create_error_response(
            "I couldn't find recipes matching your request. Try rephrasing?"
        )


async def handle_modification_mode(
    db: Session,
    session_id: str,
    message: str,
    memory: Optional[ConversationMemory] = None
) -> Dict:
    """Modify recipes using LLM with conversation context."""
    from app.services.chat.helpers import get_recipes_from_history
    from datetime import datetime
    
    # Get recipes from recent conversation
    previous_recipes = await get_recipes_from_history(memory)
    
    # If no recipes, try simple search fallback
    if not previous_recipes:
        try:
            results = await _get_recipe_recommendations(
                user_query=message, db=db, n_results=3
            )
            if results.get('recipes'):
                return {
                    "reply": "Which recipe would you like to modify? Please specify:",
                    "suggested_recipes": results['recipes'],
                    "weekly_menu": None
                }
        except:
            pass
        
        return create_error_response(
            "I don't see any recipes to modify. Please search for a recipe first!"
        )
    
    # Check if user just wants to see details or ask a question about the recipe
    context_analysis = await analyze_conversation_context(message, memory)
    action = context_analysis.get("action")
    
    if action in ["show_recipe", "answer_question", "show_previous"]:
        # Use LLM to generate a specific answer based on the recipe
        qa_config = _prompt_loader.get_llm_prompt("recipe_qa")
        system_prompt = "\n".join(qa_config.get("system", []))
        user_template = "\n".join(qa_config.get("user_template", []))
        
        qa_prompt = _prompt_loader.format_prompt(
            user_template,
            recipe_context=json.dumps(previous_recipes[0], indent=2),
            user_message=message
        )
        
        try:
            qa_response = await _llm_client.chat(
                messages=[{"role": "user", "content": qa_prompt}],
                temperature=0.3,
                system=system_prompt
            )
            reply_text = qa_response
        except Exception as e:
            logger.error(f"QA generation failed: {e}")
            reply_text = f"Here's the full recipe for **{previous_recipes[0]['name']}**!"

        # Only show recipe card if explicitly requested (show_recipe)
        # For specific questions (answer_question), do NOT show the card again
        # show_previous is legacy/fallback - we'll treat it as showing the card to be safe, 
        # but the prompt should now distinguish them.
        show_card = action == "show_recipe" or action == "show_previous"

        return {
            "reply": reply_text,
            "suggested_recipes": previous_recipes if show_card else [],
            "weekly_menu": None
        }
    
    # Modify recipe using LLM with prompt template
    modification_config = _prompt_loader.get_llm_prompt("recipe_modification")
    system_prompt = "\n".join(modification_config.get("system", []))
    user_template = "\n".join(modification_config.get("user_template", []))
    
    user_prompt = _prompt_loader.format_prompt(
        user_template,
        original_recipe=json.dumps(previous_recipes[0], indent=2),
        user_request=message
    )
    
    try:
        response = await _llm_client.chat(
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.3,
            system=system_prompt
        )
        
        # Parse JSON using robust parser
        result = parse_llm_json(response)
        
        modified_recipe = {
            "id": f"modified_{session_id}",
            "name": result.get("name", "Modified Recipe"),
            "description": result.get("description", ""),
            "servings": result.get("servings", 4),
            "ingredients": result.get("ingredients", []),
            "steps": result.get("steps", []),
            "source_type": "modified",
            "source_ref": f"session_{session_id}",
            "tags": ["modified"],
            "created_at": datetime.now().isoformat()
        }
        
        return {
            "reply": result.get("explanation", "Recipe modified!"),
            "suggested_recipes": [modified_recipe],
            "weekly_menu": None
        }
    except Exception as e:
        logger.error(f"Modification failed: {e}")
    
    return create_error_response("I had trouble modifying the recipe. Please be more specific?")


async def handle_weekly_menu_mode(
    db: Session,
    session_id: str,
    message: str,
    memory: Optional[ConversationMemory] = None
) -> Dict:
    """Generate weekly menu using RAG."""
    from app.services.chat.helpers import get_recipes_from_history
    
    try:
        # Get conversation history for context
        history_context = ""
        if memory:
            history = await memory.get_conversation_history(limit=4)
            history_lines = []
            for msg in history:
                role = "User" if msg["role"] == "user" else "Assistant"
                content = msg["content"][:200]
                history_lines.append(f"{role}: {content}")
            history_context = "\n".join(history_lines)

        # Parse constraints using LLM with prompt template
        constraint_config = _prompt_loader.get_llm_prompt("menu_constraint_parser")
        system_prompt = "\n".join(constraint_config.get("system", []))
        user_template = "\n".join(constraint_config.get("user_template", []))
        
        parse_prompt = _prompt_loader.format_prompt(
            user_template,
            conversation_history=history_context,
            user_message=message
        )
        
        llm_response = await _llm_client.chat(
            messages=[{"role": "user", "content": parse_prompt}],
            temperature=0.1,
            system=system_prompt
        )
        
        # Parse response using robust JSON parser
        fallback_constraints = {
            "days": MenuConstants.DEFAULT_DAYS,
            "meals": MenuConstants.DEFAULT_MEALS,
            "dietary": [],
            "max_calories": None,
            "other_preferences": ""
        }
        constraints = parse_llm_json(llm_response, fallback=fallback_constraints)
        
        day_names = constraints.get("days", MenuConstants.DEFAULT_DAYS)
        meal_types = constraints.get("meals", MenuConstants.DEFAULT_MEALS)
        dietary = constraints.get("dietary", [])
        max_calories = constraints.get("max_calories")
        other_prefs = constraints.get("other_preferences", "")
        use_history = constraints.get("use_history_recipes", False)
        explicit_changes = constraints.get("explicit_changes", [])
        
        logger.info(f"[Weekly Menu] Extracted constraints - Days: {len(day_names)}, Meals: {meal_types}, Calories: {max_calories}, Dietary: {dietary}, Use History: {use_history}, Changes: {len(explicit_changes)}")
        
        # Check if user wants to use previous recipes
        previous_recipes = []
        
        if use_history:
            previous_recipes = await get_recipes_from_history(memory, limit=10)
            logger.info(f"[Weekly Menu] Found {len(previous_recipes)} previous recipes to include")

        # Build metadata filter for ChromaDB
        metadata_filter = {}
        if max_calories:
            metadata_filter["calories"] = {"$lte": float(max_calories)}
        
        # Organize previous recipes for intelligent reuse
        precise_matches = {}  # (day, meal_type) -> recipe
        available_previous = [] # list of recipes
        used_previous_ids = set()
        
        if previous_recipes:
            for r in previous_recipes:
                d = r.get("day_name")
                m = r.get("meal_type")
                if d and m:
                    precise_matches[(d, m)] = r
                available_previous.append(r)

        suggested_recipes = []
        
        for meal_type in meal_types:
            # Identify which days need a recipe for this meal_type
            days_needing_recipe = []
            current_meal_recipes_map = {} # day -> recipe
            
            for day in day_names:
                # 0. Check for explicit changes FIRST
                explicit_change = next((c for c in explicit_changes if c.get("day") == day and c.get("meal") == meal_type), None)
                
                if explicit_change:
                    # Fetch specific recipe for this slot
                    change_query = f"{explicit_change.get('request')} recipe"
                    logger.info(f"[Weekly Menu] Processing explicit change for {day} {meal_type}: {change_query}")
                    
                    change_result = await _get_recipe_recommendations(
                        user_query=change_query,
                        db=db,
                        dietary_restrictions=dietary if dietary else None,
                        max_calories=max_calories,
                        n_results=1,
                        metadata_filter=metadata_filter if metadata_filter else None
                    )
                    if change_result.get('recipes'):
                        r = change_result['recipes'][0]
                        current_meal_recipes_map[day] = r
                        used_previous_ids.add(r.get("id"))
                    else:
                        # Fallback if search fails
                        days_needing_recipe.append(day)
                        
                # 1. Try precise match (Same Day, Same Meal) - ONLY if not explicitly changed
                elif (day, meal_type) in precise_matches:
                    r = precise_matches[(day, meal_type)]
                    current_meal_recipes_map[day] = r
                    used_previous_ids.add(r.get("id"))
                else:
                    days_needing_recipe.append(day)
            
            # 2. For days without precise match, try to fill with available previous recipes of same meal_type
            # This handles cases where days shifted or we just want to reuse "Lunch" recipes
            remaining_days = []
            for day in days_needing_recipe:
                found = None
                for r in available_previous:
                    # Check if not used AND matches meal type
                    # We use str(id) for comparison to be safe
                    if str(r.get("id")) not in [str(uid) for uid in used_previous_ids] and r.get("meal_type") == meal_type:
                        found = r
                        break
                
                if found:
                    current_meal_recipes_map[day] = found
                    used_previous_ids.add(found.get("id"))
                else:
                    remaining_days.append(day)
            
            # 3. Fetch new recipes for remaining slots
            if remaining_days:
                query = f"{meal_type} recipes"
                if dietary:
                    query += f" {' '.join(dietary)}"
                if other_prefs:
                    query += f" {other_prefs}"
                
                new_recipes_result = await _get_recipe_recommendations(
                    user_query=query,
                    db=db,
                    dietary_restrictions=dietary if dietary else None,
                    max_calories=max_calories,
                    n_results=len(remaining_days),
                    metadata_filter=metadata_filter if metadata_filter else None
                )
                new_recipes = new_recipes_result.get('recipes', [])
                
                for i, day in enumerate(remaining_days):
                    if i < len(new_recipes):
                        current_meal_recipes_map[day] = new_recipes[i]
            
            # Assign to final list
            for day in day_names:
                if day in current_meal_recipes_map:
                    recipe = current_meal_recipes_map[day].copy()
                    recipe["day_name"] = day
                    recipe["meal_type"] = meal_type
                    suggested_recipes.append(recipe)
        
        # Build response message
        dietary_text = f" {', '.join(dietary)}" if dietary else ""
        day_desc = f"{len(day_names)} days" if len(day_names) != 7 else "the week"
        cal_text = f" (max {max_calories} cal)" if max_calories else ""
        
        return {
            "reply": f"Here's your{dietary_text} menu plan for **{day_desc}**{cal_text} with **{len(suggested_recipes)} recipes**!",
            "suggested_recipes": suggested_recipes,
            "weekly_menu": None
        }
        
    except Exception as e:
        logger.error(f"Menu generation failed: {e}")
        return create_error_response("I couldn't generate your menu. Please try again!")


async def chat_agent_handler(
    db: Session,
    session_id: str,
    message: str
) -> Dict:
    """Main chat agent entry point with intent detection."""
    memory = ConversationMemory(session_id)
    
    # Analyze context and detect intent
    context_analysis = await analyze_conversation_context(message, memory)
    intent = await detect_user_intent_with_llm(message, memory, False, context_analysis)
    await memory.record_user_message(message, intent)
    
    logger.info(f"[Chat Agent] Intent: {intent} for message: '{message[:50]}...'")
    
    # Dispatch to handler
    result = await dispatch_intent(intent, db, session_id, message, memory)
    
    # Record response
    recipe_ids = [r.get("id") for r in result.get("suggested_recipes", [])]
    recipes = result.get("suggested_recipes")
    await memory.record_assistant_response(result["reply"], recipe_ids or None, recipes)
    
    return result
