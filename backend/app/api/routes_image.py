"""
API routes for image analysis.
"""
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.db.schema import AnalyzeImageResponse
from app.services.image_pipeline import analyze_image_pipeline

router = APIRouter()


@router.post("/analyze-image", response_model=AnalyzeImageResponse)
async def analyze_image(
    image: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Analyze a food image and extract recipe with nutrition.
    
    - **image**: Image file (JPG, PNG)
    - **title**: Optional user-provided title/description
    
    Returns structured recipe, nutrition data, and tags.
    """
    try:
        # Read image bytes
        image_bytes = await image.read()
        
        # Run pipeline
        recipe, nutrition, tags, debug = await analyze_image_pipeline(
            db, image_bytes, title
        )
        
        return AnalyzeImageResponse(
            recipe=recipe,
            nutrition=nutrition,
            tags=tags,
            debug=debug
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")
