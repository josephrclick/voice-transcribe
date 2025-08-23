#!/usr/bin/env python3
"""Characterization tests for model_config.py refactoring.

These tests capture the current behavior of complex functions before refactoring.
They ensure that refactoring doesn't break existing functionality.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model_config import (
    ModelRegistry,
    call_with_fallback,
    _initialize_default_models
)


class TestInitializeDefaultModelsCharacterization(unittest.TestCase):
    """Characterization tests for _initialize_default_models (complexity: 13, length: 160 lines)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.registry = ModelRegistry()
    
    def test_default_models_initialization(self):
        """Test that default models are properly initialized"""
        # Call the initialization
        _initialize_default_models(self.registry)
        
        # Check that models are registered
        self.assertGreater(len(self.registry.models), 0)
        
        # Check for specific model tiers
        tiers = self.registry.get_models_by_tier()
        self.assertIn("Economy", tiers)
        self.assertIn("Standard", tiers)
        self.assertIn("Flagship", tiers)
    
    def test_economy_tier_models(self):
        """Test economy tier model registration"""
        _initialize_default_models(self.registry)
        
        economy_models = self.registry.get_models_by_tier()["Economy"]
        
        # Check that economy models exist
        self.assertIsInstance(economy_models, list)
        self.assertGreater(len(economy_models), 0)
        
        # Check model properties
        for model_key in economy_models:
            model = self.registry.get_model(model_key)
            self.assertIsNotNone(model)
            self.assertEqual(model.tier, "Economy")
            self.assertIsNotNone(model.context_window)
            self.assertIsNotNone(model.max_output)
    
    def test_standard_tier_models(self):
        """Test standard tier model registration"""
        _initialize_default_models(self.registry)
        
        standard_models = self.registry.get_models_by_tier()["Standard"]
        
        # Check that standard models exist
        self.assertIsInstance(standard_models, list)
        self.assertGreater(len(standard_models), 0)
        
        # Check model properties
        for model_key in standard_models:
            model = self.registry.get_model(model_key)
            self.assertIsNotNone(model)
            self.assertEqual(model.tier, "Standard")
    
    def test_flagship_tier_models(self):
        """Test flagship tier model registration"""
        _initialize_default_models(self.registry)
        
        flagship_models = self.registry.get_models_by_tier()["Flagship"]
        
        # Check that flagship models exist
        self.assertIsInstance(flagship_models, list)
        self.assertGreater(len(flagship_models), 0)
        
        # Check model properties
        for model_key in flagship_models:
            model = self.registry.get_model(model_key)
            self.assertIsNotNone(model)
            self.assertEqual(model.tier, "Flagship")
    
    def test_model_fallback_chains(self):
        """Test that models have proper fallback chains"""
        _initialize_default_models(self.registry)
        
        # Get a model with fallbacks
        model = self.registry.get_model("gpt-4o-mini")
        if model and model.fallback_models:
            # Check fallback chain
            for fallback_key in model.fallback_models:
                fallback_model = self.registry.get_model(fallback_key)
                self.assertIsNotNone(fallback_model)
    
    def test_provider_distribution(self):
        """Test that multiple providers are represented"""
        _initialize_default_models(self.registry)
        
        providers = set()
        for model_key, model in self.registry.models.items():
            providers.add(model.provider)
        
        # Should have multiple providers
        self.assertGreater(len(providers), 1)
        
        # Check for specific providers
        expected_providers = {"openai", "anthropic"}
        self.assertTrue(providers & expected_providers)


