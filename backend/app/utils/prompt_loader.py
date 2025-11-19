"""
Prompt loader utility for managing LLM/VLM prompts from JSON files.
Centralized prompt management for easier maintenance and updates.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PromptLoader:
    """Loads and manages prompts from JSON files."""
    
    def __init__(self):
        """Initialize the prompt loader."""
        self.prompts_dir = Path(__file__).parent.parent / "prompts"
        self._cache: Dict[str, Dict[str, Any]] = {}
        
    def _load_prompt_file(self, filename: str) -> Dict[str, Any]:
        """
        Load a prompt JSON file.
        
        Args:
            filename: Name of the JSON file (without .json extension)
            
        Returns:
            Dictionary containing prompts
        """
        if filename in self._cache:
            return self._cache[filename]
        
        filepath = self.prompts_dir / f"{filename}.json"
        
        if not filepath.exists():
            logger.error(f"Prompt file not found: {filepath}")
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                prompts = json.load(f)
                self._cache[filename] = prompts
                return prompts
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing prompt file {filepath}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading prompt file {filepath}: {e}")
            return {}
    
    def get_llm_prompt(self, prompt_key: str) -> Dict[str, Any]:
        """
        Get an LLM prompt by key.
        
        Args:
            prompt_key: Key identifying the prompt (e.g., "recipe_extraction")
            
        Returns:
            Dictionary with prompt templates
        """
        prompts = self._load_prompt_file("llm_prompts")
        return prompts.get(prompt_key, {})
    
    def get_vlm_prompt(self, prompt_key: str) -> Dict[str, Any]:
        """
        Get a VLM prompt by key.
        
        Args:
            prompt_key: Key identifying the prompt (e.g., "dish_description")
            
        Returns:
            Dictionary with prompt templates
        """
        prompts = self._load_prompt_file("vlm_prompts")
        return prompts.get(prompt_key, {})
    
    def get_rag_prompt(self, prompt_key: str) -> Dict[str, Any]:
        """
        Get a RAG prompt by key.
        
        Args:
            prompt_key: Key identifying the prompt (e.g., "recipe_recommendations")
            
        Returns:
            Dictionary with prompt templates
        """
        prompts = self._load_prompt_file("rag_prompts")
        return prompts.get(prompt_key, {})
    
    def format_prompt(self, template: Any, **kwargs) -> str:
        """
        Format a prompt template with provided variables.

        Supports both a single string template or a list of string lines. If a list
        is provided it will be joined with newlines before formatting.

        Args:
            template: Prompt template (str or list of str) with placeholders
            **kwargs: Variables to substitute in the template

        Returns:
            Formatted prompt string
        """
        try:
            # If the template is a list of lines, join them with newlines first
            if isinstance(template, list):
                template_str = "\n".join(template)
            else:
                template_str = str(template or "")

            return template_str.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing variable in prompt template: {e}")
            # Return best-effort joined template
            return template_str
        except Exception as e:
            logger.error(f"Error formatting prompt: {e}")
            return template_str
    
    def clear_cache(self):
        """Clear the prompt cache to reload from files."""
        self._cache.clear()


# Global instance
_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Get or create global PromptLoader instance."""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader
