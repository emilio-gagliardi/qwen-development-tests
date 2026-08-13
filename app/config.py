"""Configuration settings for the RAG pipeline."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # LiteLLM Gateway Configuration
    litellm_base_url: str = Field(
        default="http://localhost:4000",
        description="LiteLLM proxy server URL"
    )
    litellm_api_key: Optional[str] = Field(
        default=None,
        description="API key for LiteLLM (if required)"
    )
    
    # Model Configuration
    fast_model: str = Field(
        default="gpt-3.5-turbo",
        description="Model for simple/fast queries"
    )
    balanced_model: str = Field(
        default="gpt-4",
        description="Model for balanced queries"
    )
    advanced_model: str = Field(
        default="gpt-4-turbo",
        description="Model for complex/advanced queries"
    )
    
    # Intent Classifier Configuration
    classifier_model: str = Field(
        default="gpt-3.5-turbo",
        description="Model used for intent classification"
    )
    classifier_timeout: float = Field(
        default=5.0,
        description="Timeout for intent classification in seconds"
    )
    
    # RAG Configuration
    max_retrieved_docs: int = Field(
        default=5,
        description="Maximum number of documents to retrieve"
    )
    min_relevance_score: float = Field(
        default=0.7,
        description="Minimum relevance score for retrieved documents"
    )
    
    # Service Configuration
    service_name: str = Field(
        default="rag-pipeline",
        description="Service name for identification"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    class Config:
        env_prefix = "RAG_"
        env_file = ".env"
        case_sensitive = False
