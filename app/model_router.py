"""Model router for selecting appropriate LLM based on query characteristics."""

from app.config import Settings
from app.schemas import IntentType, ModelTier, ModelRoutingDecision, IntentClassification
from app.gateway import LiteLLMGateway


class ModelRouter:
    """Routes queries to appropriate models based on intent and complexity.
    
    This component implements the routing logic that maps classified intents
    to specific model tiers, optimizing for cost, latency, and quality.
    
    Routing Strategy:
    - SIMPLE → FAST tier (cost-effective, low latency)
    - COMPLEX → ADVANCED tier (high capability, nuanced understanding)
    - TECHNICAL → BALANCED or ADVANCED (depends on confidence)
    - CREATIVE → BALANCED (good balance of creativity and coherence)
    """
    
    def __init__(self, settings: Settings, gateway: LiteLLMGateway):
        self.settings = settings
        self.gateway = gateway
        
        # Define routing rules
        self.intent_to_tier_map = {
            IntentType.SIMPLE: ModelTier.FAST,
            IntentType.COMPLEX: ModelTier.ADVANCED,
            IntentType.TECHNICAL: ModelTier.BALANCED,  # Can be upgraded based on confidence
            IntentType.CREATIVE: ModelTier.BALANCED,
        }
        
        # Confidence thresholds for upgrading model tier
        self.upgrade_threshold = 0.85
        self.downgrade_threshold = 0.5
    
    def _determine_tier(self, intent: IntentClassification) -> ModelTier:
        """Determine the appropriate model tier based on intent classification.
        
        Args:
            intent: IntentClassification result
            
        Returns:
            ModelTier for the query
        """
        base_tier = self.intent_to_tier_map.get(
            intent.intent_type, 
            ModelTier.BALANCED
        )
        
        # Adjust tier based on confidence
        if intent.confidence >= self.upgrade_threshold:
            # High confidence in complex/technical → upgrade to advanced
            if intent.intent_type in [IntentType.TECHNICAL, IntentType.COMPLEX]:
                return ModelTier.ADVANCED
        
        elif intent.confidence <= self.downgrade_threshold:
            # Low confidence → use balanced as safe default
            if base_tier == ModelTier.FAST:
                return ModelTier.BALANCED
        
        return base_tier
    
    def _generate_routing_reason(
        self, 
        intent: IntentClassification, 
        tier: ModelTier
    ) -> str:
        """Generate human-readable reasoning for the routing decision.
        
        Args:
            intent: IntentClassification result
            tier: Selected ModelTier
            
        Returns:
            Reasoning string
        """
        reasons = {
            (IntentType.SIMPLE, ModelTier.FAST): "Simple query routed to fast model for efficiency",
            (IntentType.SIMPLE, ModelTier.BALANCED): "Simple query with low confidence, using balanced model",
            (IntentType.COMPLEX, ModelTier.ADVANCED): "Complex query requiring advanced reasoning capabilities",
            (IntentType.COMPLEX, ModelTier.BALANCED): "Complex query with moderate confidence",
            (IntentType.TECHNICAL, ModelTier.ADVANCED): "Technical query with high confidence, using advanced model",
            (IntentType.TECHNICAL, ModelTier.BALANCED): "Technical query routed to balanced model",
            (IntentType.CREATIVE, ModelTier.BALANCED): "Creative query routed to balanced model for optimal creativity",
            (IntentType.CREATIVE, ModelTier.ADVANCED): "Complex creative query requiring advanced capabilities",
        }
        
        key = (intent.intent_type, tier)
        if key in reasons:
            return reasons[key]
        
        return f"Routed to {tier.value} tier based on {intent.intent_type.value} intent (confidence: {intent.confidence:.2f})"
    
    def route(self, intent: IntentClassification) -> ModelRoutingDecision:
        """Route a classified intent to an appropriate model.
        
        Args:
            intent: IntentClassification from the intent classifier
            
        Returns:
            ModelRoutingDecision with selected model and reasoning
        """
        # Determine the model tier
        tier = self._determine_tier(intent)
        
        # Get the actual model identifier for this tier
        model = self.gateway.get_model_for_tier(tier)
        
        # Generate routing reason
        reason = self._generate_routing_reason(intent, tier)
        
        return ModelRoutingDecision(
            selected_model=model,
            model_tier=tier,
            routing_reason=reason
        )
    
    def get_all_available_models(self) -> dict[str, str]:
        """Get all available models mapped by tier.
        
        Returns:
            Dictionary mapping tier names to model identifiers
        """
        return {
            "fast": self.gateway.get_model_for_tier(ModelTier.FAST),
            "balanced": self.gateway.get_model_for_tier(ModelTier.BALANCED),
            "advanced": self.gateway.get_model_for_tier(ModelTier.ADVANCED),
        }
    
    def explain_routing_for_intent(self, intent_type: IntentType) -> str:
        """Explain the routing strategy for a given intent type.
        
        Args:
            intent_type: The intent type to explain
            
        Returns:
            Explanation string
        """
        explanations = {
            IntentType.SIMPLE: (
                "Simple queries (basic facts, straightforward questions) are routed to fast, "
                "cost-effective models to minimize latency and cost while maintaining quality."
            ),
            IntentType.COMPLEX: (
                "Complex queries (multi-step reasoning, comparisons, detailed analysis) require "
                "advanced models with strong reasoning capabilities to provide accurate responses."
            ),
            IntentType.TECHNICAL: (
                "Technical queries (programming, engineering, science) are routed to balanced or "
                "advanced models depending on confidence level, ensuring technical accuracy."
            ),
            IntentType.CREATIVE: (
                "Creative queries (writing, brainstorming, design) use balanced models that offer "
                "good creativity while maintaining coherence and relevance."
            ),
        }
        
        return explanations.get(
            intent_type,
            "Default routing strategy applies balanced models for unknown intent types."
        )
