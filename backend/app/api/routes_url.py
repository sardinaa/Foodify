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
    try:
        # Run pipeline
        recipe, nutrition, tags = await analyze_url_pipeline(
            db, request.url
        )

        return AnalyzeUrlResponse(
            recipe=recipe,
            nutrition=nutrition,
            tags=tags
        )

    except RuntimeError as re:
        # Likely network/fetch issue or blocked content
        error_msg = str(re)
        if "social media" in error_msg.lower() or "blocked" in error_msg.lower() or "login" in error_msg.lower():
            detail = f"Could not access content from this URL. The platform may require login or is blocking automated access. Try copying the recipe caption/description and using the Chat feature for guaranteed results!"
        else:
            detail = f"URL fetch/extraction failed: {error_msg}"
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:
        error_str = str(e)
        # Check if it's a recipe extraction failure
        if "recipe" in error_str.lower() or "parse" in error_str.lower() or "extract" in error_str.lower():
            detail = f"Could not extract a recipe from this URL. The content may not contain recipe information, or the platform is blocking access. Try copying the recipe text and using the Chat feature instead!"
        else:
            detail = f"URL analysis failed: {error_str}"
        raise HTTPException(status_code=500, detail=detail)
