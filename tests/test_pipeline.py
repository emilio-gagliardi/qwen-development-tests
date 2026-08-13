"""Test suite for the RAG pipeline components."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.schemas import (
    IntentType, 
    ModelTier, 
    IntentClassification, 
    ModelRoutingDecision,
    RAGRequest,
)
from app.config import Settings
from app.gateway import LiteLLMGateway
from app.intent_classifier import IntentClassifier
from app.model_router import ModelRouter


class TestSchemas:
    """Test Pydantic schemas."""
    
    def test_rag_request_validation(self):
        """Test RAGRequest validation."""
        # Valid request
        request = RAGRequest(query="What is Python?")
        assert request.query == "What is Python?"
        assert request.include_sources is True
        assert request.max_tokens == 512
        
        # Request with custom parameters
        request = RAGRequest(
            query="Explain ML",
            include_sources=False,
            max_tokens=256
        )
        assert request.include_sources is False
        assert request.max_tokens == 256
        
        # Validation error for max_tokens out of range
        with pytest.raises(Exception):
            RAGRequest(query="test", max_tokens=32)  # Below minimum
    
    def test_intent_classification_schema(self):
        """Test IntentClassification schema."""
        intent = IntentClassification(
            intent_type=IntentType.COMPLEX,
            confidence=0.92,
            reasoning="Multi-step reasoning required"
        )
        assert intent.intent_type == IntentType.COMPLEX
        assert intent.confidence == 0.92
        
        # Confidence must be between 0 and 1
        with pytest.raises(Exception):
            IntentClassification(intent_type=IntentType.SIMPLE, confidence=1.5)
    
    def test_model_routing_decision_schema(self):
        """Test ModelRoutingDecision schema."""
        decision = ModelRoutingDecision(
            selected_model="gpt-4",
            model_tier=ModelTier.ADVANCED,
            routing_reason="Complex query requiring advanced capabilities"
        )
        assert decision.selected_model == "gpt-4"
        assert decision.model_tier == ModelTier.ADVANCED


class TestIntentClassifier:
    """Test intent classification logic."""
    
    def test_rule_based_technical_classification(self):
        """Test rule-based classification for technical queries."""
        settings = Settings()
        gateway = MagicMock(spec=LiteLLMGateway)
        
        classifier = IntentClassifier(settings, gateway)
        
        # Technical query with multiple keywords
        result = classifier._rule_based_classification(
            "How do I debug this Python API error with database connection?"
        )
        assert result == IntentType.TECHNICAL
    
    def test_rule_based_creative_classification(self):
        """Test rule-based classification for creative queries."""
        settings = Settings()
        gateway = MagicMock(spec=LiteLLMGateway)
        
        classifier = IntentClassifier(settings, gateway)
        
        result = classifier._rule_based_classification(
            "Write a creative story about designing an imaginary world"
        )
        assert result == IntentType.CREATIVE
    
    def test_rule_based_complex_classification(self):
        """Test rule-based classification for complex queries."""
        settings = Settings()
        gateway = MagicMock(spec=LiteLLMGateway)
        
        classifier = IntentClassifier(settings, gateway)
        
        result = classifier._rule_based_classification(
            "Compare and contrast different approaches, explain why each works"
        )
        assert result == IntentType.COMPLEX
    
    def test_rule_based_simple_classification(self):
        """Test rule-based classification for simple queries."""
        settings = Settings()
        gateway = MagicMock(spec=LiteLLMGateway)
        
        classifier = IntentClassifier(settings, gateway)
        
        result = classifier._rule_based_classification("What is the capital of France?")
        assert result == IntentType.SIMPLE


class TestModelRouter:
    """Test model routing logic."""
    
    @pytest.fixture
    def router_setup(self):
        """Set up router for testing."""
        settings = Settings()
        gateway = MagicMock(spec=LiteLLMGateway)
        gateway.get_model_for_tier.side_effect = lambda tier: {
            ModelTier.FAST: "gpt-3.5-turbo",
            ModelTier.BALANCED: "gpt-4",
            ModelTier.ADVANCED: "gpt-4-turbo",
        }[tier]
        
        router = ModelRouter(settings, gateway)
        return router
    
    def test_route_simple_intent(self, router_setup):
        """Test routing for simple intent."""
        router = router_setup
        
        intent = IntentClassification(
            intent_type=IntentType.SIMPLE,
            confidence=0.95,
            reasoning="Simple factual question"
        )
        
        decision = router.route(intent)
        assert decision.model_tier == ModelTier.FAST
        assert decision.selected_model == "gpt-3.5-turbo"
    
    def test_route_complex_intent_high_confidence(self, router_setup):
        """Test routing for complex intent with high confidence."""
        router = router_setup
        
        intent = IntentClassification(
            intent_type=IntentType.COMPLEX,
            confidence=0.92,
            reasoning="Requires multi-step reasoning"
        )
        
        decision = router.route(intent)
        assert decision.model_tier == ModelTier.ADVANCED
        assert decision.selected_model == "gpt-4-turbo"
    
    def test_route_technical_intent_upgrade(self, router_setup):
        """Test routing for technical intent with confidence-based upgrade."""
        router = router_setup
        
        intent = IntentClassification(
            intent_type=IntentType.TECHNICAL,
            confidence=0.90,  # Above upgrade threshold
            reasoning="Technical query with high confidence"
        )
        
        decision = router.route(intent)
        # Should be upgraded to ADVANCED due to high confidence
        assert decision.model_tier == ModelTier.ADVANCED
    
    def test_route_low_confidence_downgrade(self, router_setup):
        """Test routing with low confidence downgrade."""
        router = router_setup
        
        intent = IntentClassification(
            intent_type=IntentType.SIMPLE,
            confidence=0.40,  # Below downgrade threshold
            reasoning="Uncertain classification"
        )
        
        decision = router.route(intent)
        # Should be downgraded from FAST to BALANCED
        assert decision.model_tier == ModelTier.BALANCED


class TestLiteLLMGateway:
    """Test LiteLLM gateway client."""
    
    def test_get_model_for_tier(self):
        """Test model tier mapping."""
        settings = Settings()
        gateway = LiteLLMGateway(settings)
        
        assert gateway.get_model_for_tier(ModelTier.FAST) == settings.fast_model
        assert gateway.get_model_for_tier(ModelTier.BALANCED) == settings.balanced_model
        assert gateway.get_model_for_tier(ModelTier.ADVANCED) == settings.advanced_model
    
    @pytest.mark.asyncio
    async def test_generate_completion_payload(self):
        """Test completion request payload construction."""
        settings = Settings()
        gateway = LiteLLMGateway(settings)
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test response"}}]
        }
        
        with patch.object(gateway, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client
            
            await gateway.generate_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="gpt-3.5-turbo",
                max_tokens=100,
                temperature=0.5,
            )
            
            # Verify the call was made with correct payload
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "/chat/completions"
            payload = call_args[1]["json"]
            assert payload["model"] == "gpt-3.5-turbo"
            assert payload["max_tokens"] == 100
            assert payload["temperature"] == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
