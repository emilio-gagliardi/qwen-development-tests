"""LiteLLM Gateway client for unified LLM access."""

import httpx
from typing import AsyncGenerator, Optional
from datetime import datetime

from app.config import Settings
from app.schemas import ModelTier


class LiteLLMGateway:
    """Client for interacting with the LiteLLM proxy server.
    
    This gateway provides a unified interface to multiple LLM providers
    through the LiteLLM proxy, enabling seamless model switching and routing.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.litellm_base_url
        self.api_key = settings.litellm_api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(30.0, connect=5.0)
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    def get_model_for_tier(self, tier: ModelTier) -> str:
        """Get model identifier for a given tier."""
        model_mapping = {
            ModelTier.FAST: self.settings.fast_model,
            ModelTier.BALANCED: self.settings.balanced_model,
            ModelTier.ADVANCED: self.settings.advanced_model,
        }
        return model_mapping.get(tier, self.settings.balanced_model)
    
    async def generate_completion(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> dict:
        """Generate a completion using the specified model.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (e.g., 'gpt-4', 'claude-2')
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            stream: Whether to stream the response
            
        Returns:
            Completion response from the LLM
        """
        client = await self._get_client()
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        
        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        
        return response.json()
    
    async def generate_with_retry(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int = 512,
        max_retries: int = 2,
    ) -> dict:
        """Generate completion with retry logic for transient failures.
        
        Args:
            messages: List of message dicts
            model: Model identifier
            max_tokens: Maximum tokens
            max_retries: Number of retry attempts
            
        Returns:
            Completion response
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return await self.generate_completion(
                    messages=messages,
                    model=model,
                    max_tokens=max_tokens,
                )
            except httpx.HTTPError as e:
                last_error = e
                if attempt < max_retries:
                    # Wait before retry (exponential backoff could be added)
                    pass
        
        raise RuntimeError(f"Failed after {max_retries} retries: {last_error}")
    
    async def check_health(self) -> bool:
        """Check if the LiteLLM gateway is healthy.
        
        Returns:
            True if gateway is available, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get("/health/liveliness")
            return response.status_code == 200
        except Exception:
            # Try alternative health endpoint
            try:
                response = await client.get("/")
                return response.status_code in [200, 404]  # 404 is OK for root
            except Exception:
                return False
