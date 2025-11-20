"""
Text cleaning utilities for processing URLs and extracted content.
"""
import re
from bs4 import BeautifulSoup
from typing import Optional, Dict
import json
from urllib.parse import urlparse


def clean_html(html_content: str) -> str:
    """
    Extract and clean text from HTML content.
    Excludes scripts, styles, navigation, comments, and other non-content elements.
    
    Args:
        html_content: Raw HTML string
    
    Returns:
        Cleaned text content
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove unwanted elements (scripts, styles, nav, comments sections, etc.)
    for element in soup(["script", "style", "header", "footer", "nav", "aside", "iframe", "noscript"]):
        element.decompose()
    
    # Remove comment sections (common patterns)
    for comment_section in soup.find_all(['div', 'section', 'aside'], 
                                          class_=re.compile(r'comment|reply|thread|discussion', re.I)):
        comment_section.decompose()
    
    for comment_section in soup.find_all(['div', 'section'], 
                                          id=re.compile(r'comment|reply|thread|discussion', re.I)):
        comment_section.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text


def clean_recipe_text(text: str) -> str:
    """
    Clean and normalize recipe text for better LLM processing.
    Preserves Unicode characters for international recipes.
    
    Args:
        text: Raw text
    
    Returns:
        Cleaned text
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters and other problematic Unicode, but keep:
    # - Letters (any language) \p{L} via \w
    # - Numbers
    # - Common punctuation
    # - Accented characters (á, é, í, ó, ú, ñ, etc.)
    # Only remove control characters and format characters
    text = ''.join(char for char in text if char.isprintable() or char.isspace())
    
    # Trim
    text = text.strip()
    
    return text


def extract_url_content(url: str, html_content: str) -> dict:
    """
    Extract relevant content from a URL's HTML.
    Returns structured JSON-LD data if available, otherwise text.
    
    Args:
        url: Source URL
        html_content: HTML content
    
    Returns:
        Dict with 'type' ('json-ld' or 'text') and 'content' (structured data or text)
    """
    soup = BeautifulSoup(html_content, 'lxml')

    # 1) Try JSON-LD <script type="application/ld+json"> with @type Recipe
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string or '')
        except Exception:
            # Try to be forgiving when ld+json contains multiple objects or arrays
            try:
                data = json.loads((script.string or '').strip())
            except Exception:
                continue

        # Support both dict and list
        candidates = data if isinstance(data, list) else [data]
        for cand in candidates:
            if not isinstance(cand, dict):
                continue
            typ = cand.get('@type') or cand.get('type')
            # Some JSON-LD uses array of types
            if isinstance(typ, list):
                is_recipe = 'Recipe' in typ
            else:
                is_recipe = typ == 'Recipe'

            if is_recipe:
                # Return structured JSON-LD data directly
                return {'type': 'json-ld', 'content': cand}

    # 2) Try to find recipe-specific containers (prioritize recipe content)
    recipe_containers = []
    
    # Look for common recipe container patterns
    patterns = [
        ('div', {'class': re.compile(r'recipe', re.I)}),
        ('article', {'class': re.compile(r'recipe', re.I)}),
        ('section', {'class': re.compile(r'recipe', re.I)}),
        ('div', {'id': re.compile(r'recipe', re.I)}),
        ('main', {}),
        ('article', {})
    ]
    
    for tag, attrs in patterns:
        containers = soup.find_all(tag, attrs)
        if containers:
            recipe_containers = containers
            break
    
    # Extract ingredients and instructions specifically
    ingredients_section = soup.find(['ul', 'ol', 'div'], class_=re.compile(r'ingredient', re.I))
    instructions_section = soup.find(['ol', 'div', 'section'], class_=re.compile(r'instruction|direction|step|method', re.I))
    
    text_parts = []
    
    # Add title if available
    title = soup.find('h1') or soup.find('title')
    if title:
        text_parts.append(f"Recipe: {title.get_text(strip=True)}")
    
    # Add ingredients
    if ingredients_section:
        text_parts.append("\nIngredients:")
        text_parts.append(ingredients_section.get_text(separator='\n', strip=True))
    
    # Add instructions
    if instructions_section:
        text_parts.append("\nInstructions:")
        text_parts.append(instructions_section.get_text(separator='\n', strip=True))
    
    # Add general recipe container content
    if recipe_containers:
        text_parts.append("\nRecipe Details:")
        text_parts.append(' '.join(container.get_text(separator=' ', strip=True) for container in recipe_containers[:2]))
    
    # Fallback to OpenGraph tags, then general content
    if not text_parts:
        # Try OpenGraph / meta tags
        og_title = soup.find('meta', property='og:title')
        og_desc = soup.find('meta', property='og:description')
        if og_title or og_desc:
            parts = []
            if og_title and og_title.get('content'):
                parts.append(og_title.get('content'))
            if og_desc and og_desc.get('content'):
                parts.append(og_desc.get('content'))
            text = ' '.join(parts)
        else:
            text = clean_html(html_content)
    else:
        text = '\n'.join(text_parts)
    
    # Clean and limit text length for LLM processing
    cleaned_text = clean_recipe_text(text)
    
    # Keep reasonable length (increase from 2000 to 4000 for better context)
    if len(cleaned_text) > 4000:
        # Try to keep complete sentences
        cleaned_text = cleaned_text[:4000]
        last_period = cleaned_text.rfind('.')
        if last_period > 3000:
            cleaned_text = cleaned_text[:last_period + 1]

    print(f"📝 Returning text type: length={len(cleaned_text)}, first 500 chars: {cleaned_text[:500]}")
    return {'type': 'text', 'content': cleaned_text}


