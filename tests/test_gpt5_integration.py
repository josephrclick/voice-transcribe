#!/usr/bin/env python3
"""
Test suite for GPT-5 model integration and breaking change handling.
Tests parameter migration, fallback chains, and cost management.
"""

import pytest
import unittest
from unittest.mock import patch, MagicMock, Mock
import sys
import os
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model_config import ModelConfig, ModelAdapter, ModelRegistry, model_registry
from enhance import enhance_prompt


class TestGPT5ModelConfigurations(unittest.TestCase):
    """Test GPT-5 model configurations and parameter handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = model_registry
        self.gpt5_nano = self.registry.get("gpt-5-nano")
        self.gpt5_mini = self.registry.get("gpt-5-mini")
        self.gpt5 = self.registry.get("gpt-5")
    
    def test_gpt5_models_configured(self):
        """Test that GPT-5 models are properly configured."""
        self.assertIsNotNone(self.gpt5_nano)
        self.assertIsNotNone(self.gpt5_mini)
        self.assertIsNotNone(self.gpt5)
        
        # Check model names
        self.assertEqual(self.gpt5_nano.model_name, "gpt-5-nano")
        self.assertEqual(self.gpt5_mini.model_name, "gpt-5-mini")
        self.assertEqual(self.gpt5.model_name, "gpt-5")
    
    def test_max_completion_tokens_parameter(self):
        """Test that GPT-5 models use max_completion_tokens parameter."""
        self.assertEqual(self.gpt5_nano.max_tokens_param, "max_completion_tokens")
        self.assertEqual(self.gpt5_mini.max_tokens_param, "max_completion_tokens")
        self.assertEqual(self.gpt5.max_tokens_param, "max_completion_tokens")
    
    def test_tier_classification(self):
        """Test that models are properly classified by tier."""
        self.assertEqual(self.gpt5_nano.tier, "economy")
        self.assertEqual(self.gpt5_mini.tier, "standard")
        self.assertEqual(self.gpt5.tier, "premium")
    
    def test_cost_configuration(self):
        """Test that cost configurations are correct."""
        # GPT-5 Nano (economy)
        self.assertEqual(self.gpt5_nano.cost_per_1k_input, 0.00005)
        self.assertEqual(self.gpt5_nano.cost_per_1k_output, 0.00020)
        
        # GPT-5 Mini (standard)
        self.assertEqual(self.gpt5_mini.cost_per_1k_input, 0.00012)
        self.assertEqual(self.gpt5_mini.cost_per_1k_output, 0.00048)
        
        # GPT-5 (premium)
        self.assertEqual(self.gpt5.cost_per_1k_input, 0.00030)
        self.assertEqual(self.gpt5.cost_per_1k_output, 0.00120)
    
    def test_reasoning_effort_support(self):
        """Test that GPT-5 models support reasoning_effort parameter."""
        self.assertTrue(self.gpt5_nano.supports_reasoning_effort)
        self.assertTrue(self.gpt5_mini.supports_reasoning_effort)
        self.assertTrue(self.gpt5.supports_reasoning_effort)
        
        # Check reasoning effort levels in fallback params
        self.assertEqual(self.gpt5_nano.fallback_params.get("reasoning_effort"), "low")
        self.assertEqual(self.gpt5_mini.fallback_params.get("reasoning_effort"), "medium")
        self.assertEqual(self.gpt5.fallback_params.get("reasoning_effort"), "high")
    
    def test_temperature_constraints(self):
        """Test temperature constraints for GPT-5 models."""
        # GPT-5 models have temperature fixed at 1.0
        self.assertEqual(self.gpt5_nano.temperature_min, 1.0)
        self.assertEqual(self.gpt5_nano.temperature_max, 1.0)
        self.assertEqual(self.gpt5_nano.temperature, 1.0)
        
        self.assertEqual(self.gpt5_mini.temperature_min, 1.0)
        self.assertEqual(self.gpt5_mini.temperature_max, 1.0)
        self.assertEqual(self.gpt5_mini.temperature, 1.0)
        
        self.assertEqual(self.gpt5.temperature_min, 1.0)
        self.assertEqual(self.gpt5.temperature_max, 1.0)
        self.assertEqual(self.gpt5.temperature, 1.0)


class TestParameterMigration(unittest.TestCase):
    """Test parameter migration and breaking change handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.adapter = ModelAdapter()
        self.gpt5_config = model_registry.get("gpt-5-nano")
        self.gpt4_config = model_registry.get("gpt-4o-mini")
    
    def test_build_api_params_gpt5(self):
        """Test building API parameters for GPT-5 models."""
        messages = [{"role": "user", "content": "Test"}]
        params = self.gpt5_config.build_api_params(messages, style="balanced")
        
        # Check that max_completion_tokens is used
        self.assertIn("max_completion_tokens", params)
        self.assertNotIn("max_tokens", params)
        self.assertEqual(params["max_completion_tokens"], 1000)
        
        # Check reasoning_effort is included
        self.assertIn("reasoning_effort", params)
        self.assertEqual(params["reasoning_effort"], "low")
        
        # Check verbosity mapping
        self.assertIn("verbosity", params)
        self.assertEqual(params["verbosity"], "medium")
    
    def test_build_api_params_gpt4(self):
        """Test building API parameters for GPT-4 models."""
        messages = [{"role": "user", "content": "Test"}]
        params = self.gpt4_config.build_api_params(messages, style="balanced")
        
        # Check that max_tokens is used for GPT-4
        self.assertIn("max_tokens", params)
        self.assertNotIn("max_completion_tokens", params)
        self.assertEqual(params["max_tokens"], 1000)
        
        # GPT-4 doesn't support reasoning_effort or verbosity
        self.assertNotIn("reasoning_effort", params)
        self.assertNotIn("verbosity", params)
    
    @patch('model_config.client.chat.completions.create')
    def test_parameter_migration_on_error(self, mock_create):
        """Test automatic parameter migration on API error."""
        # Simulate parameter name error
        error_msg = "Unknown parameter: max_tokens. Did you mean max_completion_tokens?"
        mock_create.side_effect = [
            Exception(error_msg),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Success"))])
        ]
        
        result = self.adapter.call_with_fallback(
            "gpt-5-nano",
            [{"role": "user", "content": "Test"}],
            max_tokens=100  # Wrong parameter name
        )
        
        # Should succeed after retry
        self.assertEqual(result[0], "Success")
        self.assertIsNone(result[1])
        
        # Check that second call used correct parameter
        second_call_args = mock_create.call_args_list[1][1]
        self.assertIn("max_completion_tokens", second_call_args)
        self.assertEqual(second_call_args["max_completion_tokens"], 100)


