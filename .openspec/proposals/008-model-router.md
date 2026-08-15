# Proposal: Model Router with Tier Selection

## Overview
Implement an intelligent model router that selects the appropriate model tier based on intent classification, confidence scores, and query complexity to optimize cost and performance.

## Requirements

### Model Tiers

#### Tier Definitions
```python
class ModelTier(str, Enum):
    FAST = "fast"         # Low cost, fast response, simple tasks
    BALANCED = "balanced" # Moderate cost/speed, general purpose
    ADVANCED = "advanced" # Higher cost, complex reasoning
```

#### Tier Configuration
| Tier | Models | Max Tokens | Temperature Range | Use Cases |
|------|--------|------------|-------------------|-----------|
| FAST | deepseek-chat | 4K | 0.1-0.3 | Simple Q&A, classification, chat |
| BALANCED | deepseek-v3 | 8K | 0.3-0.7 | General chat, technical queries, creative |
| ADVANCED | llama-3.3-70b | 16K | 0.5-0.9 | Complex reasoning, analysis, nuanced tasks |

### Routing Logic

#### Intent-to-Tier Mapping
```python
INTENT_TIER_MAP = {
    IntentType.SIMPLE_QUESTION: ModelTier.FAST,
    IntentType.CONVERSATIONAL: ModelTier.FAST,
    IntentType.TECHNICAL_QUERY: ModelTier.BALANCED,
    IntentType.CREATIVE_TASK: ModelTier.BALANCED,
    IntentType.AMBIGUOUS: ModelTier.BALANCED,
    IntentType.COMPLEX_REASONING: ModelTier.ADVANCED,
}
```

#### Router Implementation
```python
class AsyncModelRouter:
    def __init__(self, settings: Settings, model_registry: ModelRegistry):
        self._settings = settings
        self._registry = model_registry
        self._intent_tier_map = INTENT_TIER_MAP
        self._tier_models = {
            ModelTier.FAST: settings.FAST_MODEL_NAME,
            ModelTier.BALANCED: settings.BALANCED_MODEL_NAME,
            ModelTier.ADVANCED: settings.ADVANCED_MODEL_NAME,
        }
    
    def route(self, intent: IntentClassification) -> ModelRoutingDecision:
        """Route intent to appropriate model tier"""
        
        # Base tier from intent type
        base_tier = self._intent_tier_map.get(
            intent.intent_type,
            ModelTier.BALANCED
        )
        
        # Adjust based on confidence
        adjusted_tier = self._adjust_for_confidence(base_tier, intent.confidence)
        
        # Adjust for query characteristics
        final_tier = self._adjust_for_query_characteristics(adjusted_tier, intent)
        
        # Select specific model
        selected_model = self._tier_models[final_tier]
        
        # Determine temperature
        temperature = self._get_temperature(final_tier, intent.intent_type)
        
        return ModelRoutingDecision(
            tier=final_tier,
            selected_model=selected_model,
            temperature=temperature,
            max_tokens=self._get_max_tokens(final_tier),
            reasoning=self._build_reasoning(intent, base_tier, final_tier),
            fallback_tier=self._get_fallback_tier(final_tier)
        )
    
    def _adjust_for_confidence(self, tier: ModelTier, confidence: float) -> ModelTier:
        """Upgrade tier if confidence is low"""
        if confidence < 0.5 and tier == ModelTier.FAST:
            return ModelTier.BALANCED
        return tier
    
    def _adjust_for_query_characteristics(
        self,
        tier: ModelTier,
        intent: IntentClassification
    ) -> ModelTier:
        """Additional adjustments based on query metadata"""
        # Could analyze query length, presence of technical terms, etc.
        # For now, keep base tier
        return tier
    
    def _get_temperature(self, tier: ModelTier, intent_type: IntentType) -> float:
        """Get appropriate temperature for tier and intent"""
        temp_ranges = {
            ModelTier.FAST: (0.1, 0.3),
            ModelTier.BALANCED: (0.3, 0.7),
            ModelTier.ADVANCED: (0.5, 0.9),
        }
        
        min_temp, max_temp = temp_ranges[tier]
        
        # Adjust within range based on intent
        if intent_type in [IntentType.SIMPLE_QUESTION, IntentType.TECHNICAL_QUERY]:
            return min_temp + (max_temp - min_temp) * 0.2
        elif intent_type in [IntentType.CREATIVE_TASK]:
            return min_temp + (max_temp - min_temp) * 0.8
        else:
            return min_temp + (max_temp - min_temp) * 0.5
    
    def _get_max_tokens(self, tier: ModelTier) -> int:
        """Get max tokens for tier"""
        max_tokens_map = {
            ModelTier.FAST: 4096,
            ModelTier.BALANCED: 8192,
            ModelTier.ADVANCED: 16384,
        }
        return max_tokens_map[tier]
    
    def _get_fallback_tier(self, tier: ModelTier) -> ModelTier | None:
        """Get fallback tier if primary fails"""
        fallback_map = {
            ModelTier.ADVANCED: ModelTier.BALANCED,
            ModelTier.BALANCED: ModelTier.FAST,
            ModelTier.FAST: None,
        }
        return fallback_map[tier]
    
    def _build_reasoning(
        self,
        intent: IntentClassification,
        base_tier: ModelTier,
        final_tier: ModelTier
    ) -> str:
        """Build human-readable routing explanation"""
        reasons = []
        reasons.append(f"Intent: {intent.intent_type.value}")
        reasons.append(f"Confidence: {intent.confidence:.2f}")
        
        if final_tier != base_tier:
            if final_tier.value > base_tier.value:  # Upgraded
                reasons.append("Upgraded due to low confidence")
            else:  # Downgraded (unlikely but possible)
                reasons.append("Downgraded based on query analysis")
        
        return "; ".join(reasons)
```

