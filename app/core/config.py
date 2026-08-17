"""Core configuration singleton for the RAG application."""
from functools import lru_cache
from typing import Any, Dict, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "RAG Pipeline"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # LiteLLM Gateway
    litellm_proxy_url: str = "http://litellm-proxy:4000"
    litellm_timeout_seconds: int = 30
    litellm_max_retries: int = 3
    
    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # Intent Classifier
    intent_classifier_model: str = "deepseek/deepseek-chat-v3-0324:free"
    intent_classifier_timeout: float = 5.0
    
    # Model Routing
    default_model_tier: str = "BALANCED"
    enable_confidence_routing: bool = True
    min_confidence_threshold: float = 0.7
    
    # Haystack Pipeline
    document_store_type: str = "in_memory"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k_retrieval: int = 10
    top_k_rerank: int = 3
    
    # Langfuse
    langfuse_enabled: bool = False
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    enable_correlation_id: bool = True
    
    # Async
    max_concurrent_requests: int = 100
    request_timeout_seconds: int = 60


class ConfigSingleton:
    """
    Singleton pattern for application configuration.
    
    Ensures a single instance of settings is shared across the application,
    providing consistent configuration access with lazy initialization.
    
    Usage:
        config = ConfigSingleton.get_instance()
        settings = config.settings
        api_key = settings.openrouter_api_key
    """
    
    _instance: Optional['ConfigSingleton'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'ConfigSingleton':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self.settings: Settings = Settings()
        self._overrides: Dict[str, Any] = {}
        self._initialized = True
    
    @classmethod
    def get_instance(cls) -> 'ConfigSingleton':
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (primarily for testing)."""
        if cls._instance is not None:
            cls._instance._initialized = False
            cls._instance = None
    
    def override_setting(self, key: str, value: Any) -> None:
        """Override a specific setting (primarily for testing)."""
        self._overrides[key] = value
        if hasattr(self.settings, key):
            setattr(self.settings, key, value)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key."""
        if key in self._overrides:
            return self._overrides[key]
        return getattr(self.settings, key, default)
    
    def reload_settings(self) -> None:
        """Reload settings from environment."""
        self.settings = Settings()
        # Reapply overrides
        for key, value in self._overrides.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Alternative to ConfigSingleton for simple use cases.
    Uses functools.lru_cache for performance.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()


__all__ = ['ConfigSingleton', 'Settings', 'get_settings']
