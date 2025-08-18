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
    supports_reasoning_effort: bool = False
    context_window: int = 128000
    deprecated: bool = False
    available_from: Optional[str] = None  # ISO date string
    sunset_date: Optional[str] = None  # ISO date string
    tier: str = "standard"  # "economy", "standard", "premium"
    temperature_constrained: bool = False  # True if temperature is restricted in GPT-5
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
            
        if self.supports_reasoning_effort and 'reasoning_effort' in kwargs:
            params["reasoning_effort"] = kwargs['reasoning_effort']
            
        if self.supports_json_mode and kwargs.get('response_format') == 'json':
            params["response_format"] = {"type": "json_object"}
            
        # Handle temperature constraints for GPT-5 models
        if self.temperature_constrained and 'style' in kwargs:
            # Map style to verbosity when temperature is constrained
            style_to_verbosity = {
                "concise": "low",
                "balanced": "medium", 
                "detailed": "high"
            }
            verbosity = style_to_verbosity.get(kwargs['style'], "medium")
            if self.supports_verbosity:
                params["verbosity"] = verbosity
            
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
    
    def get_tier_info(self) -> Dict[str, str]:
        """
        Get tier classification information
        
        Returns:
            Dictionary with tier info for UI display
        """
        tier_colors = {
            "economy": "#28a745",  # Green
            "standard": "#007bff", # Blue
            "premium": "#6f42c1"   # Purple
        }
        
        return {
            "tier": self.tier,
            "color": tier_colors.get(self.tier, "#6c757d"),
            "description": f"{self.tier.title()} tier model"
        }


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
            supports_reasoning_effort=False,
            context_window=128000,
            deprecated=False,
            tier="standard"
        ))
        
        # GPT-4.1-nano - Available now! (Cheapest option)
        self.register(ModelConfig(
            model_name="gpt-4.1-nano",
            display_name="GPT-4.1 Nano",
            max_tokens_param="max_tokens",
            max_tokens_value=500,
            temperature=0.3,
            temperature_min=0.0,
            temperature_max=2.0,
            cost_per_1k_input=0.00003,  # $0.03 per 1M input tokens (80% cheaper!)
            cost_per_1k_output=0.00012,  # Estimated proportional reduction
            supports_verbosity=True,
            supports_json_mode=True,
            supports_reasoning_effort=False,
            context_window=128000,
            deprecated=False,
            available_from=None,  # Available now!
            tier="economy"
        ))
        
        # GPT-4.1-mini - Available now!
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
            supports_reasoning_effort=False,
            context_window=256000,  # 2x context window
            deprecated=False,
            available_from=None,  # Available now!
            tier="economy"
        ))
        
        # GPT-4.1 (standard) - Available now!
        self.register(ModelConfig(
            model_name="gpt-4.1",
            display_name="GPT-4.1",
            max_tokens_param="max_tokens",
            max_tokens_value=2000,
            temperature=0.3,
            temperature_min=0.0,
            temperature_max=2.0,
            cost_per_1k_input=0.00015,  # Same as GPT-4o-mini but with better performance
            cost_per_1k_output=0.0006,
            supports_verbosity=True,
            supports_json_mode=True,
            supports_reasoning_effort=False,
            context_window=512000,  # 4x context window
            deprecated=False,
            available_from=None,  # Available now!
            tier="standard"
        ))
        
        # GPT-5-nano - Available for testing (Economy tier)
        self.register(ModelConfig(
            model_name="gpt-5-nano",
            display_name="GPT-5 Nano",
            max_tokens_param="max_completion_tokens",  # Breaking change
            max_tokens_value=250,
            temperature=1.0,  # Fixed at 1.0 for GPT-5
            temperature_min=1.0,  # GPT-5 constraint
            temperature_max=1.0,  # GPT-5 constraint
            cost_per_1k_input=0.00005,  # Ultra-cheap
            cost_per_1k_output=0.00020,
            supports_verbosity=True,
            supports_json_mode=True,
            supports_reasoning_effort=True,
            context_window=512000,  # 4x context window
            deprecated=False,
            available_from=None,  # Available now for testing
            tier="economy",
            temperature_constrained=True,
            fallback_params={
                "reasoning_effort": "low"  # New GPT-5 parameter
            }
        ))
        
        # GPT-5-mini - Available for testing (Standard tier)
        self.register(ModelConfig(
            model_name="gpt-5-mini",
            display_name="GPT-5 Mini",
            max_tokens_param="max_completion_tokens",  # Breaking change
            max_tokens_value=500,
            temperature=1.0,  # Fixed at 1.0 for GPT-5
            temperature_min=1.0,  # GPT-5 constraint
            temperature_max=1.0,  # GPT-5 constraint
            cost_per_1k_input=0.00012,
            cost_per_1k_output=0.00048,
            supports_verbosity=True,
            supports_json_mode=True,
            supports_reasoning_effort=True,
            context_window=1024000,  # 8x context window
            deprecated=False,
            available_from=None,  # Available now for testing
            tier="standard",
            temperature_constrained=True,
            fallback_params={
                "reasoning_effort": "medium"  # New GPT-5 parameter
            }
        ))
        
        # GPT-5 (full) - Available for testing (Premium tier)
        self.register(ModelConfig(
            model_name="gpt-5",
            display_name="GPT-5",
            max_tokens_param="max_completion_tokens",  # Breaking change
            max_tokens_value=1000,
            temperature=1.0,  # Fixed at 1.0 for GPT-5
            temperature_min=1.0,  # GPT-5 constraint
            temperature_max=1.0,  # GPT-5 constraint
            cost_per_1k_input=0.00030,
            cost_per_1k_output=0.00120,
            supports_verbosity=True,
            supports_json_mode=True,
            supports_reasoning_effort=True,
            context_window=2048000,  # 16x context window
            deprecated=False,
            available_from=None,  # Available now for testing
            tier="premium",
            temperature_constrained=True,
            fallback_params={
                "reasoning_effort": "high"  # New GPT-5 parameter
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
    
    def get_fallback_chain(self, model_name: str) -> List[str]:
        """
        Get fallback chain for a given model
        
        Args:
            model_name: Name of the primary model
            
        Returns:
            List of model names in fallback order
        """
        # Define fallback chains based on model tiers and capabilities
        fallback_chains = {
            # GPT-5 models fall back to GPT-4.1, then GPT-4o-mini
            "gpt-5": ["gpt-5", "gpt-4.1", "gpt-4o-mini"],
            "gpt-5-mini": ["gpt-5-mini", "gpt-4.1-mini", "gpt-4o-mini"],
            "gpt-5-nano": ["gpt-5-nano", "gpt-4.1-nano", "gpt-4o-mini"],
            
            # GPT-4.1 models fall back to GPT-4o-mini
            "gpt-4.1": ["gpt-4.1", "gpt-4o-mini"],
            "gpt-4.1-mini": ["gpt-4.1-mini", "gpt-4o-mini"],
            "gpt-4.1-nano": ["gpt-4.1-nano", "gpt-4o-mini"],
            
            # GPT-4o-mini is the ultimate fallback
            "gpt-4o-mini": ["gpt-4o-mini"]
        }
        
        return fallback_chains.get(model_name, [model_name, "gpt-4o-mini"])
    
    def get_models_by_tier(self, tier: str) -> List[ModelConfig]:
        """
        Get models by tier classification
        
        Args:
            tier: Tier name ("economy", "standard", "premium")
            
        Returns:
            List of models in the specified tier
        """
        return [model for model in self.models.values() 
                if model.tier == tier and model.is_available()]
        
    def get_all_models(self) -> List[ModelConfig]:
        """Get all registered models (including future/deprecated)"""
        return list(self.models.values())


# Global registry instance
model_registry = ModelRegistry()


def get_model_usage_summary() -> Dict[str, Any]:
    """
    Get a summary of model usage across all adapters
    
    Returns:
        Dictionary with usage summary by tier and model
    """
    # This would typically aggregate from all adapter instances
    # For now, return structure for future implementation
    return {
        "by_tier": {
            "economy": {"calls": 0, "cost": 0.0},
            "standard": {"calls": 0, "cost": 0.0}, 
            "premium": {"calls": 0, "cost": 0.0}
        },
        "total_cost": 0.0,
        "total_calls": 0
    }


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
        self.usage_stats = {}  # Track usage statistics
        
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
        # Get fallback chain for this model
        fallback_chain = self.registry.get_fallback_chain(model_name)
        
        last_error = None
        for attempt_model in fallback_chain:
            config = self.registry.get(attempt_model)
            if not config or not config.is_available():
                logger.info(f"Skipping unavailable model: {attempt_model}")
                continue
                
            try:
                # Build parameters for this model
                params = config.build_api_params(messages, **kwargs)
                
                # Make the API call
                response = self.client.chat.completions.create(**params)
                
                # Log successful call
                if attempt_model != model_name:
                    logger.info(f"Successfully used fallback model: {config.display_name}")
                
                # Log token usage and update statistics
                if hasattr(response, 'usage'):
                    self._log_token_usage(response.usage, config)
                    self._update_usage_stats(config, response.usage)
                    
                return response
                
            except Exception as e:
                last_error = e
                
                # Try parameter migration for known errors
                if self._is_parameter_error(e):
                    logger.warning(f"Parameter error with {attempt_model}, attempting migration: {e}")
                    migration_result = self._migrate_and_retry(config, messages, **kwargs)
                    if migration_result:
                        return migration_result
                        
                # Try reasoning_effort parameter removal for GPT-5 models
                if "reasoning_effort" in str(e) and config.supports_reasoning_effort:
                    logger.warning(f"reasoning_effort error with {attempt_model}, retrying without it")
                    kwargs_copy = kwargs.copy()
                    kwargs_copy.pop('reasoning_effort', None)
                    try:
                        params = config.build_api_params(messages, **kwargs_copy)
                        response = self.client.chat.completions.create(**params)
                        if hasattr(response, 'usage'):
                            self._log_token_usage(response.usage, config)
                            self._update_usage_stats(config, response.usage)
                        return response
                    except Exception as inner_e:
                        logger.warning(f"Retry without reasoning_effort failed: {inner_e}")
                
                logger.warning(f"Model {attempt_model} failed: {e}")
                continue
                
        # All fallbacks failed
        logger.error(f"All fallback models failed. Last error: {last_error}")
        return None
                
    def _is_parameter_error(self, error: Exception) -> bool:
        """
        Check if the error is a parameter-related error that can be migrated
        
        Args:
            error: The exception to check
            
        Returns:
            True if this is a migratable parameter error
        """
        error_str = str(error).lower()
        parameter_errors = [
            "max_tokens",
            "max_completion_tokens", 
            "invalid parameter",
            "unrecognized parameter",
            "unexpected parameter",
            "reasoning_effort",
            "verbosity"
        ]
        return any(param_error in error_str for param_error in parameter_errors)
    
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
            
            if hasattr(response, 'usage'):
                self._log_token_usage(response.usage, config)
                self._update_usage_stats(config, response.usage)
            
            return response
            
        except Exception as e:
            logger.error(f"Migration retry failed: {e}")
            return None
            
    def _log_token_usage(self, usage, config: ModelConfig):
        """Log token usage and estimated cost"""
        if usage:
            cost = config.estimate_cost(usage.prompt_tokens, usage.completion_tokens)
            tier_info = config.get_tier_info()
            logger.info(
                f"Token usage - Model: {config.display_name} ({tier_info['tier']}), "
                f"Input: {usage.prompt_tokens}, "
                f"Output: {usage.completion_tokens}, "
                f"Total: {usage.total_tokens}, "
                f"Cost: ${cost:.4f}"
            )
    
    def _update_usage_stats(self, config: ModelConfig, usage):
        """Update usage statistics for cost tracking"""
        model_name = config.model_name
        if model_name not in self.usage_stats:
            self.usage_stats[model_name] = {
                "calls": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost": 0.0,
                "tier": config.tier
            }
        
        stats = self.usage_stats[model_name]
        stats["calls"] += 1
        stats["total_input_tokens"] += usage.prompt_tokens
        stats["total_output_tokens"] += usage.completion_tokens
        stats["total_cost"] += config.estimate_cost(usage.prompt_tokens, usage.completion_tokens)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        return self.usage_stats.copy()
    
    def reset_usage_stats(self):
        """Reset usage statistics"""
        self.usage_stats.clear()
        logger.info("Usage statistics reset")