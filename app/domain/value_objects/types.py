"""Domain value objects for type-safe business logic."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import re


class IntentType(str, Enum):
    """Types of user intents that can be classified."""
    
    SIMPLE_FACT = "simple_fact"
    COMPLEX_REASONING = "complex_reasoning"
    CREATIVE_TASK = "creative_task"
    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    CLARIFICATION = "clarification"
    
    @classmethod
    def from_string(cls, value: str) -> 'IntentType':
        """Create IntentType from string with validation."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(
                f"Invalid intent type: {value}. "
                f"Valid values: {[e.value for e in cls]}"
            )


class ModelTier(str, Enum):
    """Tiers of LLM models based on capability and cost."""
    
    FAST = "FAST"
    BALANCED = "BALANCED"
    ADVANCED = "ADVANCED"
    
    @property
    def description(self) -> str:
        """Get human-readable description of the tier."""
        descriptions = {
            self.FAST: "Fast, cheap models for simple tasks",
            self.BALANCED: "Balanced performance and cost",
            self.ADVANCED: "High-capability models for complex reasoning",
        }
        return descriptions.get(self, "Unknown tier")
    
    @classmethod
    def from_string(cls, value: str) -> 'ModelTier':
        """Create ModelTier from string with validation."""
        try:
            return cls(value.upper())
        except ValueError:
            raise ValueError(
                f"Invalid model tier: {value}. "
                f"Valid values: {[e.value for e in cls]}"
            )


@dataclass(frozen=True)
class ConfidenceScore:
    """
    Value object representing a confidence score with validation.
    
    Ensures confidence scores are always in the valid range [0.0, 1.0].
    Immutable (frozen) to prevent accidental modification.
    
    Attributes:
        value: The confidence score between 0.0 and 1.0
        
    Usage:
        score = ConfidenceScore(0.85)
        print(score.value)  # 0.85
        print(score.is_high())  # True
    """
    value: float
    
    def __post_init__(self) -> None:
        """Validate confidence score after initialization."""
        if not isinstance(self.value, (int, float)):
            raise TypeError("Confidence score must be a number")
        
        if self.value < 0.0 or self.value > 1.0:
            raise ValueError(
                f"Confidence score must be between 0.0 and 1.0, got {self.value}"
            )
    
    def is_high(self, threshold: float = 0.7) -> bool:
        """Check if confidence is above threshold."""
        return self.value >= threshold
    
    def is_medium(self, low_threshold: float = 0.4, high_threshold: float = 0.7) -> bool:
        """Check if confidence is in medium range."""
        return low_threshold <= self.value < high_threshold
    
    def is_low(self, threshold: float = 0.4) -> bool:
        """Check if confidence is below threshold."""
        return self.value < threshold
    
    def to_percentage(self) -> int:
        """Convert to percentage (0-100)."""
        return int(round(self.value * 100))
    
    def __str__(self) -> str:
        """String representation with percentage."""
        return f"{self.to_percentage()}%"
    
    def __float__(self) -> float:
        """Convert to float."""
        return self.value


@dataclass(frozen=True)
class ModelName:
    """
    Value object representing an LLM model name with validation.
    
    Validates model names follow the provider/model pattern.
    
    Attributes:
        value: The model name string
        provider: Extracted provider name (if present)
        model: Extracted model identifier
    """
    value: str
    
    def __post_init__(self) -> None:
        """Validate model name format."""
        if not self.value or not self.value.strip():
            raise ValueError("Model name cannot be empty")
        
        # Basic validation for provider/model format
        if '/' in self.value:
            parts = self.value.split('/', 1)
            if len(parts) != 2 or not all(parts):
                raise ValueError(
                    f"Invalid model name format: {self.value}. "
                    "Expected 'provider/model' format"
                )
    
    @property
    def provider(self) -> Optional[str]:
        """Extract provider name from model identifier."""
        if '/' in self.value:
            return self.value.split('/', 1)[0]
        return None
    
    @property
    def model(self) -> str:
        """Extract model identifier."""
        if '/' in self.value:
            return self.value.split('/', 1)[1]
        return self.value
    
    def __str__(self) -> str:
        """String representation."""
        return self.value


__all__ = ['IntentType', 'ModelTier', 'ConfidenceScore', 'ModelName']
