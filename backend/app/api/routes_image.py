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


@router.post("/analyze-image")
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
        
        # Create response and serialize manually to handle datetime
        print(f"[Image API] Creating response with recipe type: {type(recipe)}")
        print(f"[Image API] Recipe created_at type: {type(recipe.created_at)}")
        
        response = AnalyzeImageResponse(
            recipe=recipe,
            nutrition=nutrition,
            tags=tags,
            debug=debug
        )
        
        print(f"[Image API] Response created, dumping to JSON...")
        # Use Pydantic's model_dump with mode='json' to properly serialize datetime
        result = response.model_dump(mode='json')
        print(f"[Image API] Successfully dumped to JSON, returning...")
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")
