"""
VLM (Vision-Language Model) client for image understanding.
Model-agnostic interface for analyzing food images.
"""
import base64
from typing import Dict, Optional

from app.core.logging import get_logger
from app.core.base_client import BaseAIClient

logger = get_logger("core.vlm_client")


class VLMClient(BaseAIClient):
    """Client for interacting with Vision-Language Models."""
    
    async def _call_ollama_vision(self, image_bytes: bytes, prompt: str) -> str:
        """Call Ollama vision API using chat endpoint."""
        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        url = f"{self.settings.vlm_base_url}/api/chat"
        
        payload = {
            "model": self.settings.vlm_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64]
                }
            ],
            "stream": False
        }
        
        response_json = await self._make_request(url, payload, log_prefix="VLM Client")
        return response_json["message"]["content"]
    
    async def describe_dish_from_image(
        self,
        image_bytes: bytes,
        title: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Analyze a food image and extract dish information.
        
        Args:
            image_bytes: Image data
            title: Optional user-provided title/hint
        
        Returns:
            Dict with:
                - description: High-level description
                - dish_type: Type of dish
                - guessed_ingredients: List of likely ingredients
                - cuisine: Cuisine type (if identifiable)
        """
        # Load prompts from JSON
        prompt_config = self.prompt_loader.get_vlm_prompt("dish_description")
        template = prompt_config.get("template", "")
        title_line_template = prompt_config.get("title_line_template", "")
        
        # Format title line if provided
        title_line = ""
        if title:
            title_line = self.prompt_loader.format_prompt(title_line_template, title=title)
        
        # Format the main prompt
        prompt = self.prompt_loader.format_prompt(template, title_line=title_line)
        
        response = await self._call_ollama_vision(image_bytes, prompt)
        
        # Parse response
        try:
            import json
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                return {
                    "description": data.get("description", "A food dish"),
                    "dish_type": data.get("dish_type", "unknown"),
                    "guessed_ingredients": data.get("guessed_ingredients", []),
                    "cuisine": data.get("cuisine", "unknown")
                }
        except Exception as e:
            # Fallback
            pass
        
        # If parsing fails, return text response as description
        return {
            "description": response[:500] if response else "A food dish",
            "dish_type": "unknown",
            "guessed_ingredients": [],
            "cuisine": "unknown"
        }


# Global instance
_vlm_client: Optional[VLMClient] = None


def get_vlm_client() -> VLMClient:
    """Get or create global VLMClient instance."""
    global _vlm_client
    if _vlm_client is None:
        _vlm_client = VLMClient()
    return _vlm_client
