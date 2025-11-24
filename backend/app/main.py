"""
FastAPI main application.
Entry point for the Food Assistant API.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import json
from datetime import datetime

from app.core.config import get_settings
from app.db.session import init_db
from app.api import routes_chat, routes_recipes
from app.core.logging import setup_logging

logger = setup_logging()


# Custom JSON encoder for datetime
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    logger.info("Starting Food Assistant API...")
    init_db()
    logger.info("Database initialized.")
    yield
    logger.info("Shutting down Food Assistant API...")


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
app.include_router(routes_chat.router, prefix="/api", tags=["chat"])
app.include_router(routes_recipes.router, tags=["recipes"])


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
        "llm_provider": settings.llm_provider
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
