"""
Social media scraper service using specialized extraction techniques.
Handles Instagram, TikTok, YouTube, Twitter/X, and other social media platforms.
Uses oEmbed APIs, Open Graph metadata, and platform-specific techniques.
"""
import httpx
import json
import re
from typing import Dict, Optional
from urllib.parse import urlparse

from app.utils.text_cleaning import (
    detect_social_platform,
    extract_social_media_content,
    is_social_media_url,
)


class SocialMediaScraper:
    """
    Scrape social media content using specialized extraction techniques.
    Extracts captions, video descriptions, transcripts, and recipe content.
    
    Methods:
    - oEmbed APIs for structured data
    - Open Graph and Twitter Card metadata
    - YouTube transcript extraction
    - Platform-specific HTML parsing
    """
    
    def __init__(self):
        """Initialize the social media scraper."""
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
    async def scrape_url(self, url: str) -> Optional[Dict]:
        """
        Scrape content from a social media URL using platform-specific methods.
        
        Args:
            url: Social media URL to scrape
            
        Returns:
            Dict with 'html', 'text', and 'metadata' keys, or None if failed
        """
        platform = detect_social_platform(url)
        
        if platform == 'youtube':
            return await self._scrape_youtube(url)
        elif platform == 'tiktok':
            return await self._scrape_tiktok(url)
        elif platform == 'instagram':
            return await self._scrape_instagram(url)
        elif platform in ['twitter', 'x']:
            return await self._scrape_twitter(url)
        else:
            # Generic scraping for other platforms
            return await self._scrape_generic(url)
    
    async def _scrape_youtube(self, url: str) -> Optional[Dict]:
        """
        Extract YouTube video metadata and transcript.
        
        Uses:
        - oEmbed API for basic metadata
        - HTML parsing for description
        - Video ID extraction for transcript API
        """
        try:
            video_id = self._extract_youtube_id(url)
            if not video_id:
                return None
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try oEmbed first
                oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
                response = await client.get(oembed_url)
                
                metadata = {}
                if response.status_code == 200:
                    metadata = response.json()
                
                # Fetch HTML for description
                headers = {"User-Agent": self.user_agent}
                html_response = await client.get(url, headers=headers)
                html_content = html_response.text
                
                return {
                    'html': html_content,
                    'text': '',
                    'metadata': metadata
                }
                
        except Exception as e:
            print(f"⚠️ Error scraping YouTube: {e}")
            return None
    
    async def _scrape_tiktok(self, url: str) -> Optional[Dict]:
        """Extract TikTok video metadata using oEmbed."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # TikTok oEmbed
                oembed_url = f"https://www.tiktok.com/oembed?url={url}"
                response = await client.get(oembed_url)
                
                if response.status_code == 200:
                    metadata = response.json()
                    text_content = f"Title: {metadata.get('title', '')}\nAuthor: {metadata.get('author_name', '')}"
                    
                    # Also try direct HTML fetch
                    headers = {"User-Agent": self.user_agent}
                    html_response = await client.get(url, headers=headers, follow_redirects=True)
                    
                    return {
                        'html': html_response.text,
                        'text': text_content,
                        'metadata': metadata
                    }
                    
        except Exception as e:
            print(f"⚠️ Error scraping TikTok: {e}")
            return None
    
    async def _scrape_instagram(self, url: str) -> Optional[Dict]:
        """
        Extract Instagram post metadata.
        
        NOTE: Instagram heavily blocks automated scraping and requires login
        for most content. This function will try to extract whatever is available
        but will likely get blocked.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try direct HTML fetch with good headers
                headers = {
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                response = await client.get(url, headers=headers, follow_redirects=True)
                html_content = response.text
                
                # Check if we got a login page or blocked
                if any(indicator in html_content.lower() for indicator in [
                    'login', 'log in', 'sign up', 'create an account',
                    'suspicious activity', 'blocked', 'rate limit'
                ]):
                    print(f"⚠️ Instagram appears to be requiring login or blocking access")
                    print(f"📋 Recommendation: Copy the post caption and paste it into chat instead")
                
                return {
                    'html': html_content,
                    'text': '',
                    'metadata': {}
                }
                
        except Exception as e:
            print(f"⚠️ Error scraping Instagram: {e}")
            return None
    
    async def _scrape_twitter(self, url: str) -> Optional[Dict]:
        """Extract Twitter/X post metadata."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                response = await client.get(url, headers=headers, follow_redirects=True)
                
                return {
                    'html': response.text,
                    'text': '',
                    'metadata': {}
                }
                
        except Exception as e:
            print(f"⚠️ Error scraping Twitter: {e}")
            return None
    
    async def _scrape_generic(self, url: str) -> Optional[Dict]:
        """Generic scraping for any social media URL."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"User-Agent": self.user_agent}
                response = await client.get(url, headers=headers, follow_redirects=True)
                
                return {
                    'html': response.text,
                    'text': '',
                    'metadata': {}
                }
                
        except Exception as e:
            print(f"⚠️ Error scraping URL: {e}")
            return None
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
            r'youtube\.com\/embed\/([^&\n?#]+)',
            r'youtube\.com\/v\/([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def detect_platform(self, url: str) -> Optional[str]:
        """Backward-compatible wrapper around the shared detector."""
        return detect_social_platform(url)
    
    def is_social_media(self, url: str) -> bool:
        """Return True when the URL belongs to a supported social platform."""
        return is_social_media_url(url)


async def fetch_social_media_content(url: str) -> Optional[Dict]:
    """
    Fetch content from social media URLs using specialized extraction techniques.
    
    Supports:
    - YouTube: oEmbed API + HTML parsing for descriptions
    - TikTok: oEmbed API for metadata
    - Instagram: Direct HTML scraping with Open Graph tags
    - Twitter/X: HTML scraping with meta tags
    - Others: Generic Open Graph extraction
    
    Args:
        url: Social media URL
        
    Returns:
        Dict with extracted content or None if failed
    """
    scraper = SocialMediaScraper()
    
    platform = detect_social_platform(url)
    if not platform:
        print(f"⚠️ URL does not appear to be from a supported social media platform")
        return None
    
    print(f"🌐 Detected platform: {platform}")
    print(f"🔄 Fetching content using {platform}-specific extraction...")
    
    result = await scraper.scrape_url(url)
    if result:
        html = result.get('html', '')
        if html:
            extracted = extract_social_media_content(url, html)
            result['text'] = extracted.get('content', '')
        html_len = len(html)
        text_len = len(result.get('text', ''))
        print(f"✓ Successfully extracted {html_len} chars HTML, {text_len} chars text")
        return result
    
    print(f"⚠️ Failed to extract content from {platform}")
    return None
