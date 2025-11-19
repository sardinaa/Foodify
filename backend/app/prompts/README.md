# Prompt Management System

This directory contains all LLM/VLM prompts used in the Foodify application, separated from code for easier maintenance and updates.

## Structure

```
prompts/
├── llm_prompts.json      # Text-based LLM prompts
├── vlm_prompts.json      # Vision-Language Model prompts
└── rag_prompts.json      # RAG (Retrieval-Augmented Generation) prompts
```

## Usage

### Loading Prompts in Code

```python
from app.utils.prompt_loader import get_prompt_loader

# Get the prompt loader instance
loader = get_prompt_loader()

# Load a specific prompt
prompt_config = loader.get_llm_prompt("recipe_extraction")
system_prompt = prompt_config.get("system")
user_template = prompt_config.get("user_template")

# Format a prompt with variables
formatted = loader.format_prompt(
    user_template,
    raw_text="Recipe content here..."
)
```

## Prompt Files

### llm_prompts.json

Contains prompts for text-based language model operations:

- **recipe_extraction**: Extract structured recipe data from raw text
- **dish_normalization**: Generate canonical dish names and tags
- **ingredients_to_recipes**: Suggest recipes based on available ingredients
- **weekly_menu_planning**: Create weekly meal plans with constraints

### vlm_prompts.json

Contains prompts for vision-language model operations:

- **dish_description**: Analyze food images and extract dish information

### rag_prompts.json

Contains prompts for RAG-based recipe recommendations:

- **recipe_recommendations**: Main template for generating personalized recommendations
- **recipe_context_item**: Template for formatting individual recipe items
- **constraints**: Templates for dietary restrictions and calorie constraints

## Editing Prompts

1. Open the appropriate JSON file
2. Locate the prompt you want to modify
3. Edit the template or prompt text
4. Save the file
5. Restart the application (prompts are cached on load)

### Template Variables

Templates use Python's `.format()` syntax with curly braces:

```json
{
  "template": "Hello {name}, you have {count} items."
}
```

In code, provide the variables:

```python
formatted = loader.format_prompt(template, name="Chef", count=5)
# Result: "Hello Chef, you have 5 items."
```

## Benefits

- **Centralized Management**: All prompts in one place
- **Easy Updates**: Modify prompts without touching code
- **Version Control**: Track prompt changes in Git
- **A/B Testing**: Easy to test different prompt variations
- **Multi-language Support**: Easier to maintain translations
- **Collaboration**: Non-developers can update prompts

## Testing

Run the test script to verify prompts load correctly:

```bash
cd backend
python3 test_prompts.py
```

## Best Practices

1. **Keep prompts concise**: Longer prompts may not always be better
2. **Test changes**: Always test prompt modifications with real data
3. **Document variables**: Comment what variables are expected in templates
4. **Version important prompts**: Consider keeping backup versions
5. **Use consistent formatting**: Maintain similar structure across prompts

## Cache Management

The prompt loader caches loaded JSON files for performance. To clear the cache:

```python
loader = get_prompt_loader()
loader.clear_cache()  # Force reload from files
```

This is useful during development when frequently modifying prompts.
