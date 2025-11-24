"""
Simplified chat agent for conversational recipe assistance.
Focuses on clean architecture with minimal duplication.
"""
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.services.conversation_memory import ConversationMemory
from app.services.chat.intent import analyze_conversation_context, detect_user_intent_with_llm
from app.services.chat.router import dispatch_intent
from app.services.chat.helpers import format_recipe_dict, create_error_response
from app.core.constants import MenuConstants, LimitsConstants
from app.utils.json_parser import parse_llm_json
from app.core.logging import get_logger

logger = get_logger("chat_agent")


async def handle_url_analysis_mode(
    db: Session,
    session_id: str,
    message: str,
    memory: Optional[ConversationMemory] = None
) -> Dict:
    """Extract recipe from URL."""
    from app.services.url_pipeline import analyze_url_pipeline
    from app.services.chat.helpers import extract_urls
    
    urls = extract_urls(message)
    if not urls:
        return create_error_response(
            "I couldn't find a valid URL in your message. Please provide a complete URL."
        )
    
    try:
        recipe, nutrition, tags = await analyze_url_pipeline(db, urls[0])
        recipe_dict = format_recipe_dict(recipe, nutrition, tags)
        recipe_dict["source_type"] = "url"
        recipe_dict["source_ref"] = urls[0]
        
        return {
            "reply": f"Successfully extracted **{recipe.name}** from the URL!",
            "suggested_recipes": [recipe_dict],
            "weekly_menu": None
        }
    except Exception as e:
        error_hints = {
            "403": "The website is blocking automated access.",
            "Could not extract": "No recipe found at this URL.",
        }
        hint = next((v for k, v in error_hints.items() if k in str(e)), "")
        return create_error_response(
            f"Failed to extract recipe. {hint} Try copying the recipe text directly!"
        )