def is_social_media_url(url: str) -> bool:
    """
    Check if URL is from a social media platform.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL is from social media platform
    """
    parsed = urlparse(url.lower())
    domain = parsed.netloc.replace('www.', '')
    
    social_media_domains = [
        'instagram.com', 'tiktok.com', 'youtube.com', 'youtu.be',
        'twitter.com', 'x.com', 'facebook.com', 'fb.com',
        'pinterest.com', 'pin.it', 'reddit.com', 'snapchat.com'
    ]
    
    return domain in social_media_domains


def extract_social_media_content(url: str, html_content: str) -> Dict:
    """
    Extract content from social media HTML with platform-specific parsing.
    Focuses on captions, descriptions, video metadata, and recipe content.
    
    Args:
        url: Source URL
        html_content: HTML content from social media page
        
    Returns:
        Dict with 'type' ('text') and 'content' (extracted text)
    """
    soup = BeautifulSoup(html_content, 'lxml')
    platform = detect_social_platform(url)
    
    print(f"🔍 Extracting content from {platform}...")
    
    text_parts = []
    
    # Platform-specific extraction strategies
    if platform == 'instagram':
        text_parts.extend(_extract_instagram_content(soup))
    elif platform == 'tiktok':
        text_parts.extend(_extract_tiktok_content(soup))
    elif platform == 'youtube':
        text_parts.extend(_extract_youtube_content(soup))
    elif platform == 'twitter' or platform == 'x':
        text_parts.extend(_extract_twitter_content(soup))
    elif platform == 'facebook':
        text_parts.extend(_extract_facebook_content(soup))
    elif platform == 'pinterest':
        text_parts.extend(_extract_pinterest_content(soup))
    else:
        # Fallback: look for common social media patterns
        text_parts.extend(_extract_generic_social_content(soup))
    
    print(f"📋 Extracted {len(text_parts)} content sections")
    for i, part in enumerate(text_parts[:3], 1):  # Show first 3 parts
        print(f"   {i}. {part[:100]}...")
    
    # Combine all extracted text
    if text_parts:
        text = '\n\n'.join(filter(None, text_parts))
    else:
        print(f"⚠️  No specific content found, using fallback extraction...")
        # Ultimate fallback - extract all visible text but be smarter about it
        text = clean_html(html_content)
    
    # Clean and limit
    cleaned_text = clean_recipe_text(text)
    
    # If we got very little content, warn but still try
    if len(cleaned_text) < 50:
        print(f"⚠️  Limited content extracted ({len(cleaned_text)} chars). Will try LLM anyway.")
        print(f"💡 If extraction fails, try copying the text and using Chat instead.")
    
    if len(cleaned_text) > 4000:
        cleaned_text = cleaned_text[:4000]
        last_period = cleaned_text.rfind('.')
        if last_period > 3000:
            cleaned_text = cleaned_text[:last_period + 1]
    
    print(f"✅ Final extracted content: {len(cleaned_text)} chars")
    return {'type': 'text', 'content': cleaned_text}


