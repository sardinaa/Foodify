"""
Prompt loader utility for managing LLM/VLM prompts from JSON files.
Centralized prompt management for easier maintenance and updates.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import logging
from langchain_core.prompts import PromptTemplate

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
    
    def get_prompt_template(self, prompt_key: str, type: str = "llm") -> PromptTemplate:
        """
        Get a LangChain PromptTemplate object for the given key.
        
        Args:
            prompt_key: Key identifying the prompt
            type: Type of prompt file to look in ("llm", "rag", "vlm")
            
        Returns:
            LangChain PromptTemplate object
        """
        if type == "llm":
            config = self.get_llm_prompt(prompt_key)
        elif type == "rag":
            config = self.get_rag_prompt(prompt_key)
        elif type == "vlm":
            config = self.get_vlm_prompt(prompt_key)
        else:
            config = {}
            
        if not config:
            logger.warning(f"Prompt key '{prompt_key}' not found in {type} prompts")
            return PromptTemplate.from_template("")
            
        # Handle "system" + "user_template" pattern
        if "system" in config and "user_template" in config:
            system_prompt = config["system"]
            if isinstance(system_prompt, list):
                system_prompt = "\n".join(system_prompt)
                
            user_template = config["user_template"]
            if isinstance(user_template, list):
                user_template = "\n".join(user_template)
                
            return PromptTemplate.from_template(f"{system_prompt}\n\n{user_template}")
            
        # Handle "template" pattern
        elif "template" in config:
            template = config["template"]
            if isinstance(template, list):
                template = "\n".join(template)
            return PromptTemplate.from_template(template)
            
        # Fallback
        return PromptTemplate.from_template("")
    
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
