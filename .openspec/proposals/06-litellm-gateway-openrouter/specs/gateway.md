# LiteLLM Gateway Design

## Configuration

### LiteLLM Proxy Config (litellm_config.yaml)
```yaml
model_list:
  # FAST Tier - Cheap, fast models for simple queries
  - model_name: deepseek-chat
    litellm_params:
      model: openrouter/deepseek/chat
      api_key: os.environ/OPENROUTER_API_KEY
      timeout: 15
      rpm: 100
      tpm: 50000
    
  - model_name: llama-3-8b
    litellm_params:
      model: openrouter/meta-llama/llama-3-8b-instruct
      api_key: os.environ/OPENROUTER_API_KEY
      timeout: 15
      rpm: 100

  # BALANCED Tier - Good balance of cost and capability
  - model_name: llama-3.3-70b
    litellm_params:
      model: openrouter/meta-llama/llama-3.3-70b-instruct
      api_key: os.environ/OPENROUTER_API_KEY
      timeout: 30
      rpm: 50
      tpm: 30000

  - model_name: mixtral-8x22b
    litellm_params:
      model: openrouter/mistralai/mixtral-8x22b-instruct
      api_key: os.environ/OPENROUTER_API_KEY
      timeout: 30
      rpm: 50

  # ADVANCED Tier - High reasoning capability for complex tasks
  - model_name: gpt-4-turbo
    litellm_params:
      model: openrouter/openai/gpt-4-turbo
      api_key: os.environ/OPENROUTER_API_KEY
      timeout: 60
      rpm: 20
      tpm: 10000

  - model_name: claude-3-opus
    litellm_params:
      model: openrouter/anthropic/claude-3-opus
      api_key: os.environ/OPENROUTER_API_KEY
      timeout: 60
      rpm: 20

litellm_settings:
  # Langfuse integration for observability
  callbacks: ["langfuse"]
  
  # Global settings
  set_verbose: False
  drop_params: True
  num_retries: 3
  retry_after: 2
  
  # Cost tracking
  track_cost_callbacks: ["langfuse"]

environment_variables:
  LANGFUSE_PUBLIC_KEY: os.environ/LANGFUSE_PUBLIC_KEY
  LANGFUSE_SECRET_KEY: os.environ/LANGFUSE_SECRET_KEY
  LANGFUSE_HOST: os.environ/LANGFUSE_HOST
```

## Gateway Client Implementation

```python
from typing import Optional, Dict, Any, AsyncIterator
from app.core.protocol import LLMGateway
from app.domain.entities import LLMResponse, LLMChunk, ModelTier
from app.core.exceptions import LiteLLMGatewayError
import aiohttp
import asyncio
from structlog import get_logger

logger = get_logger(__name__)

class LiteLLMGatewayClient:
    """Async client for LiteLLM proxy with OpenRouter integration."""
    
    MODEL_TIER_MAP = {
        ModelTier.FAST: ["deepseek-chat", "llama-3-8b"],
        ModelTier.BALANCED: ["llama-3.3-70b", "mixtral-8x22b"],
        ModelTier.ADVANCED: ["gpt-4-turbo", "claude-3-opus"]
    }
    
    TIMEOUT_MAP = {
        ModelTier.FAST: 15,
        ModelTier.BALANCED: 30,
        ModelTier.ADVANCED: 60
    }
    
    def __init__(
        self,
        proxy_url: str,
        api_key: Optional[str] = None,
        default_timeout: int = 30
    ):
        self.proxy_url = proxy_url.rstrip('/')
        self.api_key = api_key
        self.default_timeout = default_timeout
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.default_timeout)
            )
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        session = await self._get_session()
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            **kwargs
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        try:
            async with session.post(
                f"{self.proxy_url}/v1/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise LiteLLMGatewayError(
                        f"LiteLLM request failed with status {response.status}",
                        context={
                            "status": response.status,
                            "model": model,
                            "error": error_text
                        }
                    )
                
                data = await response.json()
                
                return LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=model,
                    usage=data.get("usage", {}),
                    finish_reason=data["choices"][0].get("finish_reason"),
                    metadata={
                        "provider": "openrouter",
                        "tier": self._get_tier_for_model(model)
                    }
                )
        
        except aiohttp.ClientError as e:
            raise LiteLLMGatewayError(
                f"Connection error to LiteLLM proxy",
                context={"proxy_url": self.proxy_url, "model": model},
                original_exception=e
            )
        except asyncio.TimeoutError:
            raise LiteLLMGatewayError(
                f"Request timed out after {self.default_timeout}s",
                context={"model": model, "timeout": self.default_timeout}
            )
    
    async def generate_stream(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[LLMChunk]:
        session = await self._get_session()
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "stream": True,
            **kwargs
        }
        
        try:
            async with session.post(
                f"{self.proxy_url}/v1/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise LiteLLMGatewayError(
                        f"Streaming request failed with status {response.status}",
                        context={"status": response.status, "model": model}
                    )
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        
                        try:
                            chunk_data = json.loads(data)
                            delta = chunk_data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                yield LLMChunk(
                                    content=content,
                                    model=model,
                                    finish_reason=chunk_data["choices"][0].get("finish_reason")
                                )
                        except json.JSONDecodeError:
                            continue
        
        except aiohttp.ClientError as e:
            raise LiteLLMGatewayError(
                "Streaming connection error",
                context={"model": model},
                original_exception=e
            )
    
    def _get_tier_for_model(self, model: str) -> str:
        for tier, models in self.MODEL_TIER_MAP.items():
            if any(m in model for m in models):
                return tier.value
        return "unknown"
    
    async def health_check(self) -> bool:
        session = await self._get_session()
        try:
            async with session.get(f"{self.proxy_url}/health") as response:
                return response.status == 200
        except Exception:
            return False
```

## Usage Example

```python
# Initialize gateway
gateway = LiteLLMGatewayClient(
    proxy_url="http://litellm-proxy:4000",
    api_key=settings.OPENROUTER_API_KEY
)

# Generate with FAST tier model
response = await gateway.generate(
    prompt="What is Python?",
    model="deepseek-chat",
    temperature=0.3
)

print(f"Response: {response.content}")
print(f"Tokens used: {response.usage}")

# Streaming generation
async for chunk in gateway.generate_stream(
    prompt="Write a story about AI",
    model="llama-3.3-70b",
    temperature=0.7
):
    print(chunk.content, end='', flush=True)
```

## Langfuse Integration at Proxy Level

The LiteLLM proxy configuration includes Langfuse callbacks that automatically:
- Trace all LLM requests and responses
- Track token consumption per model
- Calculate costs based on provider pricing
- Record latency metrics
- Capture errors and retries

No additional code needed in the application - all telemetry happens at the proxy layer.
