"""
Custom exception hierarchy for the RAG application.

Provides a structured set of exceptions with error codes for consistent
error handling across the application. All exceptions inherit from
RAGBaseException which includes correlation ID support for tracing.
"""
from typing import Any, Dict, Optional
from uuid import UUID


class RAGBaseException(Exception):
    """
    Base exception for all RAG application errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code
        correlation_id: Request correlation ID for tracing
        details: Additional error context
        original_exception: Original exception if this is a wrapper
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        correlation_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.correlation_id = correlation_id
        self.details = details or {}
        self.original_exception = original_exception
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        result = {
            "error_code": self.error_code,
            "message": self.message,
            "type": self.__class__.__name__,
        }
        
        if self.correlation_id:
            result["correlation_id"] = str(self.correlation_id)
        
        if self.details:
            result["details"] = self.details
        
        return result
    
    def __str__(self) -> str:
        """String representation with error code."""
        return f"[{self.error_code}] {self.message}"


# =============================================================================
# Configuration Errors (1000-1999)
# =============================================================================

class ConfigurationError(RAGBaseException):
    """Base exception for configuration-related errors."""
    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""
    
    def __init__(self, setting_name: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Required configuration '{setting_name}' is missing",
            error_code="CONFIG_MISSING",
            details={"setting_name": setting_name},
            **kwargs
        )


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration value is invalid."""
    
    def __init__(self, setting_name: str, reason: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Invalid configuration '{setting_name}': {reason}",
            error_code="CONFIG_INVALID",
            details={"setting_name": setting_name, "reason": reason},
            **kwargs
        )


# =============================================================================
# Validation Errors (2000-2999)
# =============================================================================

class ValidationError(RAGBaseException):
    """Base exception for validation errors."""
    pass


class QueryValidationError(ValidationError):
    """Raised when query validation fails."""
    
    def __init__(self, reason: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Query validation failed: {reason}",
            error_code="QUERY_VALIDATION_ERROR",
            details={"reason": reason},
            **kwargs
        )


class DocumentValidationError(ValidationError):
    """Raised when document validation fails."""
    
    def __init__(self, reason: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Document validation failed: {reason}",
            error_code="DOCUMENT_VALIDATION_ERROR",
            details={"reason": reason},
            **kwargs
        )


# =============================================================================
# Intent Classification Errors (3000-3999)
# =============================================================================

class IntentClassificationError(RAGBaseException):
    """Base exception for intent classification errors."""
    pass


class IntentClassificationTimeoutError(IntentClassificationError):
    """Raised when intent classification times out."""
    
    def __init__(self, timeout_seconds: float, **kwargs: Any) -> None:
        super().__init__(
            message=f"Intent classification timed out after {timeout_seconds}s",
            error_code="INTENT_CLASSIFICATION_TIMEOUT",
            details={"timeout_seconds": timeout_seconds},
            **kwargs
        )


class IntentClassificationFailureError(IntentClassificationError):
    """Raised when intent classification fails."""
    
    def __init__(self, reason: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Intent classification failed: {reason}",
            error_code="INTENT_CLASSIFICATION_FAILURE",
            details={"reason": reason},
            **kwargs
        )


# =============================================================================
# Model Routing Errors (4000-4999)
# =============================================================================

class ModelRoutingError(RAGBaseException):
    """Base exception for model routing errors."""
    pass


class ModelNotFoundError(ModelRoutingError):
    """Raised when requested model is not found."""
    
    def __init__(self, model_name: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Model '{model_name}' not found",
            error_code="MODEL_NOT_FOUND",
            details={"model_name": model_name},
            **kwargs
        )


class ModelRoutingFailureError(ModelRoutingError):
    """Raised when model routing fails."""
    
    def __init__(self, reason: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Model routing failed: {reason}",
            error_code="MODEL_ROUTING_FAILURE",
            details={"reason": reason},
            **kwargs
        )


# =============================================================================
# LLM Gateway Errors (5000-5999)
# =============================================================================

class LLMGatewayError(RAGBaseException):
    """Base exception for LLM gateway errors."""
    pass


class LLMGatewayConnectionError(LLMGatewayError):
    """Raised when connection to LLM gateway fails."""
    
    def __init__(self, gateway_url: str, reason: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Failed to connect to LLM gateway at {gateway_url}: {reason}",
            error_code="LLM_GATEWAY_CONNECTION_ERROR",
            details={"gateway_url": gateway_url, "reason": reason},
            **kwargs
        )


