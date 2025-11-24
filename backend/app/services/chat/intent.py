"""Intent detection helpers for the chat agent."""

from __future__ import annotations

import json
from typing import Dict, Optional

from app.core.llm_client import get_llm_client
from app.services.conversation_memory import ConversationMemory
from app.utils.prompt_loader import get_prompt_loader
from app.core.logging import get_logger

logger = get_logger("services.chat.intent")


async def analyze_conversation_context(
    message: str,
    memory: Optional[ConversationMemory] = None,
) -> Dict:
    """Use LLM to analyze conversation context and referenced items."""
    llm = get_llm_client()
    prompt_loader = get_prompt_loader()
    conversation_history = "(No previous conversation)"
    previous_recipes = []

    if memory:
        history = await memory.get_conversation_history(limit=8)
        if history:
            history_lines = []
            for msg in history:
                role = "User" if msg["role"] == "user" else "Assistant"
                content = msg["content"][:300]
                history_lines.append(f"{role}: {content}")
                if msg["role"] == "assistant" and "recipes" in msg:
                    previous_recipes.extend(msg["recipes"])
            conversation_history = "\n".join(history_lines)

    context_config = prompt_loader.get_llm_prompt("context_understanding")
    system_prompt = "\n".join(context_config.get("system", []))
    user_template = "\n".join(context_config.get("user_template", []))

    user_prompt = prompt_loader.format_prompt(
        user_template,
        conversation_history=conversation_history,
        user_message=message,
    )

    response = await llm.chat(
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.1,
        system=system_prompt,
    )

    try:
        cleaned_response = response.strip()
        if cleaned_response.startswith("```"):
            lines = cleaned_response.split("\n")
            cleaned_response = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned_response
        cleaned_response = cleaned_response.replace("{{", "{").replace("}}", "}")
        json_start = cleaned_response.find("{")
        json_end = cleaned_response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = cleaned_response[json_start:json_end]
            context_analysis = json.loads(json_str)

            logger.debug(
                f"[Context Analysis] Action: {context_analysis.get('action')}, Items: "
                f"{len(context_analysis.get('referenced_items', []))}"
            )

            for item in context_analysis.get("referenced_items", []):
                item_name = item.get("name", "").lower()
                logger.debug(f"[Context Analysis] Looking for recipe matching: {item_name}")
                for prev_recipe in previous_recipes:
                    prev_name = prev_recipe.get("name", "").lower()
                    if (
                        item_name in prev_name
                        or prev_name in item_name
                        or any(word in prev_name for word in item_name.split() if len(word) > 3)
                    ):
                        item["matched_recipe"] = prev_recipe
                        logger.debug(
                            f"[Context Analysis] Matched '{item_name}' to '{prev_recipe.get('name')}'"
                        )
                        break

            return context_analysis
    except Exception as exc:
        logger.warning(f"Failed to parse context analysis: {exc}")
        logger.debug(f"Raw response was: {response[:200]}")

    message_lower = message.lower()
    menu_modification_words = ["change", "replace", "swap", "modify", "remove", "update"]
    day_words = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    meal_words = ["breakfast", "lunch", "dinner"]

    has_menu_modification = any(word in message_lower for word in menu_modification_words)
    has_day_reference = any(word in message_lower for word in day_words)
    has_meal_reference = any(word in message_lower for word in meal_words)
    is_previous_menu = previous_recipes and len(previous_recipes) > 1 and all(
        r.get("day_name") for r in previous_recipes
    )

    if has_menu_modification and (has_day_reference or has_meal_reference) and is_previous_menu:
        logger.info("[Context Analysis] Fallback: Detected menu modification request")
        return {
            "action": "modify_menu",
            "referenced_items": [
                {
                    "type": "menu",
                    "name": "current menu",
                    "context": message,
                }
            ],
        }

    reference_words = ["this", "it", "that", "the recipe", "include it", "add it", "use it"]
    if any(word in message_lower for word in reference_words) and previous_recipes:
        logger.info("[Context Analysis] Fallback: Detected reference word, using most recent recipe")
        return {
            "action": "include_in_new",
            "referenced_items": [
                {
                    "type": "recipe",
                    "name": previous_recipes[-1].get("name", ""),
                    "context": message,
                    "matched_recipe": previous_recipes[-1],
                }
            ],
        }

    return {"action": "new_request", "referenced_items": []}


async def detect_user_intent_with_llm(
    message: str,
    memory: Optional[ConversationMemory] = None,
    image_present: bool = False,
    context_analysis: Optional[Dict] = None,
) -> str:
    """Use LLM to classify intent using conversation context."""
    prompt_loader = get_prompt_loader()

    if context_analysis:
        action = context_analysis.get("action")
        if action in {"show_previous", "modify_previous"}:
            return "modification"
        if action == "modify_menu":
            return "weekly_menu"
        if action == "include_in_new":
            message_lower = message.lower()
            day_names = [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ]
            if "menu" in message_lower or "plan" in message_lower or any(
                day in message_lower for day in day_names
            ):
                return "weekly_menu"

    history_context = "(No previous conversation)"
    if memory:
        history = await memory.get_conversation_history(limit=6)
        if history:
            history_lines = []
            for msg in history[-4:]:
                role = "User" if msg["role"] == "user" else "Assistant"
                content = msg["content"][:150]
                history_lines.append(f"{role}: {content}")
            history_context = "\n".join(history_lines)

    image_context = "Note: User has attached an image." if image_present else ""

    # Use new structured intent classification
    intent_config = prompt_loader.get_llm_prompt("intent_classification_json")
    system_prompt = "\n".join(intent_config.get("system", []))
    user_template = "\n".join(intent_config.get("user_template", []))

    user_prompt = prompt_loader.format_prompt(
        user_template,
        history_context=history_context,
        image_context=image_context,
        user_message=message,
    )

    llm = get_llm_client()
    response = await llm.chat(
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.1,
        system=system_prompt,
    )

    try:
        # Parse JSON response
        from app.utils.json_parser import parse_llm_json
        result = parse_llm_json(response)
        intent = result.get("intent", "recipe_search").lower()
        confidence = result.get("confidence", 0.0)
        logger.info(f"[Intent Detection] Intent: {intent}, Confidence: {confidence}, Reason: {result.get('reasoning')}")
        
        valid_intents = [
            "url_analysis",
            "weekly_menu",
            "modification",
            "nutrition",
            "ingredients",
            "recipe_search",
        ]
        
        if intent in valid_intents:
            return intent
            
    except Exception as e:
        logger.error(f"[Intent Detection] Failed to parse JSON: {e}. Fallback to text analysis.")

    # Fallback to simple text matching if JSON parsing fails
    intent = response.strip().lower()
    valid_intents = [
        "url_analysis",
        "weekly_menu",
        "modification",
        "nutrition",
        "ingredients",
        "recipe_search",
    ]
    for valid in valid_intents:
        if valid in intent:
            return valid

    return "recipe_search"
