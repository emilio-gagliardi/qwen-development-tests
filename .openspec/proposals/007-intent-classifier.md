# Proposal: Intent Classification System

## Overview
Implement a fast, cost-effective intent classification system using cheap models to categorize user queries before routing to appropriate model tiers.

## Requirements

### Intent Types

#### Supported Intents
```python
class IntentType(str, Enum):
    SIMPLE_QUESTION = "simple_question"      # Factual, straightforward
    COMPLEX_REASONING = "complex_reasoning"  # Multi-step logic required
    CREATIVE_TASK = "creative_task"          # Writing, brainstorming
    TECHNICAL_QUERY = "technical_query"       # Code, technical docs
    CONVERSATIONAL = "conversational"         # Chat, casual interaction
    AMBIGUOUS = "ambiguous"                   # Unclear intent
```

#### Intent Definitions
| Intent | Description | Example | Target Tier |
|--------|-------------|---------|-------------|
| simple_question | Direct factual questions | "What is Python?" | Fast |
| complex_reasoning | Multi-step analysis | "Compare these architectures..." | Advanced |
| creative_task | Content generation | "Write a poem about..." | Balanced |
| technical_query | Code/technical docs | "How do I fix this error?" | Balanced |
| conversational | Casual chat | "How are you today?" | Fast |
| ambiguous | Unclear requests | "Tell me stuff" | Balanced |

### Classification Model

#### Model Selection
- **Primary**: `openrouter/deepseek/deepseek-chat` (fast, ~$0.14/1M tokens)
- **Fallback**: Rule-based keyword matching if LLM unavailable
- **Temperature**: 0.1 (deterministic classification)
- **Max Tokens**: 50 (just need the intent label)

#### Classification Prompt
```python
CLASSIFICATION_PROMPT = """
Classify the user's query into exactly ONE of these intents:
- simple_question: Direct factual questions with clear answers
- complex_reasoning: Requires multi-step analysis or comparison
- creative_task: Writing, brainstorming, or content creation
- technical_query: Code, debugging, or technical documentation
- conversational: Casual chat or social interaction
- ambiguous: Unclear or too vague to classify

Return ONLY the intent name, nothing else.

Query: {query}

Intent:"""
```

### Implementation

#### Async Intent Classifier
```python
class AsyncIntentClassifier:
    def __init__(
        self,
        gateway: ILLMGateway,
        settings: Settings,
        fallback_threshold: float = 0.6
    ):
        self._gateway = gateway
        self._settings = settings
        self._fallback_threshold = fallback_threshold
        self._supported_intents = [e.value for e in IntentType]
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_CLASSIFICATIONS)
    
    async def classify(self, query: str) -> IntentClassification:
        async with self._semaphore:
            try:
                # LLM-based classification with timeout
                prompt = CLASSIFICATION_PROMPT.format(query=query)
                response = await with_timeout(
                    self._gateway.generate(
                        prompt=prompt,
                        model=self._settings.CLASSIFICATION_MODEL,
                        temperature=0.1,
                        max_tokens=50
                    ),
                    timeout=self._settings.CLASSIFICATION_TIMEOUT,
                    operation="intent_classification"
                )
                
                intent_text = response.content.strip().lower()
                confidence = self._calculate_confidence(response, intent_text)
                
                return IntentClassification(
                    intent_type=self._parse_intent(intent_text),
                    confidence=confidence,
                    method="llm",
                    model_used=self._settings.CLASSIFICATION_MODEL,
                    processing_time_ms=response.usage.total_time_ms
                )
            
            except (GenerationException, asyncio.TimeoutError) as e:
                logger.warning("LLM classification failed, using fallback", error=str(e))
                return self._rule_based_classify(query)
    
    def _rule_based_classify(self, query: str) -> IntentClassification:
        """Fallback rule-based classification"""
        query_lower = query.lower()
        
        # Simple keyword matching
        if any(word in query_lower for word in ["what is", "define", "explain"]):
            intent = IntentType.SIMPLE_QUESTION
            confidence = 0.5
        elif any(word in query_lower for word in ["compare", "analyze", "evaluate"]):
            intent = IntentType.COMPLEX_REASONING
            confidence = 0.5
        elif any(word in query_lower for word in ["write", "create", "generate"]):
            intent = IntentType.CREATIVE_TASK
            confidence = 0.5
        elif any(word in query_lower for word in ["code", "error", "debug", "fix"]):
            intent = IntentType.TECHNICAL_QUERY
            confidence = 0.5
        elif "?" in query or len(query.split()) < 5:
            intent = IntentType.CONVERSATIONAL
            confidence = 0.4
        else:
            intent = IntentType.AMBIGUOUS
            confidence = 0.3
        
        return IntentClassification(
            intent_type=intent,
            confidence=confidence,
            method="rule_based",
            model_used=None,
            processing_time_ms=0
        )
    
    def _calculate_confidence(self, response: LLMResponse, intent_text: str) -> float:
        """Calculate confidence based on response clarity"""
        if intent_text in self._supported_intents:
            return 0.9
        elif any(intent in intent_text for intent in self._supported_intents):
            return 0.7
        else:
            return 0.5
    
    def _parse_intent(self, intent_text: str) -> IntentType:
        """Parse intent string to enum"""
        for intent in IntentType:
            if intent.value in intent_text:
                return intent
        return IntentType.AMBIGUOUS
```

