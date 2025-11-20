"""
URL analysis pipeline.
Fetches content from URLs using httpx and BeautifulSoup for HTML parsing.
Supports social media URLs via specialized extraction techniques.
"""
from typing import Tuple
from sqlalchemy.orm import Session
import httpx

from app.core.config import get_settings
from app.core.constants import HTTPConstants, LimitsConstants
from app.core.llm_client import get_llm_client
from app.db.schema import Recipe, NutritionSummary
from app.services.ingestion.base import persist_generated_recipe
from app.utils.text_cleaning import (
    extract_url_content,
    is_social_media_url,
    extract_social_media_content
)
from app.services.social_media_scraper import fetch_social_media_content
from app.services.video_transcript import get_transcript_extractor


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
        print(f"📱 Detected social media URL, using specialized extraction...")
        
        # Use specialized social media extraction techniques
        social_result = await fetch_social_media_content(url)
        
        if social_result and social_result.get('html'):
            print(f"✓ Specialized extraction: {len(social_result['html'])} chars HTML")
            # Extract social media specific content with platform parsers
            extracted = extract_social_media_content(url, social_result['html'])
            
            # If we have additional text from metadata, prepend it
            if social_result.get('text'):
                extracted['content'] = social_result['text'] + '\n\n' + extracted['content']
            
            return extracted
        else:
            print(f"⚠️ Specialized extraction failed, falling back to httpx...")
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
                
                print(f"  Response status: {response.status_code}, encoding: {response.encoding}")
                print(f"  Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    # Use response.text directly - httpx handles decoding
                    html_content = response.text
                    
                    print(f"  HTML length: {len(html_content)}")
                    
                    if len(html_content) > LimitsConstants.HTTP_MAX_CONTENT_LENGTH:
                        print(f"✓ httpx: Extracted {len(html_content)} chars from URL")
                        return extract_url_content(url, html_content)
                        
        except Exception as e:
            print(f"⚠ Failed with user agent {user_agent[:50]}: {str(e)[:60]}")
            continue
    
    raise RuntimeError(
        f"Failed to fetch URL with all methods. Try pasting recipe content into Chat."
    )


async def analyze_url_pipeline(
    db: Session,
    url: str
) -> Tuple[Recipe, NutritionSummary, list[str]]:
    """
    Full pipeline for analyzing a recipe URL.
    
    Steps:
    1. Fetch and clean URL content
    2. Extract structured recipe using LLM
    3. Generate tags
    4. Calculate nutrition
    5. Persist to database
    
    Args:
        db: Database session
        url: Recipe URL
    
    Returns:
        Tuple of (Recipe, NutritionSummary, tags)
    """
    try:
        llm = get_llm_client()
        
        # Step 1: Fetch content
        print(f"📥 Fetching URL: {url}")
        content_data = await fetch_url_content(url)
        print(f"📄 Content type: {content_data['type']}, length: {len(str(content_data['content']))} chars")
        
        # Check if we got minimal content - try video transcript extraction
        content_length = len(str(content_data['content']))
        if content_length < 100 and is_social_media_url(url):
            print(f"⚠️  Limited text content ({content_length} chars) from social media")
            print(f"🎬 Attempting video transcript extraction...")
            
            # Try to extract transcript from video
            extractor = get_transcript_extractor()
            transcript = await extractor.extract_transcript(url)
            
            if transcript and len(transcript) > 100:
                print(f"✓ Extracted transcript: {len(transcript)} chars from video audio")
                # Prepend transcript to existing content
                content_data['content'] = f"Video Transcript:\n{transcript}\n\n{content_data['content']}"
                content_length = len(content_data['content'])
            else:
                print(f"⚠️  Could not extract transcript. Will try with available content.")
        
        # Final check - warn if still minimal
        if content_length < 30:
            print(f"⚠️  Very limited content ({content_length} chars) - likely blocked/login required")
            print(f"💡 Will attempt LLM extraction but may fail. Consider using Chat with copied text.")
        
        # Step 2: Extract recipe
        if content_data['type'] == 'json-ld':
            # Direct parsing from JSON-LD (fast, no LLM needed)
            print("🔍 Parsing JSON-LD structured data...")
            from app.utils.recipe_parser import json_ld_to_recipe
            recipe_base = json_ld_to_recipe(content_data['content'])
            
            # Validate JSON-LD had sufficient data - if not, fall back to LLM
            if not recipe_base.ingredients or len(recipe_base.ingredients) == 0:
                print("⚠️  JSON-LD incomplete (no ingredients), falling back to LLM...")
                # Use the full JSON-LD description which often contains embedded recipe data
                json_text = f"Recipe: {recipe_base.name}\n\n{recipe_base.description}"
                print(f"📝 Sending {len(json_text)} chars to LLM for parsing...")
                recipe_base = await llm.generate_recipe_from_text(json_text)
        else:
            # Use LLM to parse unstructured text (slower)
            print("🤖 Using LLM to extract recipe from text...")
            print(f"📝 Content preview: {content_data['content'][:200]}...")
            recipe_base = await llm.generate_recipe_from_text(content_data['content'])
        
        # Validate that we got a valid recipe with ingredients
        if not recipe_base.ingredients or len(recipe_base.ingredients) == 0:
            raise ValueError(
                "Failed to extract recipe. No ingredients found in the content. "
                "The platform may be blocking access or the content doesn't contain a recipe. "
                "Try copying the recipe text and using the Chat feature instead!"
            )
        
        print(f"✓ Recipe extracted: {recipe_base.name}")
        
        # Step 3-5: Generate tags, calculate nutrition, and save
        print("🏷️  Generating tags and saving recipe...")
        recipe, nutrition, tags = await persist_generated_recipe(
            db,
            llm,
            recipe_base,
            source_type="url",
            source_ref=url,
            tag_context=recipe_base.description or recipe_base.name,
        )

        print(f"✅ Recipe saved with ID: {recipe.id}")
        return recipe, nutrition, tags
        
    except Exception as e:
        print(f"❌ Error in analyze_url_pipeline: {type(e).__name__}: {str(e)}")
        raise