def detect_social_platform(url: str) -> Optional[str]:
    """Detect social media platform from URL."""
    parsed = urlparse(url.lower())
    domain = parsed.netloc.replace('www.', '')
    
    platform_map = {
        'instagram.com': 'instagram',
        'tiktok.com': 'tiktok',
        'youtube.com': 'youtube',
        'youtu.be': 'youtube',
        'twitter.com': 'twitter',
        'x.com': 'x',
        'facebook.com': 'facebook',
        'fb.com': 'facebook',
        'pinterest.com': 'pinterest',
        'pin.it': 'pinterest',
        'reddit.com': 'reddit',
        'snapchat.com': 'snapchat'
    }
    
    return platform_map.get(domain)


def _extract_instagram_content(soup: BeautifulSoup) -> list:
    """Extract Instagram captions and video descriptions."""
    parts = []
    
    # Instagram embeds data in various places:
    # 1. Try to find embedded JSON data in script tags
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            data = json.loads(script.string or '')
            if isinstance(data, dict):
                if 'caption' in data:
                    parts.append(f"Caption: {data['caption']}")
                if 'description' in data:
                    parts.append(f"Description: {data['description']}")
                if 'articleBody' in data:
                    parts.append(f"Content: {data['articleBody']}")
        except:
            pass
    
    # 2. Check for meta tags (most reliable for Instagram)
    og_title = soup.find('meta', property='og:title')
    og_desc = soup.find('meta', property='og:description')
    twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
    
    if og_title and og_title.get('content'):
        title = og_title.get('content')
        if title and len(title) > 10:  # Filter out generic titles
            parts.append(f"Post Title: {title}")
    
    if og_desc and og_desc.get('content'):
        desc = og_desc.get('content')
        if desc and len(desc) > 10:
            parts.append(f"Description: {desc}")
    
    if twitter_desc and twitter_desc.get('content'):
        desc = twitter_desc.get('content')
        if desc and len(desc) > 10 and desc not in str(parts):
            parts.append(f"Caption: {desc}")
    
    # 3. Try to extract from window._sharedData or similar embedded JSON
    for script in soup.find_all('script'):
        if script.string and 'window._sharedData' in script.string:
            try:
                # Extract JSON from window._sharedData
                text = script.string
                start = text.find('{')
                end = text.rfind('}') + 1
                if start > -1 and end > start:
                    data = json.loads(text[start:end])
                    # Navigate through Instagram's data structure
                    if 'entry_data' in data:
                        for key in ['PostPage', 'ProfilePage', 'StoriesPage']:
                            if key in data['entry_data']:
                                posts = data['entry_data'][key]
                                for post_data in posts:
                                    if 'graphql' in post_data:
                                        media = post_data['graphql'].get('shortcode_media', {})
                                        if 'edge_media_to_caption' in media:
                                            edges = media['edge_media_to_caption'].get('edges', [])
                                            for edge in edges:
                                                caption = edge.get('node', {}).get('text', '')
                                                if caption:
                                                    parts.append(f"Instagram Caption: {caption}")
            except:
                pass
    
    # 4. If still no content, extract from any visible article/main content
    if not parts:
        article = soup.find('article')
        if article:
            # Get all text from article, excluding script/style
            for elem in article(['script', 'style', 'nav', 'footer']):
                elem.decompose()
            text = article.get_text(separator=' ', strip=True)
            if text and len(text) > 20:
                # Limit to reasonable size
                parts.append(f"Post Content: {text[:1000]}")
    
    return parts


