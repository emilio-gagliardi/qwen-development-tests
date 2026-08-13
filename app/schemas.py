"""Pydantic schemas for the RAG pipeline."""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from enum import Enum


class IntentType(str, Enum):
    """Types of user intents."""
    SIMPLE = "simple"
    COMPLEX = "complex"
    TECHNICAL = "technical"
    CREATIVE = "creative"


class ModelTier(str, Enum):
    """Model tiers based on capability and cost."""
    FAST = "fast"  # For simple queries
    BALANCED = "balanced"  # For moderate complexity
    ADVANCED = "advanced"  # For complex/nuanced queries


class RAGRequest(BaseModel):
    """Request schema for RAG queries."""
    query: str = Field(..., description="The user's query")
    include_sources: bool = Field(
        default=True, 
        description="Whether to include document sources in response"
    )
    max_tokens: int = Field(
        default=512, 
        ge=64, 
        le=4096, 
        description="Maximum tokens in response"
    )


class IntentClassification(BaseModel):
    """Schema for intent classification results."""
    intent_type: IntentType = Field(..., description="Classified intent type")
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence score of classification"
    )
    reasoning: Optional[str] = Field(
        None, 
        description="Optional reasoning for the classification"
    )


class ModelRoutingDecision(BaseModel):
    """Schema for model routing decisions."""
    selected_model: str = Field(..., description="Selected model identifier")
    model_tier: ModelTier = Field(..., description="Tier of the selected model")
    routing_reason: str = Field(..., description="Reason for model selection")


class DocumentSource(BaseModel):
    """Schema for retrieved document sources."""
    content: str = Field(..., description="Document content snippet")
    metadata: dict = Field(default_factory=dict, description="Document metadata")
    score: float = Field(..., description="Relevance score")


class RAGResponse(BaseModel):
    """Response schema for RAG queries."""
    answer: str = Field(..., description="Generated answer")
    model_used: str = Field(..., description="Model that generated the response")
    intent: Optional[IntentClassification] = Field(
        None, 
        description="Intent classification details"
    )
    sources: Optional[List[DocumentSource]] = Field(
        None, 
        description="Retrieved document sources"
    )
    processing_time_ms: float = Field(
        ..., 
        description="Total processing time in milliseconds"
    )


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(..., description="Service health status")
    litellm_gateway: bool = Field(..., description="LiteLLM gateway availability")
    timestamp: str = Field(..., description="Response timestamp")


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: str = Field(..., description="Error code")
