"""
Model Configuration Registry for OpenAI API

This module provides a model-agnostic interface for managing different OpenAI models
and their specific parameter requirements. It handles parameter mapping, version
compatibility, and graceful fallback for breaking API changes.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for a specific OpenAI model"""
    
    model_name: str
    display_name: str
    max_tokens_param: str  # 'max_tokens' for GPT-4, 'max_completion_tokens' for GPT-5
    max_tokens_value: int
    temperature: float = 0.7
    temperature_min: float = 0.0
    temperature_max: float = 2.0
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    supports_verbosity: bool = False
    supports_json_mode: bool = True
    context_window: int = 128000
    deprecated: bool = False
    available_from: Optional[str] = None  # ISO date string
    sunset_date: Optional[str] = None  # ISO date string
    fallback_params: Dict[str, Any] = field(default_factory=dict)
    
    def build_api_params(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Dynamically build API parameters based on model requirements
        
        Args:
            messages: List of message dictionaries for the API
            **kwargs: Additional parameters to override defaults
            
        Returns:
            Dictionary of API parameters tailored for this model
        """
        params = {
            "model": self.model_name,
            "messages": messages,
            self.max_tokens_param: kwargs.get('max_tokens', self.max_tokens_value),
            "temperature": max(self.temperature_min, 
                             min(kwargs.get('temperature', self.temperature), 
                                 self.temperature_max))
        }
        
        # Add model-specific features
        if self.supports_verbosity and 'verbosity' in kwargs:
            params["verbosity"] = kwargs['verbosity']
            
        if self.supports_json_mode and kwargs.get('response_format') == 'json':
            params["response_format"] = {"type": "json_object"}
            
        # Apply any additional model-specific parameters
        for key, value in self.fallback_params.items():
            if key not in params:
                params[key] = value
                
        return params
    
    def migrate_params(self, old_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate parameters from old format to current model's format
        
        Args:
            old_params: Parameters in potentially outdated format
            
        Returns:
            Parameters migrated to current model's format
        """
        migrated = old_params.copy()
        
        # Handle max_tokens -> max_completion_tokens migration
        if 'max_tokens' in migrated and self.max_tokens_param == 'max_completion_tokens':
            migrated['max_completion_tokens'] = migrated.pop('max_tokens')
        elif 'max_completion_tokens' in migrated and self.max_tokens_param == 'max_tokens':
            migrated['max_tokens'] = migrated.pop('max_completion_tokens')
            
        # Ensure temperature is within model's bounds
        if 'temperature' in migrated:
            migrated['temperature'] = max(self.temperature_min,
                                        min(migrated['temperature'], 
                                           self.temperature_max))
        
        return migrated
    
    def is_available(self) -> bool:
        """Check if model is currently available"""
        if self.deprecated:
            return False
            
        now = datetime.now().isoformat()
        
        if self.available_from and now < self.available_from:
            return False
            
        if self.sunset_date and now > self.sunset_date:
            return False
            
        return True
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for a given token usage
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        input_cost = (input_tokens / 1000) * self.cost_per_1k_input
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output
        return input_cost + output_cost


class ModelRegistry:
    """Registry for managing multiple model configurations"""
    
    def __init__(self):
        self.models: Dict[str, ModelConfig] = {}
        self._initialize_default_models()
        
    def _initialize_default_models(self):
        """Initialize with known model configurations"""
        
        # Current model - GPT-4o-mini
        self.register(ModelConfig(
            model_name="gpt-4o-mini",
            display_name="GPT-4o Mini",
            max_tokens_param="max_tokens",
            max_tokens_value=150,
            temperature=0.7,
            temperature_min=0.0,
            temperature_max=2.0,
            cost_per_1k_input=0.00015,
            cost_per_1k_output=0.0006,
            supports_verbosity=False,
            supports_json_mode=True,
            context_window=128000,
            deprecated=False
        ))
        
        # Future model - GPT-4.1-mini (Q1 2026)
        self.register(ModelConfig(
            model_name="gpt-4.1-mini",
            display_name="GPT-4.1 Mini",
            max_tokens_param="max_tokens",
            max_tokens_value=1000,
            temperature=0.3,
            temperature_min=0.0,
            temperature_max=2.0,
            cost_per_1k_input=0.00007,  # $0.07 per 1M input tokens (53% cheaper)
            cost_per_1k_output=0.00028,  # Estimated proportional reduction
            supports_verbosity=True,
            supports_json_mode=True,
            context_window=256000,  # 2x context window
            deprecated=False,
            available_from="2026-01-01T00:00:00"
        ))
        
        # Future model - GPT-5-nano (Mid 2026)
        self.register(ModelConfig(
            model_name="gpt-5-nano",
            display_name="GPT-5 Nano",
            max_tokens_param="max_completion_tokens",  # Breaking change
            max_tokens_value=250,
            temperature=0.5,  # Different default
            temperature_min=0.0,
            temperature_max=1.0,  # Lower max temperature
            cost_per_1k_input=0.00008,  # Even cheaper
            cost_per_1k_output=0.00032,
            supports_verbosity=True,
            supports_json_mode=True,
            context_window=512000,  # 4x context window
            deprecated=False,
            available_from="2026-06-01T00:00:00",
            fallback_params={
                "reasoning_effort": "low"  # New GPT-5 parameter
            }
        ))
        
        # Future model - GPT-5-mini (Mid 2026)
        self.register(ModelConfig(
            model_name="gpt-5-mini",
            display_name="GPT-5 Mini",
            max_tokens_param="max_completion_tokens",  # Breaking change
            max_tokens_value=500,
            temperature=0.5,
            temperature_min=0.0,
            temperature_max=1.0,  # Lower max temperature
            cost_per_1k_input=0.00015,
            cost_per_1k_output=0.0006,
            supports_verbosity=True,
            supports_json_mode=True,
            context_window=1024000,  # 8x context window
            deprecated=False,
            available_from="2026-06-01T00:00:00",
            fallback_params={
                "reasoning_effort": "medium"  # New GPT-5 parameter
            }
        ))
        
    def register(self, config: ModelConfig) -> None:
        """Register a new model configuration"""
        self.models[config.model_name] = config
        logger.info(f"Registered model: {config.display_name} ({config.model_name})")
        
    def get(self, model_name: str) -> Optional[ModelConfig]:
        """Get a model configuration by name"""
        return self.models.get(model_name)
        
    def get_available_models(self) -> List[ModelConfig]:
        """Get list of currently available models"""
        return [model for model in self.models.values() if model.is_available()]
        
    def get_default_model(self) -> ModelConfig:
        """Get the default model (currently GPT-4o-mini)"""
        return self.models["gpt-4o-mini"]
        
    def get_all_models(self) -> List[ModelConfig]:
        """Get all registered models (including future/deprecated)"""
        return list(self.models.values())


# Global registry instance
model_registry = ModelRegistry()


class ModelAdapter:
    """Adapter for making API calls with automatic parameter migration"""
    
    def __init__(self, api_client):
        """
        Initialize the adapter with an OpenAI client
        
        Args:
            api_client: OpenAI API client instance
        """
        self.client = api_client
        self.registry = model_registry
        
    def call_with_fallback(self, model_name: str, messages: List[Dict[str, str]], **kwargs):
        """
        Call the API with automatic fallback on parameter errors
        
        Args:
            model_name: Name of the model to use
            messages: Messages for the API
            **kwargs: Additional parameters
            
        Returns:
            API response or None on failure
        """
        config = self.registry.get(model_name)
        if not config:
            logger.error(f"Model {model_name} not found in registry")
            return None
            
        if not config.is_available():
            logger.warning(f"Model {model_name} is not currently available")
            # Fall back to default model
            config = self.registry.get_default_model()
            logger.info(f"Falling back to {config.display_name}")
            
        try:
            # Build parameters for this model
            params = config.build_api_params(messages, **kwargs)
            
            # Make the API call
            response = self.client.chat.completions.create(**params)
            
            # Log token usage
            if hasattr(response, 'usage'):
                self._log_token_usage(response.usage, config)
                
            return response
            
        except Exception as e:
            if "max_tokens" in str(e) or "max_completion_tokens" in str(e):
                logger.warning(f"Parameter mismatch detected, attempting migration: {e}")
                return self._migrate_and_retry(config, messages, **kwargs)
            else:
                logger.error(f"API call failed: {e}")
                raise
                
    def _migrate_and_retry(self, config: ModelConfig, messages: List[Dict[str, str]], **kwargs):
        """
        Retry API call with migrated parameters
        
        Args:
            config: Model configuration
            messages: Messages for the API
            **kwargs: Additional parameters
            
        Returns:
            API response or None on failure
        """
        try:
            # Try alternative parameter name
            alt_param = "max_completion_tokens" if config.max_tokens_param == "max_tokens" else "max_tokens"
            params = config.build_api_params(messages, **kwargs)
            
            # Swap parameter name
            if config.max_tokens_param in params:
                params[alt_param] = params.pop(config.max_tokens_param)
                
            logger.info(f"Retrying with parameter: {alt_param}")
            response = self.client.chat.completions.create(**params)
            
            # Update registry with discovered parameter
            config.max_tokens_param = alt_param
            logger.info(f"Updated {config.model_name} to use {alt_param}")
            
            return response
            
        except Exception as e:
            logger.error(f"Migration retry failed: {e}")
            return None
            
    def _log_token_usage(self, usage, config: ModelConfig):
        """Log token usage and estimated cost"""
        if usage:
            cost = config.estimate_cost(usage.prompt_tokens, usage.completion_tokens)
            logger.info(
                f"Token usage - Input: {usage.prompt_tokens}, "
                f"Output: {usage.completion_tokens}, "
                f"Total: {usage.total_tokens}, "
                f"Cost: ${cost:.4f}"
            )