def _extract_tiktok_content(soup: BeautifulSoup) -> list:
    """Extract TikTok video descriptions and captions."""
    parts = []
    
    # TikTok often uses meta tags
    og_title = soup.find('meta', property='og:title')
    og_desc = soup.find('meta', property='og:description')
    
    if og_title and og_title.get('content'):
        parts.append(f"Title: {og_title.get('content')}")
    
    if og_desc and og_desc.get('content'):
        parts.append(f"Description: {og_desc.get('content')}")
    
    # Try to find video description
    desc_elem = soup.find(['div', 'span'], class_=re.compile(r'desc|caption|title', re.I))
    if desc_elem:
        text = desc_elem.get_text(strip=True)
        if text and text not in str(parts):
            parts.append(f"Video caption: {text}")
    
    return parts


def _extract_youtube_content(soup: BeautifulSoup) -> list:
    """Extract YouTube video title and description - works for regular videos and Shorts."""
    parts = []
    
    # 1. YouTube meta tags (most reliable)
    og_title = soup.find('meta', property='og:title')
    og_desc = soup.find('meta', property='og:description')
    twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
    twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
    
    if og_title and og_title.get('content'):
        parts.append(f"Video: {og_title.get('content')}")
    elif twitter_title and twitter_title.get('content'):
        parts.append(f"Video: {twitter_title.get('content')}")
    
    if og_desc and og_desc.get('content'):
        desc = og_desc.get('content')
        if len(desc) > 20:  # Filter out very short descriptions
            parts.append(f"Description: {desc}")
    elif twitter_desc and twitter_desc.get('content'):
        desc = twitter_desc.get('content')
        if len(desc) > 20:
            parts.append(f"Description: {desc}")
    
    # 2. Try to extract from embedded JSON data (ytInitialData or ytInitialPlayerResponse)
    for script in soup.find_all('script'):
        if script.string and ('ytInitialData' in script.string or 'ytInitialPlayerResponse' in script.string):
            try:
                # Extract JSON from various YouTube data structures
                text = script.string
                
                # Look for videoDetails
                if '"videoDetails"' in text:
                    import json
                    # Try to extract the videoDetails object
                    start = text.find('"videoDetails"')
                    if start > -1:
                        # Find the opening brace after videoDetails
                        brace_start = text.find('{', start)
                        if brace_start > -1:
                            # Count braces to find the end
                            brace_count = 1
                            i = brace_start + 1
                            while i < len(text) and brace_count > 0:
                                if text[i] == '{':
                                    brace_count += 1
                                elif text[i] == '}':
                                    brace_count -= 1
                                i += 1
                            
                            if brace_count == 0:
                                json_str = text[brace_start:i]
                                try:
                                    video_details = json.loads(json_str)
                                    if 'title' in video_details and 'title' not in str(parts):
                                        parts.append(f"Title: {video_details['title']}")
                                    if 'shortDescription' in video_details:
                                        desc = video_details['shortDescription']
                                        if desc and len(desc) > 20 and desc not in str(parts):
                                            parts.append(f"Video Description: {desc}")
                                except:
                                    pass
            except:
                pass
    
    # 3. Try to find description element in page
    desc_elem = soup.find('div', id=re.compile(r'description', re.I))
    if desc_elem:
        text = desc_elem.get_text(strip=True)
        if text and len(text) > 20 and text not in str(parts):
            parts.append(f"Details: {text[:500]}")
    
    # 4. For Shorts, try to find any text content in the page
    if not parts or len(str(parts)) < 50:
        # Look for any substantial text in the body
        body = soup.find('body')
        if body:
            # Remove unwanted elements
            for elem in body(['script', 'style', 'nav', 'header', 'footer']):
                elem.decompose()
            
            # Get all text
            all_text = body.get_text(separator=' ', strip=True)
            # Look for recipe-related keywords to extract relevant sections
            if any(keyword in all_text.lower() for keyword in ['recipe', 'ingredient', 'cook', 'prepare', 'serve']):
                # Extract up to 1000 chars of text that might contain recipe info
                parts.append(f"Page Content: {all_text[:1000]}")
    
    return parts


