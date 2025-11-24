"""
API routes for URL analysis.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.schema import AnalyzeUrlRequest, AnalyzeUrlResponse
from app.services.url_pipeline import analyze_url_pipeline

router = APIRouter()


@router.post("/analyze-url", response_model=AnalyzeUrlResponse)
async def analyze_url(
    request: AnalyzeUrlRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze a recipe URL and extract structured recipe with nutrition.
    
    - **url**: URL to a recipe (blog, YouTube, social media, etc.)
    
    Supports:
    - Recipe blogs (best results)
    - YouTube (extracts from description)
    - Social media (Instagram, TikTok, Twitter) - limited due to platform restrictions
    
    Note: Social media platforms often block automated access. For best results with
    social media, copy the caption/description and use the Chat feature instead.
    
    Returns structured recipe, nutrition data, and tags.
    """
    # Run pipeline
    recipe, nutrition, tags = await analyze_url_pipeline(
        db, request.url
    )

    return AnalyzeUrlResponse(
        recipe=recipe,
        nutrition=nutrition,
        tags=tags
    )
