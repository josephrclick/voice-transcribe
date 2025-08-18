#!/usr/bin/env python3
"""
Tests for Model Configuration and GPT-5 Integration
"""

import pytest
from unittest.mock import Mock, patch
from model_config import ModelConfig, ModelRegistry, ModelAdapter, model_registry


class TestModelConfig:
    """Test ModelConfig class functionality"""
    
    def test_gpt5_model_configuration(self):
        """Test GPT-5 model configurations are properly set up"""
        gpt5_nano = model_registry.get("gpt-5-nano")
        assert gpt5_nano is not None
        assert gpt5_nano.max_tokens_param == "max_completion_tokens"
        assert gpt5_nano.supports_reasoning_effort == True
        assert gpt5_nano.supports_verbosity == True
        assert gpt5_nano.temperature_constrained == True
        assert gpt5_nano.tier == "economy"
        assert gpt5_nano.is_available() == True
    
    def test_gpt4_model_configuration(self):
        """Test GPT-4 models maintain their configurations"""
        gpt4_mini = model_registry.get("gpt-4o-mini")
        assert gpt4_mini is not None
        assert gpt4_mini.max_tokens_param == "max_tokens"
        assert gpt4_mini.supports_reasoning_effort == False
        assert gpt4_mini.supports_verbosity == False
        assert gpt4_mini.temperature_constrained == False
        assert gpt4_mini.tier == "standard"
    
    def test_parameter_building_gpt5(self):
        """Test parameter building for GPT-5 models"""
        gpt5_mini = model_registry.get("gpt-5-mini")
        
        # Test with explicit verbosity (should use provided value)
        params = gpt5_mini.build_api_params(
            messages=[{"role": "user", "content": "test"}],
            max_tokens=500,
            verbosity="high",
            reasoning_effort="medium",
            style="detailed"
        )
        
        assert params["model"] == "gpt-5-mini"
        assert params["max_completion_tokens"] == 500
        assert params["verbosity"] == "high"  # explicit verbosity provided
        assert params["reasoning_effort"] == "medium"
        assert "messages" in params
        
        # Test style-to-verbosity mapping when temperature constrained (no explicit verbosity)
        params_no_verbosity = gpt5_mini.build_api_params(
            messages=[{"role": "user", "content": "test"}],
            max_tokens=500,
            reasoning_effort="medium",
            style="concise"  # should map to low verbosity
        )
        
        assert params_no_verbosity["verbosity"] == "low"  # mapped from style
    
    def test_parameter_building_gpt4(self):
        """Test parameter building for GPT-4 models"""
        gpt4 = model_registry.get("gpt-4.1")
        params = gpt4.build_api_params(
            messages=[{"role": "user", "content": "test"}],
            max_tokens=500,
            verbosity="high"
        )
        
        assert params["model"] == "gpt-4.1"
        assert params["max_tokens"] == 500
        assert params["verbosity"] == "high"
        assert "reasoning_effort" not in params
    
    def test_fallback_chains(self):
        """Test fallback chain generation"""
        # GPT-5 should fall back to GPT-4.1 then GPT-4o-mini
        chain = model_registry.get_fallback_chain("gpt-5")
        assert chain == ["gpt-5", "gpt-4.1", "gpt-4o-mini"]
        
        # GPT-5-nano should fall back to GPT-4.1-nano then GPT-4o-mini
        chain = model_registry.get_fallback_chain("gpt-5-nano")
        assert chain == ["gpt-5-nano", "gpt-4.1-nano", "gpt-4o-mini"]
        
        # Unknown model should fall back to default
        chain = model_registry.get_fallback_chain("unknown")
        assert chain == ["unknown", "gpt-4o-mini"]
    
    def test_tier_classification(self):
        """Test model tier classification"""
        economy_models = model_registry.get_models_by_tier("economy")
        standard_models = model_registry.get_models_by_tier("standard")
        premium_models = model_registry.get_models_by_tier("premium")
        
        # Check that we have models in each tier
        assert len(economy_models) > 0
        assert len(standard_models) > 0
        assert len(premium_models) > 0
        
        # Check specific models are in expected tiers
        economy_names = [m.model_name for m in economy_models]
        assert "gpt-5-nano" in economy_names
        assert "gpt-4.1-nano" in economy_names
        
        premium_names = [m.model_name for m in premium_models]
        assert "gpt-5" in premium_names
    
    def test_cost_estimation(self):
        """Test cost estimation across different models"""
        gpt5_nano = model_registry.get("gpt-5-nano")
        gpt5 = model_registry.get("gpt-5")
        
        # GPT-5 nano should be cheaper than GPT-5
        nano_cost = gpt5_nano.estimate_cost(1000, 500)
        premium_cost = gpt5.estimate_cost(1000, 500)
        assert nano_cost < premium_cost
        
        # Cost should be positive for positive token counts
        assert nano_cost > 0
        assert premium_cost > 0


class TestModelAdapter:
    """Test ModelAdapter functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_client = Mock()
        self.adapter = ModelAdapter(self.mock_client)
    
    def test_adapter_initialization(self):
        """Test adapter initializes correctly"""
        assert self.adapter.client == self.mock_client
        assert self.adapter.registry == model_registry
        assert isinstance(self.adapter.usage_stats, dict)
    
    def test_usage_stats_tracking(self):
        """Test usage statistics tracking"""
        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        
        config = model_registry.get("gpt-5-nano")
        self.adapter._update_usage_stats(config, mock_usage)
        
        stats = self.adapter.get_usage_stats()
        assert "gpt-5-nano" in stats
        assert stats["gpt-5-nano"]["calls"] == 1
        assert stats["gpt-5-nano"]["total_input_tokens"] == 100
        assert stats["gpt-5-nano"]["total_output_tokens"] == 50
        assert stats["gpt-5-nano"]["tier"] == "economy"
    
    def test_parameter_error_detection(self):
        """Test parameter error detection"""
        # Test various parameter error patterns
        max_tokens_error = Exception("Invalid parameter: max_tokens")
        reasoning_effort_error = Exception("Unrecognized parameter: reasoning_effort")
        completion_tokens_error = Exception("Expected max_completion_tokens")
        
        assert self.adapter._is_parameter_error(max_tokens_error) == True
        assert self.adapter._is_parameter_error(reasoning_effort_error) == True
        assert self.adapter._is_parameter_error(completion_tokens_error) == True
        
        # Non-parameter errors should return False
        network_error = Exception("Network connection failed")
        assert self.adapter._is_parameter_error(network_error) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])