def _extract_twitter_content(soup: BeautifulSoup) -> list:
    """Extract Twitter/X post content."""
    parts = []
    
    # Twitter uses meta tags heavily
    og_desc = soup.find('meta', property='og:description')
    twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
    
    if og_desc and og_desc.get('content'):
        parts.append(f"Tweet: {og_desc.get('content')}")
    elif twitter_desc and twitter_desc.get('content'):
        parts.append(f"Tweet: {twitter_desc.get('content')}")
    
    # Look for tweet text
    tweet_elem = soup.find(['div', 'span'], attrs={'data-testid': 'tweetText'})
    if tweet_elem:
        parts.append(f"Content: {tweet_elem.get_text(strip=True)}")
    
    return parts


def _extract_facebook_content(soup: BeautifulSoup) -> list:
    """Extract Facebook post content."""
    parts = []
    
    og_title = soup.find('meta', property='og:title')
    og_desc = soup.find('meta', property='og:description')
    
    if og_title and og_title.get('content'):
        parts.append(f"Post: {og_title.get('content')}")
    
    if og_desc and og_desc.get('content'):
        parts.append(f"Description: {og_desc.get('content')}")
    
    return parts


def _extract_pinterest_content(soup: BeautifulSoup) -> list:
    """Extract Pinterest pin descriptions."""
    parts = []
    
    og_desc = soup.find('meta', property='og:description')
    if og_desc and og_desc.get('content'):
        parts.append(f"Pin: {og_desc.get('content')}")
    
    # Pinterest often has description in specific divs
    desc_elem = soup.find('div', class_=re.compile(r'description|pinDescription', re.I))
    if desc_elem:
        parts.append(f"Description: {desc_elem.get_text(strip=True)}")
    
    return parts


def _extract_generic_social_content(soup: BeautifulSoup) -> list:
    """Generic extraction for unknown social media platforms."""
    parts = []
    
    # Try all common meta tags
    og_title = soup.find('meta', property='og:title')
    og_desc = soup.find('meta', property='og:description')
    twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
    twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    
    if og_title and og_title.get('content'):
        title = og_title.get('content')
        if title and len(title) > 10:
            parts.append(f"Title: {title}")
    
    if twitter_title and twitter_title.get('content'):
        title = twitter_title.get('content')
        if title and len(title) > 10 and title not in str(parts):
            parts.append(f"Title: {title}")
    
    for meta in [og_desc, twitter_desc, meta_desc]:
        if meta and meta.get('content'):
            content = meta.get('content')
            if content and len(content) > 10 and content not in str(parts):
                parts.append(f"Description: {content}")
    
    # Try to find main content area (avoid comments)
    main_content = soup.find(['main', 'article', 'div'], attrs={'role': 'main'})
    if main_content:
        # Remove comment sections
        for comment_section in main_content.find_all(['div', 'section'], class_=re.compile(r'comment|reply|thread', re.I)):
            comment_section.decompose()
        
        text = main_content.get_text(separator=' ', strip=True)
        if text and len(text) > 50 and text not in str(parts):
            parts.append(f"Content: {text[:1000]}")
    
    return parts
