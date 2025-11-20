"""
Configuration module for the Food Assistant API.
Loads settings from environment variables.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Database (use relative path or set via environment variable)
    database_url: str = "sqlite:///./foodify.db"
    
    # Data paths (use relative path or set via environment variable)
    nutrition_data_path: str = "../data/nutrition_data.csv"
    
    # RAG Configuration
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_store_path: str = "./chroma_db"
    recipes_dataset: str = "AkashPS11/recipes_data_food.com"
    
    # LLM Configuration
    llm_provider: str = "ollama"
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3:latest"
    
    # VLM Configuration
    vlm_provider: str = "ollama"
    vlm_base_url: str = "http://localhost:11434"
    vlm_model: str = "qwen3-vl:latest"
    
    # Web Scraping
    # For blogs: Uses httpx + BeautifulSoup (fast, simple)
    # For social media: Uses oEmbed APIs, Open Graph metadata, and platform-specific extraction
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
