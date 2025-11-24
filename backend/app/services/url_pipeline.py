"""
URL analysis pipeline.
Fetches content from URLs using httpx and BeautifulSoup for HTML parsing.
Supports social media URLs via specialized extraction techniques.
"""
from typing import Tuple, Dict, Any
from sqlalchemy.orm import Session
import httpx

from app.core.config import get_settings
from app.core.constants import HTTPConstants, LimitsConstants
from app.core.llm_client import get_llm_client
from app.db.schema import Recipe, NutritionSummary, RecipeBase
from app.services.base_pipeline import BaseIngestionPipeline
from app.utils.text_cleaning import (
    extract_url_content,
    is_social_media_url,
    extract_social_media_content
)
from app.services.social_media_scraper import fetch_social_media_content
from app.services.video_transcript import get_transcript_extractor
from app.core.logging import get_logger

logger = get_logger("services.url_pipeline")


async def fetch_url_content(url: str) -> dict:
    """
    Fetch and extract content from a URL.
    
    For social media URLs: Uses specialized extraction (oEmbed, Open Graph, platform APIs)
    For blog/recipe sites: Uses httpx with BeautifulSoup (faster, simpler)
    
    Supports:
    - Social media: Instagram, TikTok, YouTube, Twitter/X, Facebook, Pinterest, Reddit
    - Blogs: Automatic decompression (gzip, deflate, brotli), HTTP/2, redirects
    
    Args:
        url: Recipe URL to fetch
    
    Returns:
        Dict with extracted content
    """
    # Check if this is a social media URL
    if is_social_media_url(url):
        logger.info(f"Detected social media URL, using specialized extraction...")
        
        # Use specialized social media extraction techniques
        social_result = await fetch_social_media_content(url)

        
        if social_result and social_result.get('html'):
            logger.info(f"Specialized extraction: {len(social_result['html'])} chars HTML")
            # Extract social media specific content with platform parsers
            extracted = extract_social_media_content(url, social_result['html'])
            
            # If we have additional text from metadata, prepend it
            if social_result.get('text'):
                extracted['content'] = social_result['text'] + '\n\n' + extracted['content']
            
            return extracted
        else:
            logger.warning(f"Specialized extraction failed, falling back to httpx...")
            # Fall through to regular httpx scraping
    
    # Regular blog/recipe site scraping with httpx
    html_content = None
    
    # Use httpx with multiple user agents for better compatibility
    # httpx automatically handles compression (gzip, deflate, br) if dependencies are installed
    for user_agent in HTTPConstants.USER_AGENTS:
        try:
            headers = HTTPConstants.get_headers_with_user_agent(user_agent)
            async with httpx.AsyncClient(
                timeout=LimitsConstants.HTTP_TIMEOUT_SECONDS,
                follow_redirects=True
            ) as client:
                response = await client.get(url, headers=headers)
                
                logger.debug(f"  Response status: {response.status_code}, encoding: {response.encoding}")
                logger.debug(f"  Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    # Use response.text directly - httpx handles decoding
                    html_content = response.text
                    
                    logger.debug(f"  HTML length: {len(html_content)}")
                    
                    if len(html_content) > LimitsConstants.HTTP_MAX_CONTENT_LENGTH:
                        logger.info(f"httpx: Extracted {len(html_content)} chars from URL")
                        return extract_url_content(url, html_content)
                        
        except Exception as e:
            logger.warning(f"Failed with user agent {user_agent[:50]}: {str(e)[:60]}")
            continue
    
    raise RuntimeError(
        f"Failed to fetch URL with all methods. Try pasting recipe content into Chat."
    )


class UrlIngestionPipeline(BaseIngestionPipeline):
    async def extract_recipe_data(self, url: str, **kwargs) -> Tuple[RecipeBase, Dict[str, Any]]:
        # Step 1: Fetch content
        logger.info(f"Fetching URL: {url}")
        content_data = await fetch_url_content(url)
        logger.info(f"Content type: {content_data['type']}, length: {len(str(content_data['content']))} chars")
        
        # Check if we got minimal content - try video transcript extraction
        content_length = len(str(content_data['content']))
        if content_length < 100 and is_social_media_url(url):
            logger.warning(f"Limited text content ({content_length} chars) from social media")
            logger.info(f"Attempting video transcript extraction...")
            
            # Try to extract transcript from video
            extractor = get_transcript_extractor()
            transcript = await extractor.extract_transcript(url)
            
            if transcript and len(transcript) > 100:
                logger.info(f"Extracted transcript: {len(transcript)} chars from video audio")
                # Prepend transcript to existing content
                content_data['content'] = f"Video Transcript:\n{transcript}\n\n{content_data['content']}"
                content_length = len(content_data['content'])
            else:
                logger.warning(f"Could not extract transcript. Will try with available content.")
        
        # Final check - warn if still minimal
        if content_length < 30:
            logger.warning(f"Very limited content ({content_length} chars) - likely blocked/login required")
            logger.warning(f"Will attempt LLM extraction but may fail. Consider using Chat with copied text.")
        
        # Step 2: Extract recipe
        recipe_base = None
        if content_data['type'] == 'json-ld':
            # Direct parsing from JSON-LD (fast, no LLM needed)
            logger.info("Parsing JSON-LD structured data...")
            from app.utils.recipe_parser import json_ld_to_recipe
            recipe_base = json_ld_to_recipe(content_data['content'])
            
            # Validate JSON-LD had sufficient data - if not, fall back to LLM
            if not recipe_base.ingredients or len(recipe_base.ingredients) == 0:
                logger.warning("JSON-LD incomplete (no ingredients), falling back to LLM...")
                # Use the full JSON-LD description which often contains embedded recipe data
                json_text = f"Recipe: {recipe_base.name}\n\n{recipe_base.description}"
                logger.info(f"Sending {len(json_text)} chars to LLM for parsing...")
                recipe_base = await self.llm.generate_recipe_from_text(json_text)
        else:
            # Use LLM to parse unstructured text (slower)
            logger.info("Using LLM to extract recipe from text...")
            logger.debug(f"Content preview: {content_data['content'][:200]}...")
            recipe_base = await self.llm.generate_recipe_from_text(content_data['content'])
        
        # Validate that we got a valid recipe with ingredients
        if not recipe_base.ingredients or len(recipe_base.ingredients) == 0:
            raise ValueError(
                "Failed to extract recipe. No ingredients found in the content. "
                "The platform may be blocking access or the content doesn't contain a recipe. "
                "Try copying the recipe text and using the Chat feature instead!"
            )
        
        logger.info(f"Recipe extracted: {recipe_base.name}")
        
        return recipe_base, {
            "tag_context": recipe_base.description or recipe_base.name
        }


async def analyze_url_pipeline(
    db: Session,
    url: str
) -> Tuple[Recipe, NutritionSummary, list[str]]:
    """
    Full pipeline for analyzing a recipe URL.
    """
    pipeline = UrlIngestionPipeline(db)
    return await pipeline.run(url, source_type="url", source_ref=url)
