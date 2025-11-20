"""
FastAPI main application.
Entry point for the Food Assistant API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import json
from datetime import datetime

from app.core.config import get_settings
from app.db.session import init_db
from app.api import routes_image, routes_url, routes_chat, routes_rag


# Custom JSON encoder for datetime
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


# Create FastAPI app
app = FastAPI(
    title="Food Assistant API",
    description="AI-powered food assistant for recipe extraction and nutrition analysis",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes_image.router, prefix="/api", tags=["image"])
app.include_router(routes_url.router, prefix="/api", tags=["url"])
app.include_router(routes_chat.router, prefix="/api", tags=["chat"])
app.include_router(routes_rag.router, tags=["rag"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Food Assistant API is running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    settings = get_settings()
    return {
        "status": "healthy",
        "database": settings.database_url,
        "llm_provider": settings.llm_provider,
        "vlm_provider": settings.vlm_provider
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
