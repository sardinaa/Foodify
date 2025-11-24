"""
Base client for AI operations.
Provides common functionality for LLM and VLM clients.
"""
from typing import Dict, Any, Optional
import httpx
from app.core.config import get_settings
from app.utils.prompt_loader import get_prompt_loader
from app.core.logging import get_logger

logger = get_logger("core.base_client")

class BaseAIClient:
    """Base client for interacting with AI Models."""
    
    def __init__(self):
        self.settings = get_settings()
        self.prompt_loader = get_prompt_loader()
        self.timeout = 120.0

    async def _make_request(
        self, 
        url: str, 
        payload: Dict[str, Any], 
        log_prefix: str = "AI Client"
    ) -> Dict[str, Any]:
        """
        Make a generic HTTP POST request to the AI provider.
        
        Args:
            url: The full API endpoint URL.
            payload: The JSON payload to send.
            log_prefix: Prefix for log messages.
            
        Returns:
            The parsed JSON response.
            
        Raises:
            httpx.HTTPStatusError: If the API returns an error status.
        """
        logger.debug(f"[{log_prefix}] Calling {url}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            
            logger.debug(f"[{log_prefix}] Response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"[{log_prefix}] Error response: {response.text[:500]}")
                
            response.raise_for_status()
            return response.json()
