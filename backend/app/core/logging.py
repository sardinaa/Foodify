import logging
import sys
from app.core.config import get_settings

def setup_logging():
    """Configure logging for the application."""
    settings = get_settings()
    
    # Create logger
    logger = logging.getLogger("app")
    logger.setLevel(settings.log_level.upper())
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(settings.log_level.upper())
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    if not logger.handlers:
        logger.addHandler(handler)
        
    # Configure root logger as well to capture library logs if needed, 
    # but usually we want to control our own app logger.
    # For now, let's just ensure our app logger is configured.
    
    return logger

def get_logger(name: str):
    """Get a logger instance with the given name."""
    # Ensure the parent 'app' logger is configured
    setup_logging()
    return logging.getLogger(f"app.{name}")