class LLMGatewayTimeoutError(LLMGatewayError):
    """Raised when LLM gateway request times out."""
    
    def __init__(self, timeout_seconds: int, **kwargs: Any) -> None:
        super().__init__(
            message=f"LLM gateway request timed out after {timeout_seconds}s",
            error_code="LLM_GATEWAY_TIMEOUT",
            details={"timeout_seconds": timeout_seconds},
            **kwargs
        )


class LLMGatewayRateLimitError(LLMGatewayError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after_seconds: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(
            message="Rate limit exceeded",
            error_code="LLM_GATEWAY_RATE_LIMIT",
            details={"retry_after_seconds": retry_after_seconds},
            **kwargs
        )


class LLMGenerationError(LLMGatewayError):
    """Raised when LLM generation fails."""
    
    def __init__(self, model: str, reason: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"LLM generation failed for model '{model}': {reason}",
            error_code="LLM_GENERATION_ERROR",
            details={"model": model, "reason": reason},
            **kwargs
        )


# =============================================================================
# Repository Errors (6000-6999)
# =============================================================================

class RepositoryError(RAGBaseException):
    """Base exception for repository errors."""
    pass


class DocumentNotFoundError(RepositoryError):
    """Raised when document is not found."""
    
    def __init__(self, document_id: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Document '{document_id}' not found",
            error_code="DOCUMENT_NOT_FOUND",
            details={"document_id": document_id},
            **kwargs
        )


class RepositoryOperationError(RepositoryError):
    """Raised when repository operation fails."""
    
    def __init__(self, operation: str, reason: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Repository operation '{operation}' failed: {reason}",
            error_code="REPOSITORY_OPERATION_ERROR",
            details={"operation": operation, "reason": reason},
            **kwargs
        )


# =============================================================================
# Pipeline Errors (7000-7999)
# =============================================================================

class PipelineError(RAGBaseException):
    """Base exception for pipeline errors."""
    pass


class PipelineExecutionError(PipelineError):
    """Raised when pipeline execution fails."""
    
    def __init__(self, stage: str, reason: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Pipeline execution failed at stage '{stage}': {reason}",
            error_code="PIPELINE_EXECUTION_ERROR",
            details={"stage": stage, "reason": reason},
            **kwargs
        )


class RerankerError(PipelineError):
    """Raised when reranking fails."""
    
    def __init__(self, reason: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Reranking failed: {reason}",
            error_code="RERANKER_ERROR",
            details={"reason": reason},
            **kwargs
        )


# =============================================================================
# Infrastructure Errors (8000-8999)
# =============================================================================

class InfrastructureError(RAGBaseException):
    """Base exception for infrastructure errors."""
    pass


class ServiceUnavailableError(InfrastructureError):
    """Raised when external service is unavailable."""
    
    def __init__(self, service_name: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Service '{service_name}' is unavailable",
            error_code="SERVICE_UNAVAILABLE",
            details={"service_name": service_name},
            **kwargs
        )


# =============================================================================
# API Errors (9000-9999)
# =============================================================================

class APIError(RAGBaseException):
    """Base exception for API errors."""
    pass


class BadRequestError(APIError):
    """Raised for bad request errors."""
    
    def __init__(self, message: str = "Bad request", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code="BAD_REQUEST",
            **kwargs
        )


class AuthenticationError(APIError):
    """Raised for authentication errors."""
    
    def __init__(self, reason: str = "Authentication failed", **kwargs: Any) -> None:
        super().__init__(
            message=reason,
            error_code="AUTHENTICATION_ERROR",
            **kwargs
        )


__all__ = [
    # Base
    'RAGBaseException',
    
    # Configuration (1000s)
    'ConfigurationError',
    'MissingConfigurationError',
    'InvalidConfigurationError',
    
    # Validation (2000s)
    'ValidationError',
    'QueryValidationError',
    'DocumentValidationError',
    
    # Intent Classification (3000s)
    'IntentClassificationError',
    'IntentClassificationTimeoutError',
    'IntentClassificationFailureError',
    
    # Model Routing (4000s)
    'ModelRoutingError',
    'ModelNotFoundError',
    'ModelRoutingFailureError',
    
    # LLM Gateway (5000s)
    'LLMGatewayError',
    'LLMGatewayConnectionError',
    'LLMGatewayTimeoutError',
    'LLMGatewayRateLimitError',
    'LLMGenerationError',
    
    # Repository (6000s)
    'RepositoryError',
    'DocumentNotFoundError',
    'RepositoryOperationError',
    
    # Pipeline (7000s)
    'PipelineError',
    'PipelineExecutionError',
    'RerankerError',
    
    # Infrastructure (8000s)
    'InfrastructureError',
    'ServiceUnavailableError',
    
    # API (9000s)
    'APIError',
    'BadRequestError',
    'AuthenticationError',
]
