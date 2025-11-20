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
            "reply": f"✅ Successfully extracted **{recipe.name}** from the URL!",
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
    from app.core.llm_client import get_llm_client
    
    try:
        rag_service = RecipeRAGService()
        llm = get_llm_client()
        from app.utils.prompt_loader import get_prompt_loader
        
        # Let LLM extract constraints from the user's query using prompt template
        prompt_loader = get_prompt_loader()
        constraint_config = prompt_loader.get_llm_prompt("recipe_constraint_parser")
        system_prompt = "\n".join(constraint_config.get("system", []))
        user_template = "\n".join(constraint_config.get("user_template", []))
        
        constraint_prompt = prompt_loader.format_prompt(
            user_template,
            user_query=message
        )
        
        print(f"[Recipe Search] Constraint prompt: {constraint_prompt[:200]}")
        
        constraint_response = await llm.chat(
            messages=[{"role": "user", "content": constraint_prompt}],
            temperature=0.1,
            system=system_prompt
        )
        
        print(f"[Recipe Search] LLM raw response: {constraint_response[:300]}")
        
        # Parse constraints
        constraints = parse_llm_json(constraint_response, fallback={
            "dietary": [],
            "max_time_minutes": None,
            "max_calories": None
        })
        
        dietary = constraints.get("dietary", [])
        max_time = constraints.get("max_time_minutes")
        max_calories = constraints.get("max_calories")
        
        print(f"[Recipe Search] Extracted constraints - Time: {max_time}, Calories: {max_calories}, Dietary: {dietary}")
        
        # Build metadata filter for time constraint
        metadata_filter = {}
        if max_time:
            metadata_filter["time"] = {"$lte": float(max_time)}
        
        recommendations = await rag_service.get_recipe_recommendations(
            user_query=message,
            db=db,
            dietary_restrictions=dietary if dietary else None,
            max_calories=max_calories,
            n_results=5,
            metadata_filter=metadata_filter if metadata_filter else None
        )
        
        return {
            "reply": recommendations.get('explanation', "Here are some great recipes!"),
            "suggested_recipes": recommendations.get('recipes', [])[:3],
            "weekly_menu": None
        }
    except Exception as e:
        print(f"RAG search failed: {e}")
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
    previous_recipes = get_recipes_from_history(memory)
    
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
    
    # Check if user just wants to see details
    context_analysis = await analyze_conversation_context(message, memory)
    if context_analysis.get("action") == "show_previous":
        return {
            "reply": f"Here's the full recipe for **{previous_recipes[0]['name']}**!",
            "suggested_recipes": previous_recipes,
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
        print(f"Modification failed: {e}")
    
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
        
        print(f"[Weekly Menu] Extracted constraints - Days: {len(day_names)}, Meals: {meal_types}, Time: {max_time}, Calories: {max_calories}, Dietary: {dietary}")
        
        # Build metadata filter for ChromaDB
        metadata_filter = {}
        if max_time:
            metadata_filter["time"] = {"$lte": float(max_time)}
        if max_calories:
            metadata_filter["calories"] = {"$lte": float(max_calories)}
        
        # Get recipes for each meal type
        suggested_recipes = []
        for meal_type in meal_types:
            query = f"{meal_type} recipes"
            if dietary:
                query += f" {' '.join(dietary)}"
            if other_prefs:
                query += f" {other_prefs}"
            
            recipes = await rag_service.search_recipes_with_full_context(
                query=query,
                db=db,
                metadata_filter=metadata_filter if metadata_filter else None,
                n_results=len(day_names)
            )
            
            # Assign to days
            for idx, day in enumerate(day_names):
                if idx < len(recipes):
                    recipe = recipes[idx].copy()
                    recipe["day_name"] = day
                    recipe["meal_type"] = meal_type
                    suggested_recipes.append(recipe)
        
        # Build response message
        dietary_text = f" {', '.join(dietary)}" if dietary else ""
        day_desc = f"{len(day_names)} days" if len(day_names) != 7 else "the week"
        time_text = f" (under {max_time} min)" if max_time else ""
        cal_text = f" (max {max_calories} cal)" if max_calories else ""
        
        return {
            "reply": f"🍽️ Here's your{dietary_text} menu plan for **{day_desc}**{time_text}{cal_text} with **{len(suggested_recipes)} recipes**!",
            "suggested_recipes": suggested_recipes,
            "weekly_menu": None
        }
        
    except Exception as e:
        print(f"Menu generation failed: {e}")
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
    memory.record_user_message(message, intent)
    
    print(f"[Chat Agent] Intent: {intent} for message: '{message[:50]}...'")
    
    # Handle image analysis
    if image_bytes:
        from app.services.image_pipeline import analyze_image_pipeline
        
        try:
            recipe, nutrition, tags, _ = await analyze_image_pipeline(db, image_bytes, title=message)
            recipe_dict = format_recipe_dict(recipe, nutrition, tags)
            recipe_dict["source_type"] = "image"
            recipe_dict["show_nutrition_only"] = (intent == "nutrition")
            
            result = {
                "reply": f"🔍 Identified: **{recipe.name}**!\n\nHere's the {'nutrition information' if intent == 'nutrition' else 'full recipe'}.",
                "suggested_recipes": [recipe_dict],
                "weekly_menu": None
            }
            memory.record_assistant_response(result["reply"], [recipe.id], [recipe_dict])
            return result
        except Exception as e:
            print(f"Image analysis failed: {e}")
            return create_error_response(f"Couldn't analyze the image: {str(e)}")
    
    # Dispatch to handler
    result = await dispatch_intent(intent, db, session_id, message, memory)
    
    # Record response
    recipe_ids = [r.get("id") for r in result.get("suggested_recipes", [])]
    recipes = result.get("suggested_recipes")
    memory.record_assistant_response(result["reply"], recipe_ids or None, recipes)
    
    return result
