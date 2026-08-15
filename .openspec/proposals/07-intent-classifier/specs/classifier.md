# Intent Classifier Design

## Intent Types Enum

```python
from enum import Enum

class IntentType(str, Enum):
    FACTUAL_QUERY = "factual_query"
    TECHNICAL_QUESTION = "technical_question"
    CREATIVE_TASK = "creative_task"
    ANALYSIS_REQUEST = "analysis_request"
    SIMPLE_CHAT = "simple_chat"
    COMPLEX_REASONING = "complex_reasoning"
```

## Classification Prompt

```python
CLASSIFICATION_PROMPT = """You are an intent classifier for a RAG system. Classify the user query into exactly one of these intent types:

- FACTUAL_QUERY: Seeking factual information, definitions, explanations (e.g., "What is Python?", "Who invented the telephone?")
- TECHNICAL_QUESTION: Technical/programming questions, code-related (e.g., "How do I fix this bug?", "Write a function to...")
- CREATIVE_TASK: Creative writing, brainstorming, storytelling (e.g., "Write a poem about...", "Give me ideas for...")
- ANALYSIS_REQUEST: Analysis, comparison, evaluation, pros/cons (e.g., "Compare X and Y", "Analyze the impact of...")
- SIMPLE_CHAT: Casual conversation, greetings, thanks (e.g., "Hello", "Thank you", "How are you?")
- COMPLEX_REASONING: Multi-step reasoning, problem solving, math, logic (e.g., "Solve this step by step...", "If A then B, and B then C...")

Respond ONLY with a JSON object in this exact format:
{"intent": "<INTENT_TYPE>", "confidence": <0.0-1.0>, "reasoning": "<brief explanation>"}

Query: {query}
"""
```

## Classifier Implementation

```python
from typing import Optional, Dict, Any
from app.core.protocol import IntentClassifier as IntentClassifierProtocol
from app.domain.entities import IntentClassification, IntentType
from app.core.exceptions import IntentClassificationError, ConfidenceThresholdError
import asyncio
import json
import re

class IntentClassifierImpl:
    """LLM-based intent classifier with rule-based fallback."""
    
    CONFIDENCE_THRESHOLD = 0.6
    CLASSIFICATION_TIMEOUT = 5
    
    def __init__(self, gateway, model: str = "deepseek-chat"):
        self.gateway = gateway
        self.model = model
    
    async def classify(self, query: str) -> IntentClassification:
        try:
            # Try LLM classification with timeout
            result = await asyncio.wait_for(
                self._llm_classify(query),
                timeout=self.CLASSIFICATION_TIMEOUT
            )
            
            if result.confidence >= self.CONFIDENCE_THRESHOLD:
                return result
            
            # Low confidence - use fallback
            return self._rule_based_classify(query)
        
        except asyncio.TimeoutError:
            # Timeout - use fallback
            return self._rule_based_classify(query)
        
        except Exception as e:
            # Any error - use fallback
            return self._rule_based_classify(query)
    
    async def _llm_classify(self, query: str) -> IntentClassification:
        prompt = CLASSIFICATION_PROMPT.format(query=query)
        
        response = await self.gateway.generate(
            prompt=prompt,
            model=self.model,
            temperature=0.1,  # Low temp for consistent classification
            max_tokens=150
        )
        
        try:
            # Parse JSON response
            content = response.content.strip()
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if not match:
                raise IntentClassificationError(
                    "Invalid classification response format",
                    context={"response": content}
                )
            
            data = json.loads(match.group())
            
            intent_type = IntentType(data["intent"])
            confidence = float(data["confidence"])
            reasoning = data.get("reasoning", "")
            
            return IntentClassification(
                intent_type=intent_type,
                confidence=confidence,
                reasoning=reasoning,
                model_used=self.model
            )
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise IntentClassificationError(
                "Failed to parse classification response",
                context={"error": str(e)},
                original_exception=e
            )
    
    def _rule_based_classify(self, query: str) -> IntentClassification:
        """Fallback rule-based classification."""
        query_lower = query.lower()
        
        # Simple chat patterns
        if any(p in query_lower for p in ["hello", "hi ", "hey", "thank", "bye", "goodbye"]):
            return IntentClassification(
                intent_type=IntentType.SIMPLE_CHAT,
                confidence=0.8,
                reasoning="Rule-based: greeting/courtesy pattern detected",
                model_used="rule-based"
            )
        
        # Technical question patterns
        if any(p in query_lower for p in ["code", "function", "bug", "error", "python", "javascript", "api"]):
            return IntentClassification(
                intent_type=IntentType.TECHNICAL_QUESTION,
                confidence=0.7,
                reasoning="Rule-based: technical keywords detected",
                model_used="rule-based"
            )
        
        # Creative task patterns
        if any(p in query_lower for p in ["write", "story", "poem", "ideas", "brainstorm", "creative"]):
            return IntentClassification(
                intent_type=IntentType.CREATIVE_TASK,
                confidence=0.7,
                reasoning="Rule-based: creative keywords detected",
                model_used="rule-based"
            )
        
        # Analysis patterns
        if any(p in query_lower for p in ["compare", "analyze", "pros and cons", "advantages", "disadvantages"]):
            return IntentClassification(
                intent_type=IntentType.ANALYSIS_REQUEST,
                confidence=0.7,
                reasoning="Rule-based: analysis keywords detected",
                model_used="rule-based"
            )
        
        # Complex reasoning patterns
        if any(p in query_lower for p in ["solve", "step by step", "calculate", "prove", "if ", "then "]):
            return IntentClassification(
                intent_type=IntentType.COMPLEX_REASONING,
                confidence=0.65,
                reasoning="Rule-based: reasoning keywords detected",
                model_used="rule-based"
            )
        
        # Default to factual
        return IntentClassification(
            intent_type=IntentType.FACTUAL_QUERY,
            confidence=0.5,
            reasoning="Rule-based: default to factual query",
            model_used="rule-based"
        )
    
    async def classify_batch(
        self, 
        queries: list[str]
    ) -> list[IntentClassification]:
        results = await asyncio.gather(
            *[self.classify(query) for query in queries],
            return_exceptions=True
        )
        
        classifications = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Fallback for failed classifications
                classifications.append(self._rule_based_classify(queries[i]))
            else:
                classifications.append(result)
        
        return classifications
```

## Usage Example

```python
# Initialize classifier
classifier = IntentClassifierImpl(gateway)

# Classify single query
classification = await classifier.classify("What is the capital of France?")
print(f"Intent: {classification.intent_type}")
print(f"Confidence: {classification.confidence}")
print(f"Model: {classification.model_used}")

# Batch classification
queries = ["Hello!", "Write a poem", "Fix this bug"]
classifications = await classifier.classify_batch(queries)
```