class TestFallbackChains(unittest.TestCase):
    """Test model fallback chains and error recovery."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.adapter = ModelAdapter()
    
    @patch('model_config.client.chat.completions.create')
    def test_fallback_to_gpt4_on_gpt5_error(self, mock_create):
        """Test fallback from GPT-5 to GPT-4 on error."""
        # First call fails (GPT-5), second succeeds (GPT-4)
        mock_create.side_effect = [
            Exception("Model not available"),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Fallback success"))])
        ]
        
        result = self.adapter.call_with_fallback(
            "gpt-5-nano",
            [{"role": "user", "content": "Test"}]
        )
        
        self.assertEqual(result[0], "Fallback success")
        self.assertIsNone(result[1])
        
        # Verify fallback model was used
        self.assertEqual(mock_create.call_count, 2)
        second_call = mock_create.call_args_list[1][1]
        self.assertEqual(second_call["model"], "gpt-4o-mini")  # Default fallback
    
    @patch('model_config.client.chat.completions.create')
    def test_temperature_constraint_handling(self, mock_create):
        """Test handling of temperature constraint errors."""
        # Simulate temperature constraint error
        error_msg = "Temperature must be 1.0 for this model"
        mock_create.side_effect = [
            Exception(error_msg),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Temperature fixed"))])
        ]
        
        result = self.adapter.call_with_fallback(
            "gpt-5-nano",
            [{"role": "user", "content": "Test"}],
            temperature=0.7
        )
        
        self.assertEqual(result[0], "Temperature fixed")
        
        # Verify temperature was adjusted
        second_call = mock_create.call_args_list[1][1]
        self.assertEqual(second_call["temperature"], 1.0)


class TestCostManagement(unittest.TestCase):
    """Test cost estimation and tier management."""
    
    def test_get_models_by_tier(self):
        """Test grouping models by tier."""
        # Group models by tier manually for testing
        models = [m.model_name for m in model_registry.get_available_models()]
        tiers = {"economy": [], "standard": [], "premium": []}
        
        for model_name in models:
            config = model_registry.get(model_name)
            if config and hasattr(config, 'tier'):
                tiers[config.tier].append(config)
        
        self.assertIn("economy", tiers)
        self.assertIn("standard", tiers)
        self.assertIn("premium", tiers)
        
        # Check some models are in correct tiers
        economy_names = [m.model_name for m in tiers["economy"]]
        standard_names = [m.model_name for m in tiers["standard"]]
        premium_names = [m.model_name for m in tiers["premium"]]
        
        self.assertIn("gpt-5-nano", economy_names)
        self.assertIn("gpt-5-mini", standard_names)
        self.assertIn("gpt-5", premium_names)
    
    def test_cost_estimation(self):
        """Test cost estimation for different models."""
        transcript = "Test transcript " * 100  # ~200 tokens
        
        # Estimate tokens (rough approximation)
        input_tokens = len(transcript.split()) * 1.5
        output_tokens = 50  # Expected response
        
        # Test economy tier
        nano_config = model_registry.get("gpt-5-nano")
        cost_nano = nano_config.estimate_cost(input_tokens, output_tokens)
        self.assertLess(cost_nano, 0.001)  # Should be very cheap
        
        # Test standard tier  
        mini_config = model_registry.get("gpt-5-mini")
        cost_mini = mini_config.estimate_cost(input_tokens, output_tokens)
        self.assertGreater(cost_mini, cost_nano)  # Should be more expensive
        
        # Test premium tier
        premium_config = model_registry.get("gpt-5")
        cost_premium = premium_config.estimate_cost(input_tokens, output_tokens)
        self.assertGreater(cost_premium, cost_mini)  # Should be most expensive
    
    def test_model_availability(self):
        """Test model availability checking."""
        registry = model_registry
        
        # GPT-5 models should be available (dates updated for testing)
        gpt5_nano = registry.get("gpt-5-nano")
        self.assertTrue(gpt5_nano.is_available())
        
        gpt5_mini = registry.get("gpt-5-mini")
        self.assertTrue(gpt5_mini.is_available())
        
        gpt5 = registry.get("gpt-5")
        self.assertTrue(gpt5.is_available())


class TestEnhancementIntegration(unittest.TestCase):
    """Test full enhancement flow with GPT-5 models."""
    
    @patch('enhance.client.chat.completions.create')
    @patch('enhance.load_config')
    def test_enhance_with_gpt5_nano(self, mock_config, mock_create):
        """Test enhancement using GPT-5 Nano model."""
        mock_config.return_value = {"selected_model": "gpt-5-nano"}
        mock_create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Enhanced text"))],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50)
        )
        
        result = enhance_prompt("Test transcript", style="balanced")
        
        self.assertEqual(result[0], "Enhanced text")
        self.assertIsNone(result[1])
        
        # Verify correct parameters were used
        call_args = mock_create.call_args[1]
        self.assertEqual(call_args["model"], "gpt-5-nano")
        self.assertIn("max_completion_tokens", call_args)
        self.assertIn("reasoning_effort", call_args)
        self.assertIn("verbosity", call_args)
    
    @patch('enhance.client.chat.completions.create')
    def test_style_to_verbosity_mapping(self, mock_create):
        """Test that enhancement styles map to verbosity for GPT-5."""
        mock_create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Result"))],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50)
        )
        
        # Test different styles
        styles_to_verbosity = {
            "concise": "low",
            "balanced": "medium",
            "detailed": "high"
        }
        
        for style, expected_verbosity in styles_to_verbosity.items():
            enhance_prompt("Test", style=style, model_key="gpt-5-nano")
            call_args = mock_create.call_args[1]
            self.assertEqual(call_args["verbosity"], expected_verbosity)


class TestModelTransitions(unittest.TestCase):
    """Test smooth transitions between different model generations."""
    
    @patch('enhance.client.chat.completions.create')
    @patch('enhance.load_config')
    def test_switch_gpt4_to_gpt5(self, mock_config, mock_create):
        """Test switching from GPT-4 to GPT-5 models."""
        mock_create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Result"))],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50)
        )
        
        # Test GPT-4 call
        mock_config.return_value = {"selected_model": "gpt-4o-mini"}
        enhance_prompt("Test", style="balanced")
        gpt4_args = mock_create.call_args[1]
        self.assertIn("max_tokens", gpt4_args)
        self.assertNotIn("reasoning_effort", gpt4_args)
        
        # Test GPT-5 call
        mock_config.return_value = {"selected_model": "gpt-5-nano"}
        enhance_prompt("Test", style="balanced")
        gpt5_args = mock_create.call_args[1]
        self.assertIn("max_completion_tokens", gpt5_args)
        self.assertIn("reasoning_effort", gpt5_args)
    
    def test_model_feature_compatibility(self):
        """Test that model features are correctly identified."""
        registry = model_registry
        
        # GPT-4 models
        gpt4 = registry.get("gpt-4o-mini")
        self.assertFalse(gpt4.supports_reasoning_effort)
        self.assertEqual(gpt4.max_tokens_param, "max_tokens")
        
        # GPT-4.1 models
        gpt41 = registry.get("gpt-4.1-mini")
        self.assertFalse(gpt41.supports_reasoning_effort)  # GPT-4.1 doesn't have reasoning_effort
        self.assertFalse(gpt41.supports_verbosity)  # GPT-4.1 doesn't support verbosity either
        self.assertEqual(gpt41.max_tokens_param, "max_tokens")
        
        # GPT-5 models
        gpt5 = registry.get("gpt-5-nano")
        self.assertTrue(gpt5.supports_reasoning_effort)
        self.assertEqual(gpt5.max_tokens_param, "max_completion_tokens")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])