### Integration with Model Router

#### Confidence-Based Routing Adjustments
```python
def adjust_routing_based_on_confidence(
    intent: IntentClassification,
    initial_decision: ModelRoutingDecision
) -> ModelRoutingDecision:
    """Upgrade/downgrade model tier based on classification confidence"""
    
    if intent.confidence < 0.5:
        # Low confidence - upgrade to better model for safety
        if initial_decision.tier == ModelTier.FAST:
            return ModelRoutingDecision(
                tier=ModelTier.BALANCED,
                selected_model=initial_decision.selected_model.replace("fast", "balanced"),
                reasoning=f"Low classification confidence ({intent.confidence}), upgrading tier"
            )
    
    elif intent.confidence > 0.95 and intent.intent_type == IntentType.SIMPLE_QUESTION:
        # Very high confidence simple question - ensure fast tier
        return ModelRoutingDecision(
            tier=ModelTier.FAST,
            selected_model=get_fast_model(),
            reasoning=f"High confidence simple question ({intent.confidence})"
        )
    
    return initial_decision
```

### Performance Optimization

#### Caching Frequent Queries
```python
from cachetools import TTLCache

class CachedIntentClassifier:
    def __init__(self, classifier: AsyncIntentClassifier, cache_ttl: int = 300):
        self._classifier = classifier
        self._cache: dict[str, IntentClassification] = TTLCache(maxsize=1000, ttl=cache_ttl)
    
    async def classify(self, query: str) -> IntentClassification:
        # Normalize query for caching
        normalized = self._normalize_query(query)
        
        if normalized in self._cache:
            cached = self._cache[normalized]
            logger.debug("Intent cache hit", query_hash=hash(normalized))
            return cached
        
        result = await self._classifier.classify(query)
        self._cache[normalized] = result
        return result
    
    def _normalize_query(self, query: str) -> str:
        # Lowercase, remove extra whitespace, strip punctuation
        normalized = query.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[^\w\s?]', '', normalized)
        return normalized
```

### Testing Strategy

#### Unit Tests
```python
async def test_simple_question_classification():
    classifier = AsyncIntentClassifier(mock_gateway, settings)
    result = await classifier.classify("What is the capital of France?")
    assert result.intent_type == IntentType.SIMPLE_QUESTION
    assert result.confidence > 0.8
    assert result.method == "llm"

async def test_fallback_on_timeout():
    mock_gateway.generate.side_effect = asyncio.TimeoutError()
    classifier = AsyncIntentClassifier(mock_gateway, settings)
    result = await classifier.classify("What is AI?")
    assert result.method == "rule_based"
    assert result.confidence == 0.5
```

#### Integration Tests
- Verify end-to-end classification latency < 500ms (P95)
- Test fallback behavior when LLM unavailable
- Validate confidence thresholds trigger correct routing adjustments

## Acceptance Criteria
1. Six intent types implemented and documented
2. LLM-based classification with DeepSeek Chat model
3. Rule-based fallback when LLM fails
4. Confidence scores returned with each classification
5. Classification timeout < 2 seconds
6. Cache hit rate > 30% for repeated queries
7. Unit tests cover all intent types and fallback
8. Integration with model router for confidence-based adjustments