### Routing Strategies

#### Strategy Pattern for Custom Routing
```python
class RoutingStrategy(Protocol):
    def select_tier(self, intent: IntentClassification) -> ModelTier:
        """Select tier based on intent"""
        ...

class DefaultRoutingStrategy:
    def __init__(self, intent_tier_map: dict[IntentType, ModelTier]):
        self._map = intent_tier_map
    
    def select_tier(self, intent: IntentClassification) -> ModelTier:
        return self._map.get(intent.intent_type, ModelTier.BALANCED)

class CostOptimizedRoutingStrategy:
    """Aggressively routes to cheaper tiers when possible"""
    
    def select_tier(self, intent: IntentClassification) -> ModelTier:
        base_tier = INTENT_TIER_MAP.get(intent.intent_type, ModelTier.BALANCED)
        
        # Only use ADVANCED if very high confidence and truly complex
        if base_tier == ModelTier.ADVANCED and intent.confidence < 0.9:
            return ModelTier.BALANCED
        
        # Downgrade ambiguous to FAST
        if intent.intent_type == IntentType.AMBIGUOUS and intent.confidence < 0.4:
            return ModelTier.FAST
        
        return base_tier

class QualityFirstRoutingStrategy:
    """Prioritizes quality over cost"""
    
    def select_tier(self, intent: IntentClassification) -> ModelTier:
        base_tier = INTENT_TIER_MAP.get(intent.intent_type, ModelTier.BALANCED)
        
        # Upgrade any low confidence to ADVANCED
        if intent.confidence < 0.6 and base_tier != ModelTier.ADVANCED:
            return ModelTier.ADVANCED
        
        return base_tier
```

### Strategy Registry
```python
class StrategyRegistry:
    _strategies: dict[str, RoutingStrategy] = {}
    
    @classmethod
    def register(cls, name: str, strategy: RoutingStrategy) -> None:
        cls._strategies[name] = strategy
    
    @classmethod
    def get(cls, name: str) -> RoutingStrategy:
        if name not in cls._strategies:
            raise ValueError(f"Unknown strategy: {name}")
        return cls._strategies[name]
    
    @classmethod
    def list_strategies(cls) -> list[str]:
        return list(cls._strategies.keys())

# Register default strategies
StrategyRegistry.register("default", DefaultRoutingStrategy(INTENT_TIER_MAP))
StrategyRegistry.register("cost_optimized", CostOptimizedRoutingStrategy())
StrategyRegistry.register("quality_first", QualityFirstRoutingStrategy())
```

### API Endpoint for Routing Explanation

```python
@app.get("/routing/explain/{intent_type}")
async def explain_routing(
    intent_type: IntentType,
    confidence: float = 0.8,
    strategy: str = "default"
) -> RoutingExplanation:
    """Explain routing decision for given intent"""
    
    intent = IntentClassification(
        intent_type=intent_type,
        confidence=confidence,
        method="hypothetical"
    )
    
    router_strategy = StrategyRegistry.get(strategy)
    tier = router_strategy.select_tier(intent)
    model = router._tier_models[tier]
    
    return RoutingExplanation(
        intent_type=intent_type,
        confidence=confidence,
        selected_tier=tier,
        selected_model=model,
        strategy=strategy,
        reasoning=f"Based on {strategy} strategy, {intent_type.value} with {confidence:.2f} confidence routes to {tier.value} tier"
    )
```

### Cost Optimization

#### Expected Cost per Query
| Tier | Model | Avg Input Tokens | Avg Output Tokens | Cost/Query |
|------|-------|------------------|-------------------|------------|
| FAST | deepseek-chat | 200 | 300 | ~$0.00007 |
| BALANCED | deepseek-v3 | 300 | 400 | ~$0.00019 |
| ADVANCED | llama-3.3-70b | 400 | 500 | ~$0.00036 |

#### Monthly Cost Projection (10K queries/day)
Assuming distribution: 50% FAST, 40% BALANCED, 10% ADVANCED
- FAST: 150K queries × $0.00007 = $10.50
- BALANCED: 120K queries × $0.00019 = $22.80
- ADVANCED: 30K queries × $0.00036 = $10.80
- **Total: ~$44/month** vs ~$120/month if all used ADVANCED

### Testing

#### Unit Tests
```python
def test_simple_question_routes_to_fast():
    router = AsyncModelRouter(settings, registry)
    intent = IntentClassification(
        intent_type=IntentType.SIMPLE_QUESTION,
        confidence=0.9,
        method="llm"
    )
    decision = router.route(intent)
    assert decision.tier == ModelTier.FAST
    assert "deepseek-chat" in decision.selected_model

def test_low_confidence_upgrades_tier():
    router = AsyncModelRouter(settings, registry)
    intent = IntentClassification(
        intent_type=IntentType.SIMPLE_QUESTION,
        confidence=0.3,  # Low confidence
        method="llm"
    )
    decision = router.route(intent)
    assert decision.tier == ModelTier.BALANCED  # Upgraded from FAST
```

#### Integration Tests
- Verify routing decisions logged to Langfuse
- Test fallback chain when model unavailable
- Validate cost tracking accuracy

## Acceptance Criteria
1. Three model tiers implemented (FAST, BALANCED, ADVANCED)
2. Intent-to-tier mapping configurable
3. Confidence-based tier adjustments working
4. Multiple routing strategies available
5. Temperature selection based on tier and intent
6. Routing explanations returned with decisions
7. Fallback chain configured for each tier
8. Cost projections documented and tracked
9. Unit tests cover all routing scenarios
