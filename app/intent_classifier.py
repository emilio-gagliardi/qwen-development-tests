"""Intent classifier for analyzing user requests."""

import re
from typing import Optional
from app.config import Settings
from app.schemas import IntentType, IntentClassification
from app.gateway import LiteLLMGateway


class IntentClassifier:
    """Classifies user queries by intent and complexity.
    
    This component analyzes incoming user requests to determine:
    - The type of intent (simple, complex, technical, creative)
    - Confidence level of the classification
    - Reasoning behind the classification
    
    This enables intelligent model routing based on query characteristics.
    """
    
    def __init__(self, settings: Settings, gateway: LiteLLMGateway):
        self.settings = settings
        self.gateway = gateway
        
        # Keywords for rule-based pre-classification (fallback)
        self.technical_keywords = {
            'api', 'code', 'programming', 'debug', 'error', 'stack',
            'database', 'sql', 'query', 'algorithm', 'complexity',
            'architecture', 'deployment', 'kubernetes', 'docker',
            'microservice', 'endpoint', 'authentication', 'encryption'
        }
        
        self.creative_keywords = {
            'write', 'create', 'story', 'poem', 'imagine', 'design',
            'brainstorm', 'ideate', 'conceptualize', 'artistic',
            'metaphor', 'analogy', 'creative', 'invent'
        }
        
        self.complexity_indicators = {
            'compare', 'contrast', 'analyze', 'evaluate', 'critique',
            'synthesize', 'explain why', 'how does', 'what if',
            'pros and cons', 'advantages disadvantages',
            'step by step', 'detailed explanation'
        }
    
    def _rule_based_classification(self, query: str) -> Optional[IntentType]:
        """Perform rule-based classification as fallback.
        
        Args:
            query: User query text
            
        Returns:
            IntentType if classification is clear, None otherwise
        """
        query_lower = query.lower()
        words = set(re.findall(r'\b\w+\b', query_lower))
        
        # Check for technical content
        tech_matches = len(words & self.technical_keywords)
        if tech_matches >= 2:
            return IntentType.TECHNICAL
        
        # Check for creative content
        creative_matches = len(words & self.creative_keywords)
        if creative_matches >= 2:
            return IntentType.CREATIVE
        
        # Check for complexity indicators
        complexity_matches = sum(1 for indicator in self.complexity_indicators 
                                if indicator in query_lower)
        if complexity_matches >= 2:
            return IntentType.COMPLEX
        
        # Default to simple if no strong signals
        if tech_matches == 0 and creative_matches == 0 and complexity_matches == 0:
            return IntentType.SIMPLE
        
        return None
    
    async def classify(self, query: str) -> IntentClassification:
        """Classify a user query using LLM-based analysis.
        
        Uses the LiteLLM gateway to analyze the query and determine
        its intent type, confidence, and reasoning.
        
        Args:
            query: The user's query text
            
        Returns:
            IntentClassification with type, confidence, and reasoning
        """
        # Try rule-based classification first (fast path)
        rule_based = self._rule_based_classification(query)
        
        # Use LLM for nuanced classification
        system_prompt = """You are an intent classifier for a RAG pipeline. 
Classify user queries into one of these categories:
- SIMPLE: Basic factual questions, straightforward requests
- COMPLEX: Multi-step reasoning, comparisons, detailed explanations
- TECHNICAL: Programming, engineering, scientific topics
- CREATIVE: Writing, brainstorming, artistic requests

Respond in JSON format:
{
    "intent_type": "<one of SIMPLE|COMPLEX|TECHNICAL|CREATIVE>",
    "confidence": <0.0-1.0>,
    "reasoning": "<brief explanation>"
}"""

        user_message = f"Classify this query: {query}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        try:
            response = await self.gateway.generate_completion(
                messages=messages,
                model=self.settings.classifier_model,
                max_tokens=150,
                temperature=0.3,  # Lower temperature for consistency
            )
            
            # Parse the response
            content = response["choices"][0]["message"]["content"]
            
            # Extract JSON from response (handle potential markdown formatting)
            import json
            import re
            
            # Try to extract JSON block
            json_match = re.search(r'\{[^}]*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return IntentClassification(
                    intent_type=IntentType(result["intent_type"].lower()),
                    confidence=float(result["confidence"]),
                    reasoning=result.get("reasoning")
                )
            
            # Fallback to rule-based if parsing fails
            if rule_based:
                return IntentClassification(
                    intent_type=rule_based,
                    confidence=0.6,
                    reasoning="Rule-based classification (LLM parsing failed)"
                )
            
            # Default fallback
            return IntentClassification(
                intent_type=IntentType.SIMPLE,
                confidence=0.5,
                reasoning="Default classification"
            )
            
        except Exception as e:
            # Fallback to rule-based classification on error
            if rule_based:
                return IntentClassification(
                    intent_type=rule_based,
                    confidence=0.6,
                    reasoning=f"Rule-based classification (LLM error: {str(e)})"
                )
            
            return IntentClassification(
                intent_type=IntentType.SIMPLE,
                confidence=0.5,
                reasoning=f"Default classification (LLM error: {str(e)})"
            )
    
    async def classify_with_timeout(self, query: str) -> IntentClassification:
        """Classify with timeout protection.
        
        Args:
            query: User query text
            
        Returns:
            IntentClassification result
        """
        import asyncio
        
        try:
            return await asyncio.wait_for(
                self.classify(query),
                timeout=self.settings.classifier_timeout
            )
        except asyncio.TimeoutError:
            # Return simple classification on timeout
            return IntentClassification(
                intent_type=IntentType.SIMPLE,
                confidence=0.5,
                reasoning="Classification timeout - defaulted to simple"
            )