async def handle_recipe_search_mode(
    db: Session,
    session_id: str,
    message: str,
    memory: Optional[ConversationMemory] = None
) -> Dict:
    """Search recipes using full RAG with LLM-extracted constraints."""
    from app.services.recipe_rag import RecipeRAGService
    
    try:
        rag_service = RecipeRAGService()
        
        # Use the unified constraint extraction from RAG service
        constraints = await rag_service.extract_constraints(message)
        
        logger.debug(f"[Recipe Search] Extracted constraints: {constraints}")
        
        # Extract specific constraints
        dietary = constraints.get("dietary", [])
        max_time = constraints.get("max_time_minutes")
        max_calories = constraints.get("max_calories")
        quantity = constraints.get("quantity")
        min_protein = constraints.get("min_protein")
        max_carbs = constraints.get("max_carbs")
        max_fat = constraints.get("max_fat")
        included_ingredients = constraints.get("included_ingredients", [])
        excluded_ingredients = constraints.get("excluded_ingredients", [])
        
        logger.info(f"[Recipe Search] Extracted constraints - Time: {max_time}, Calories: {max_calories}, Dietary: {dietary}, Quantity: {quantity}, Protein: {min_protein}, Carbs: {max_carbs}, Fat: {max_fat}, Inc: {included_ingredients}, Exc: {excluded_ingredients}")
        
        # Update session preferences if new constraints found
        if dietary or max_time or max_calories:
            from app.db.crud_chat import update_session_preferences
            update_session_preferences(
                db, 
                session_id, 
                dietary_restrictions=dietary if dietary else None,
                time_constraints=max_time
            )
        
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
        
        # Build metadata filter for time constraint
        metadata_filter = {}
        if max_time:
            metadata_filter["time"] = {"$lte": float(max_time)}
        
        recommendations = await rag_service.get_recipe_recommendations(
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
    from app.core.llm_client import get_llm_client
    from app.services.chat.helpers import get_recipes_from_history
    from app.services.recipe_rag import RecipeRAGService
    import json
    from datetime import datetime
    
    # Get recipes from recent conversation
    previous_recipes = await get_recipes_from_history(memory)
    
    # If no recipes, try RAG fallback
    if not previous_recipes:
        try:
            rag_service = RecipeRAGService()
            search_results = await rag_service.search_recipes_with_full_context(
                query=message, db=db, n_results=3
            )
            if search_results:
                return {
                    "reply": "Which recipe would you like to modify? Please specify:",
                    "suggested_recipes": search_results[:3],
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
        llm = get_llm_client()
        from app.utils.prompt_loader import get_prompt_loader
        
        prompt_loader = get_prompt_loader()
        qa_config = prompt_loader.get_llm_prompt("recipe_qa")
        system_prompt = "\n".join(qa_config.get("system", []))
        user_template = "\n".join(qa_config.get("user_template", []))
        
        qa_prompt = prompt_loader.format_prompt(
            user_template,
            recipe_context=json.dumps(previous_recipes[0], indent=2),
            user_message=message
        )
        
        try:
            qa_response = await llm.chat(
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
    llm = get_llm_client()
    from app.utils.prompt_loader import get_prompt_loader
    
    prompt_loader = get_prompt_loader()
    modification_config = prompt_loader.get_llm_prompt("recipe_modification")
    system_prompt = "\n".join(modification_config.get("system", []))
    user_template = "\n".join(modification_config.get("user_template", []))
    
    user_prompt = prompt_loader.format_prompt(
        user_template,
        original_recipe=json.dumps(previous_recipes[0], indent=2),
        user_request=message
    )
    
    try:
        response = await llm.chat(
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
            "total_time_minutes": result.get("total_time_minutes", 30),
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
    from app.services.recipe_rag import RecipeRAGService
    from app.core.llm_client import get_llm_client
    from app.services.chat.helpers import get_recipes_from_history
    import json
    
    try:
        rag_service = RecipeRAGService()
        llm = get_llm_client()
        from app.utils.prompt_loader import get_prompt_loader
        
        # Parse constraints using LLM with prompt template
        prompt_loader = get_prompt_loader()
        constraint_config = prompt_loader.get_llm_prompt("menu_constraint_parser")
        system_prompt = "\n".join(constraint_config.get("system", []))
        user_template = "\n".join(constraint_config.get("user_template", []))
        
        parse_prompt = prompt_loader.format_prompt(
            user_template,
            user_message=message
        )
        
        llm_response = await llm.chat(
            messages=[{"role": "user", "content": parse_prompt}],
            temperature=0.1,
            system=system_prompt
        )
        
        # Parse response using robust JSON parser
        fallback_constraints = {
            "days": MenuConstants.DEFAULT_DAYS,
            "meals": MenuConstants.DEFAULT_MEALS,
            "dietary": [],
            "max_time_minutes": None,
            "max_calories": None,
            "other_preferences": ""
        }
        constraints = parse_llm_json(llm_response, fallback=fallback_constraints)
        
        day_names = constraints.get("days", MenuConstants.DEFAULT_DAYS)
        meal_types = constraints.get("meals", MenuConstants.DEFAULT_MEALS)
        dietary = constraints.get("dietary", [])
        max_time = constraints.get("max_time_minutes")
        max_calories = constraints.get("max_calories")
        other_prefs = constraints.get("other_preferences", "")
        use_history = constraints.get("use_history_recipes", False)
        
        logger.info(f"[Weekly Menu] Extracted constraints - Days: {len(day_names)}, Meals: {meal_types}, Time: {max_time}, Calories: {max_calories}, Dietary: {dietary}, Use History: {use_history}")
        
        # Check if user wants to use previous recipes
        previous_recipes = []
        
        # Use LLM-detected intent to use history, or fallback to keyword check if LLM missed it
        # but user explicitly mentioned "previous" or "history"
        keyword_fallback = any(k in message.lower() for k in ["previous", "history", "these", "all recipes", "the recipes", "those recipes"])
        
        if use_history or keyword_fallback:
            previous_recipes = await get_recipes_from_history(memory, limit=10)
            logger.info(f"[Weekly Menu] Found {len(previous_recipes)} previous recipes to include")

        # Build metadata filter for ChromaDB
        metadata_filter = {}
        if max_time:
            metadata_filter["time"] = {"$lte": float(max_time)}
        if max_calories:
            metadata_filter["calories"] = {"$lte": float(max_calories)}
        
        # Get recipes for each meal type
        suggested_recipes = []
        
        # If we have previous recipes, try to use them first
        used_previous_indices = set()
        
        for meal_type in meal_types:
            query = f"{meal_type} recipes"
            if dietary:
                query += f" {' '.join(dietary)}"
            if other_prefs:
                query += f" {other_prefs}"
            
            # Calculate how many new recipes we need
            needed_count = len(day_names)
            
            # Try to fill with previous recipes first if requested
            current_meal_recipes = []
            if previous_recipes:
                for i, prev_recipe in enumerate(previous_recipes):
                    if i not in used_previous_indices and len(current_meal_recipes) < needed_count:
                        # Simple check if it fits meal type (optional: could use LLM to check)
                        current_meal_recipes.append(prev_recipe)
                        used_previous_indices.add(i)
            
            # If we still need more recipes, fetch from RAG
            remaining_count = needed_count - len(current_meal_recipes)
            if remaining_count > 0:
                new_recipes = await rag_service.get_recipe_recommendations(
                    user_query=query,
                    db=db,
                    dietary_restrictions=dietary if dietary else None,
                    max_calories=max_calories,
                    n_results=remaining_count,
                    metadata_filter=metadata_filter if metadata_filter else None
                )
                current_meal_recipes.extend(new_recipes.get('recipes', []))
            
            # Assign to days
            for idx, day in enumerate(day_names):
                if idx < len(current_meal_recipes):
                    recipe = current_meal_recipes[idx].copy()
                    recipe["day_name"] = day
                    recipe["meal_type"] = meal_type
                    suggested_recipes.append(recipe)
        
        # Build response message
        dietary_text = f" {', '.join(dietary)}" if dietary else ""
        day_desc = f"{len(day_names)} days" if len(day_names) != 7 else "the week"
        time_text = f" (under {max_time} min)" if max_time else ""
        cal_text = f" (max {max_calories} cal)" if max_calories else ""
        
        return {
            "reply": f"Here's your{dietary_text} menu plan for **{day_desc}**{time_text}{cal_text} with **{len(suggested_recipes)} recipes**!",
            "suggested_recipes": suggested_recipes,
            "weekly_menu": None
        }
        
    except Exception as e:
        logger.error(f"Menu generation failed: {e}")
        return create_error_response("I couldn't generate your menu. Please try again!")


async def chat_agent_handler(
    db: Session,
    session_id: str,
    message: str,
    image_bytes: bytes = None
) -> Dict:
    """Main chat agent entry point with intent detection."""
    memory = ConversationMemory(db, session_id)
    
    # Analyze context and detect intent
    context_analysis = await analyze_conversation_context(message, memory)
    intent = await detect_user_intent_with_llm(message, memory, image_bytes is not None, context_analysis)
    await memory.record_user_message(message, intent)
    
    logger.info(f"[Chat Agent] Intent: {intent} for message: '{message[:50]}...'")
    
    # Handle image analysis
    if image_bytes:
        from app.services.image_pipeline import analyze_image_pipeline
        
        try:
            recipe, nutrition, tags, _ = await analyze_image_pipeline(db, image_bytes, title=message)
            recipe_dict = format_recipe_dict(recipe, nutrition, tags)
            recipe_dict["source_type"] = "image"
            recipe_dict["show_nutrition_only"] = (intent == "nutrition")
            
            result = {
                "reply": f"Identified: **{recipe.name}**!\n\nHere's the {'nutrition information' if intent == 'nutrition' else 'full recipe'}.",
                "suggested_recipes": [recipe_dict],
                "weekly_menu": None
            }
            await memory.record_assistant_response(result["reply"], [recipe.id], [recipe_dict])
            return result
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return create_error_response(f"Couldn't analyze the image: {str(e)}")
    
    # Dispatch to handler
    result = await dispatch_intent(intent, db, session_id, message, memory)
    
    # Record response
    recipe_ids = [r.get("id") for r in result.get("suggested_recipes", [])]
    recipes = result.get("suggested_recipes")
    await memory.record_assistant_response(result["reply"], recipe_ids or None, recipes)
    
    return result
