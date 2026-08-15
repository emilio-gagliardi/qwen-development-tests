# Model Router Design

## Model Tier Enum

```python
from enum import Enum

class ModelTier(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    ADVANCED = "advanced"
```

## Routing Configuration

```python
from typing import Dict, List
from app.domain.entities import IntentType, ModelTier

ROUTING_CONFIG = {
    IntentType.SIMPLE_CHAT: {
        "default_tier": ModelTier.FAST,
        "confidence_thresholds": [],  # No upgrades
        "models": ["deepseek-chat", "llama-3-8b"]
    },
    IntentType.FACTUAL_QUERY: {
        "default_tier": ModelTier.FAST,
        "confidence_thresholds": [
            {"threshold": 0.8, "tier": ModelTier.FAST},
            {"threshold": 0.0, "tier": ModelTier.BALANCED}  # Fallback
        ],
        "models": ["deepseek-chat", "llama-3.3-70b"]
    },
    IntentType.TECHNICAL_QUESTION: {
        "default_tier": ModelTier.BALANCED,
        "confidence_thresholds": [
            {"threshold": 0.7, "tier": ModelTier.BALANCED},
            {"threshold": 0.0, "tier": ModelTier.ADVANCED}  # Low confidence upgrade
        ],
        "models": ["llama-3.3-70b", "gpt-4-turbo"]
    },
    IntentType.CREATIVE_TASK: {
        "default_tier": ModelTier.BALANCED,
        "confidence_thresholds": [],
        "models": ["llama-3.3-70b", "mixtral-8x22b"]
    },
    IntentType.ANALYSIS_REQUEST: {
        "default_tier": ModelTier.ADVANCED,
        "confidence_thresholds": [],  # Always advanced
        "models": ["gpt-4-turbo", "claude-3-opus"]
    },
    IntentType.COMPLEX_REASONING: {
        "default_tier": ModelTier.ADVANCED,
        "confidence_thresholds": [],  # Always advanced
        "models": ["gpt-4-turbo", "claude-3-opus"]
    }
}

COST_PER_MILLION_TOKENS = {
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "llama-3-8b": {"input": 0.05, "output": 0.10},
    "llama-3.3-70b": {"input": 0.39, "output": 0.50},
    "mixtral-8x22b": {"input": 0.27, "output": 0.36},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "claude-3-opus": {"input": 15.0, "output": 75.0}
}
```

## Router Implementation

```python
from typing import Optional, Dict, Any
from app.core.protocol import ModelRouter as ModelRouterProtocol
from app.domain.entities import ModelRoutingDecision, ModelTier, IntentType
from app.core.exceptions import ModelRoutingError, InvalidModelTierError

class ModelRouterImpl:
    """Intent-based model router with cost optimization."""
    
    def __init__(self):
        self.config = ROUTING_CONFIG
    
    async def route(
        self,
        intent: IntentType,
        confidence: float,
        context: Optional[Dict[str, Any]] = None
    ) -> ModelRoutingDecision:
        if intent not in self.config:
            raise ModelRoutingError(
                f"No routing config for intent: {intent}",
                context={"intent": intent.value}
            )
        
        intent_config = self.config[intent]
        
        # Determine tier based on confidence thresholds
        selected_tier = intent_config["default_tier"]
        for threshold_config in intent_config.get("confidence_thresholds", []):
            if confidence >= threshold_config["threshold"]:
                selected_tier = threshold_config["tier"]
                break
        
        # Select best model from tier
        available_models = intent_config["models"]
        selected_model = available_models[0]  # Could add load balancing here
        
        return ModelRoutingDecision(
            tier=selected_tier,
            model_id=selected_model,
            reasoning=self._generate_reasoning(intent, confidence, selected_tier),
            estimated_cost_per_million=self._get_model_cost(selected_model)
        )
    
    def _generate_reasoning(
        self,
        intent: IntentType,
        confidence: float,
        tier: ModelTier
    ) -> str:
        return (
            f"Routed to {tier.value} tier based on intent={intent.value} "
            f"with confidence={confidence:.2f}"
        )
    
    def _get_model_cost(self, model: str) -> Dict[str, float]:
        return COST_PER_MILLION_TOKENS.get(model, {"input": 0, "output": 0})
    
    def get_routing_explanation(self, intent: IntentType) -> str:
        if intent not in self.config:
            return f"No routing information for intent: {intent.value}"
        
        config = self.config[intent]
        explanation = f"Intent '{intent.value}' routes to {config['default_tier'].value} tier by default.\n"
        
        if config.get("confidence_thresholds"):
            explanation += "Confidence-based adjustments:\n"
            for tc in config["confidence_thresholds"]:
                explanation += f"  - If confidence >= {tc['threshold']}: use {tc['tier'].value} tier\n"
        
        explanation += f"Available models: {', '.join(config['models'])}"
        return explanation
```

## Usage Example

```python
router = ModelRouterImpl()

# Route based on classification
decision = await router.route(
    intent=IntentType.TECHNICAL_QUESTION,
    confidence=0.85
)

print(f"Selected tier: {decision.tier}")
print(f"Selected model: {decision.model_id}")
print(f"Reasoning: {decision.reasoning}")
print(f"Estimated cost: ${decision.estimated_cost_per_million['input']}/M input tokens")

# Get routing explanation
explanation = router.get_routing_explanation(IntentType.COMPLEX_REASONING)
print(explanation)
```