class TestCallWithFallbackCharacterization(unittest.TestCase):
    """Characterization tests for call_with_fallback (complexity: 14, length: 71 lines)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.registry = ModelRegistry()
        _initialize_default_models(self.registry)
    
    @patch('model_config.openai')
    def test_successful_call_no_fallback(self, mock_openai):
        """Test successful API call without needing fallback"""
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response text"))]
        mock_client.chat.completions.create.return_value = mock_response
        
        result, error = call_with_fallback(
            model_key="gpt-4o-mini",
            messages=[{"role": "user", "content": "Test"}]
        )
        
        self.assertEqual(result, "Response text")
        self.assertIsNone(error)
    
    @patch('model_config.openai')
    def test_fallback_on_primary_failure(self, mock_openai):
        """Test fallback to secondary model on primary failure"""
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        
        # First call fails
        mock_client.chat.completions.create.side_effect = [
            Exception("Primary model failed"),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Fallback response"))])
        ]
        
        result, error = call_with_fallback(
            model_key="gpt-4o-mini",
            messages=[{"role": "user", "content": "Test"}]
        )
        
        # Should get fallback response
        self.assertIsNotNone(result)
        self.assertIsNone(error)
    
    @patch('model_config.openai')
    def test_all_models_fail(self, mock_openai):
        """Test when all models in fallback chain fail"""
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("All models failed")
        
        result, error = call_with_fallback(
            model_key="gpt-4o-mini",
            messages=[{"role": "user", "content": "Test"}]
        )
        
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("failed", error.lower())
    
    def test_invalid_model_key(self):
        """Test handling of invalid model key"""
        result, error = call_with_fallback(
            model_key="invalid-model-key",
            messages=[{"role": "user", "content": "Test"}]
        )
        
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("not found", error.lower())
    
    def test_empty_messages(self):
        """Test handling of empty messages"""
        result, error = call_with_fallback(
            model_key="gpt-4o-mini",
            messages=[]
        )
        
        # Should handle gracefully
        self.assertIsNone(result)
        self.assertIsNotNone(error)
    
    @patch('model_config.anthropic')
    def test_anthropic_model_call(self, mock_anthropic):
        """Test calling Anthropic models"""
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Anthropic response")]
        mock_client.messages.create.return_value = mock_response
        
        result, error = call_with_fallback(
            model_key="claude-3-haiku",
            messages=[{"role": "user", "content": "Test"}]
        )
        
        self.assertEqual(result, "Anthropic response")
        self.assertIsNone(error)
    
    @patch('model_config.openai')
    def test_retry_logic(self, mock_openai):
        """Test retry logic on transient failures"""
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        
        # First two attempts fail, third succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success after retry"))]
        mock_client.chat.completions.create.side_effect = [
            Exception("Transient error 1"),
            Exception("Transient error 2"),
            mock_response
        ]
        
        result, error = call_with_fallback(
            model_key="gpt-4o-mini",
            messages=[{"role": "user", "content": "Test"}],
            max_retries=3
        )
        
        # Should eventually succeed
        self.assertIsNotNone(result)
        self.assertIsNone(error)


class TestModelRegistryCharacterization(unittest.TestCase):
    """Test ModelRegistry class methods"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.registry = ModelRegistry()
        _initialize_default_models(self.registry)
    
    def test_get_default_model(self):
        """Test getting the default model"""
        default = self.registry.get_default_model()
        
        self.assertIsNotNone(default)
        self.assertIn(default, self.registry.models)
    
    def test_get_models_by_tier_structure(self):
        """Test structure of get_models_by_tier return value"""
        tiers = self.registry.get_models_by_tier()
        
        self.assertIsInstance(tiers, dict)
        for tier_name, models in tiers.items():
            self.assertIsInstance(tier_name, str)
            self.assertIsInstance(models, list)
            for model_key in models:
                self.assertIsInstance(model_key, str)
                self.assertIn(model_key, self.registry.models)
    
    def test_model_migration(self):
        """Test model migration functionality"""
        # Test migration from old to new model names
        old_model = "gpt-4"
        result = self.registry.migrate_model(old_model)
        
        # Should return a valid model key
        self.assertIsNotNone(result)
        if result != old_model:
            self.assertIn(result, self.registry.models)
    
    def test_usage_statistics_tracking(self):
        """Test usage statistics are properly tracked"""
        stats = self.registry.get_usage_statistics()
        
        self.assertIsInstance(stats, dict)
        # Check for expected keys
        expected_keys = ["total_calls", "total_tokens", "total_cost"]
        for key in expected_keys:
            self.assertIn(key, stats)
    
    def test_cost_estimation(self):
        """Test cost estimation for models"""
        model_key = "gpt-4o-mini"
        estimated_cost = self.registry.estimate_cost(
            model_key=model_key,
            input_tokens=100,
            output_tokens=50
        )
        
        self.assertIsInstance(estimated_cost, (int, float))
        self.assertGreaterEqual(estimated_cost, 0)


class TestEdgeCasesAndErrorHandling(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.registry = ModelRegistry()
        _initialize_default_models(self.registry)
    
    def test_none_inputs(self):
        """Test handling of None inputs"""
        result, error = call_with_fallback(
            model_key=None,
            messages=[{"role": "user", "content": "Test"}]
        )
        
        self.assertIsNone(result)
        self.assertIsNotNone(error)
    
    def test_malformed_messages(self):
        """Test handling of malformed message structures"""
        test_cases = [
            None,
            "string instead of list",
            [{"invalid": "structure"}],
            [{"role": "user"}],  # Missing content
            [{"content": "test"}],  # Missing role
        ]
        
        for messages in test_cases:
            with self.subTest(messages=messages):
                result, error = call_with_fallback(
                    model_key="gpt-4o-mini",
                    messages=messages
                )
                
                self.assertIsNone(result)
                self.assertIsNotNone(error)
    
    @patch('model_config.openai')
    def test_partial_response_handling(self, mock_openai):
        """Test handling of partial or malformed API responses"""
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        
        # Response missing expected fields
        mock_response = MagicMock()
        mock_response.choices = []  # Empty choices
        mock_client.chat.completions.create.return_value = mock_response
        
        result, error = call_with_fallback(
            model_key="gpt-4o-mini",
            messages=[{"role": "user", "content": "Test"}]
        )
        
        self.assertIsNone(result)
        self.assertIsNotNone(error)


if __name__ == "__main__":
    unittest.main()