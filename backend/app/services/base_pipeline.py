"""
Base class for ingestion pipelines.
"""
from abc import ABC, abstractmethod
from typing import Any, Tuple, List, Optional, Dict
from sqlalchemy.orm import Session

from app.core.llm_client import get_llm_client, LLMClient
from app.db.schema import RecipeBase, Recipe, NutritionSummary
from app.services.ingestion.base import persist_generated_recipe
from app.core.logging import get_logger

logger = get_logger("services.base_pipeline")


class BaseIngestionPipeline(ABC):
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm_client()

    @abstractmethod
    async def extract_recipe_data(self, input_data: Any, **kwargs) -> Tuple[RecipeBase, Dict[str, Any]]:
        """
        Extract structured recipe data from input.
        Returns tuple of (RecipeBase, extra_metadata_for_persist).
        """
        pass

    async def run(
        self, 
        input_data: Any, 
        source_type: str, 
        source_ref: str, 
        **kwargs
    ) -> Tuple[Recipe, NutritionSummary, List[str]]:
        """
        Run the full ingestion pipeline.
        """
        # 1. Extract
        recipe_base, metadata = await self.extract_recipe_data(input_data, **kwargs)
        
        # 2. Persist
        # Merge metadata with kwargs, metadata takes precedence
        persist_kwargs = {**kwargs, **metadata}
        
        normalized_name = persist_kwargs.get("normalized_name")
        tags = persist_kwargs.get("tags")
        tag_context = persist_kwargs.get("tag_context") or recipe_base.description or recipe_base.name
        
        return await persist_generated_recipe(
            self.db,
            self.llm,
            recipe_base,
            source_type=source_type,
            source_ref=source_ref,
            normalized_name=normalized_name,
            tags=tags,
            tag_context=tag_context,
        )
