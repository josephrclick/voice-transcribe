#!/usr/bin/env python3
"""Enhancement builder for refactoring complex enhance_prompt function."""

import logging
import re
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def sanitize_error_message(message: str) -> str:
    """Sanitize error messages to prevent API key exposure.
    
    Removes or masks sensitive information like API keys, tokens,
    and credentials from error messages before logging.
    """
    # Common API key patterns to mask
    patterns = [
        (r'(api[_-]?key[\s=:]+)[\w-]{20,}', r'\1[REDACTED]'),
        (r'(token[\s=:]+)[\w-]{20,}', r'\1[REDACTED]'),
        (r'(bearer\s+)[\w-]{20,}', r'\1[REDACTED]'),
        (r'(sk-)[\w-]{20,}', r'\1[REDACTED]'),  # OpenAI keys
        (r'(key[\s=:]+)[\w-]{20,}', r'\1[REDACTED]'),
        (r'(secret[\s=:]+)[\w-]{20,}', r'\1[REDACTED]'),
        (r'(password[\s=:]+)[^\s]+', r'\1[REDACTED]'),
    ]
    
    sanitized = str(message)
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized


class EnhancementBuilder:
    """Builder pattern for constructing enhanced prompts."""

    def __init__(self, transcript: str, style: str = "balanced") -> None:
        """Initialize the builder with transcript and style.

        Args:
            transcript: Raw transcript text
            style: Enhancement style ('concise', 'balanced', 'detailed')
        """
        self.transcript = transcript
        self.style = style
        self.processed_transcript = transcript
        self.model_config = None
        self.fragment_processor = None
        self.error = None

    def validate_input(self) -> "EnhancementBuilder":
        """Validate the input transcript."""
        if not self.transcript or not self.transcript.strip():
            self.error = "Empty transcript"
        return self

    def normalize_style(self, available_styles: Dict[str, Any]) -> "EnhancementBuilder":
        """Normalize the enhancement style."""
        if self.style not in available_styles:
            logger.warning(f"Invalid style '{self.style}', falling back to 'balanced'")
            self.style = "balanced"
        return self

    def process_fragments(self, config: Optional[Dict] = None) -> "EnhancementBuilder":
        """Process transcript fragments if enabled.

        Args:
            config: Fragment processing configuration
        """
        if self.error:
            return self

        if config is None:
            config = {}

        if config.get("enabled", True):
            try:
                # Import here to avoid circular dependency
                from enhance import FragmentProcessor

                self.fragment_processor = FragmentProcessor()
                self.processed_transcript = self.fragment_processor.reconstruct_fragments(self.transcript)
                self._log_fragment_processing()
            except (ImportError, AttributeError) as e:
                # Handle import or attribute errors
                logger.error(f"Fragment processing failed: {sanitize_error_message(str(e))}")
                # Continue with original transcript
                self.processed_transcript = self.transcript
            except (ValueError, TypeError) as e:
                # Handle value or type errors in processing
                logger.error(f"Fragment processing error: {sanitize_error_message(str(e))}")
                # Continue with original transcript
                self.processed_transcript = self.transcript

        return self

    def _log_fragment_processing(self) -> None:
        """Log fragment processing analytics."""
        if self.processed_transcript != self.transcript:
            original_segments = len([s for s in re.split(r"[.!?]\s+", self.transcript) if s.strip()])
            processed_segments = len([s for s in re.split(r"[.!?]\s+", self.processed_transcript) if s.strip()])
            logger.info(f"Fragment processing applied: {original_segments} → {processed_segments} segments")

    def check_token_limits(self, max_tokens: int = 3000) -> "EnhancementBuilder":
        """Check if transcript exceeds token limits.

        Args:
            max_tokens: Maximum allowed tokens
        """
        if self.error:
            return self

        # Import here to avoid circular dependency
        from enhance import estimate_tokens_with_fragments

        if estimate_tokens_with_fragments(self.processed_transcript) > max_tokens:
            self.error = "Transcript too long for enhancement"

        return self

    def configure_model(self, model_key: Optional[str] = None, model_name: Optional[str] = None) -> "EnhancementBuilder":
        """Configure the model for enhancement.

        Args:
            model_key: Model key/ID from UI selection (preferred)
            model_name: Specific model name (deprecated)
        """
        if self.error:
            return self

        # Import here to avoid circular dependency
        from model_config import model_registry

        # Prefer model_key over model_name
        if model_key:
            self.model_config = {"key": model_key, "source": "model_key"}
        elif model_name:
            self.model_config = {"key": model_name, "source": "model_name"}
        else:
            # Use default
            default_model = model_registry.get_default_model()
            self.model_config = {"key": default_model, "source": "default"}

        return self

    def build_system_prompt(self, prompt_templates: Dict[str, str]) -> str:
        """Build the system prompt based on style.

        Args:
            prompt_templates: Dictionary of prompt templates by style

        Returns:
            System prompt string
        """
        base_prompt = prompt_templates.get(self.style, prompt_templates["balanced"])

        # Add any style-specific modifications
        if self.style == "concise":
            base_prompt += "\nBe extremely brief and to the point."
        elif self.style == "detailed":
            base_prompt += "\nProvide comprehensive detail and context."

        return base_prompt

    def build_user_prompt(self) -> str:
        """Build the user prompt from processed transcript.

        Returns:
            User prompt string
        """
        # Clean up the transcript
        cleaned = self.processed_transcript.strip()

        # Add any necessary formatting
        if not cleaned.endswith((".", "!", "?")):
            cleaned += "."

        return cleaned

    def apply_style_rules(self, text: str) -> str:
        """Apply style-specific transformation rules.

        Args:
            text: Text to transform

        Returns:
            Transformed text
        """
        if self.style == "concise":
            # Remove filler words for concise style
            filler_words = ["basically", "actually", "literally", "obviously"]
            for word in filler_words:
                text = re.sub(rf"\b{word}\b", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s+", " ", text).strip()

        elif self.style == "detailed":
            # Add emphasis markers for detailed style
            # This is a placeholder - actual implementation would be more sophisticated
            pass

        return text

    def execute_enhancement(self, call_function: Callable) -> Tuple[Optional[str], Optional[str]]:
        """Execute the actual enhancement using the configured model.

        Args:
            call_function: Function to call the model API

        Returns:
            Tuple of (enhanced_text, error_message)
        """
        if self.error:
            return None, self.error

        if not self.model_config:
            return None, "Model not configured"

        # This will be called with the actual API function
        try:
            # The actual call would be done in enhance.py
            # This is just the structure
            result = call_function(
                model_key=self.model_config["key"], transcript=self.processed_transcript, style=self.style
            )
            return result
        except (AttributeError, KeyError) as e:
            # Handle missing attributes or keys
            safe_error = sanitize_error_message(str(e))
            logger.error(f"Enhancement configuration error: {safe_error}")
            return None, safe_error
        except (ConnectionError, TimeoutError) as e:
            # Handle network-related errors
            safe_error = sanitize_error_message(str(e))
            logger.error(f"Enhancement network error: {safe_error}")
            return None, safe_error
        except (ValueError, TypeError) as e:
            # Handle value or type errors
            safe_error = sanitize_error_message(str(e))
            logger.error(f"Enhancement execution failed: {safe_error}")
            return None, safe_error


class ModelConfigBuilder:
    """Builder for model configuration to reduce complexity."""

    def __init__(self) -> None:
        """Initialize the model configuration builder."""
        self.models = {}
        self.default_model = None
        self.tiers = {"Economy": [], "Standard": [], "Flagship": []}

    def add_economy_models(self) -> "ModelConfigBuilder":
        """Add economy tier models."""
        economy_models = [
            {
                "key": "gpt-4o-mini",
                "name": "GPT-4o mini",
                "provider": "openai",
                "context_window": 128000,
                "max_output": 16384,
                "supports_json": True,
                "supports_tools": True,
                "fallback_models": ["gpt-3.5-turbo", "claude-3-haiku"],
            },
            {
                "key": "gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "provider": "openai",
                "context_window": 16385,
                "max_output": 4096,
                "supports_json": True,
                "supports_tools": True,
                "fallback_models": ["claude-3-haiku"],
            },
            {
                "key": "claude-3-haiku",
                "name": "Claude 3 Haiku",
                "provider": "anthropic",
                "context_window": 200000,
                "max_output": 4096,
                "supports_json": False,
                "supports_tools": True,
                "fallback_models": [],
            },
        ]

        for model in economy_models:
            self.models[model["key"]] = model
            self.tiers["Economy"].append(model["key"])

        return self

    def add_standard_models(self) -> "ModelConfigBuilder":
        """Add standard tier models."""
        standard_models = [
            {
                "key": "gpt-4o",
                "name": "GPT-4o",
                "provider": "openai",
                "context_window": 128000,
                "max_output": 16384,
                "supports_json": True,
                "supports_tools": True,
                "supports_vision": True,
                "fallback_models": ["gpt-4o-mini", "claude-3-sonnet"],
            },
            {
                "key": "claude-3-sonnet",
                "name": "Claude 3.5 Sonnet",
                "provider": "anthropic",
                "context_window": 200000,
                "max_output": 8192,
                "supports_json": False,
                "supports_tools": True,
                "supports_vision": True,
                "fallback_models": ["claude-3-haiku"],
            },
        ]

        for model in standard_models:
            self.models[model["key"]] = model
            self.tiers["Standard"].append(model["key"])

        return self

    def add_flagship_models(self) -> "ModelConfigBuilder":
        """Add flagship tier models."""
        flagship_models = [
            {
                "key": "gpt-5",
                "name": "GPT-5",
                "provider": "openai",
                "context_window": 200000,
                "max_output": 65536,
                "supports_json": True,
                "supports_tools": True,
                "supports_vision": True,
                "supports_reasoning": True,
                "fallback_models": ["gpt-4o", "claude-3-opus"],
            },
            {
                "key": "claude-3-opus",
                "name": "Claude 3 Opus",
                "provider": "anthropic",
                "context_window": 200000,
                "max_output": 4096,
                "supports_json": False,
                "supports_tools": True,
                "supports_vision": True,
                "fallback_models": ["claude-3-sonnet"],
            },
            {
                "key": "o1-preview",
                "name": "OpenAI o1-preview",
                "provider": "openai",
                "context_window": 128000,
                "max_output": 32768,
                "supports_json": False,
                "supports_tools": False,
                "supports_vision": False,
                "supports_reasoning": True,
                "fallback_models": ["gpt-4o"],
            },
        ]

        for model in flagship_models:
            self.models[model["key"]] = model
            self.tiers["Flagship"].append(model["key"])

        return self

    def set_default_model(self, model_key: str) -> "ModelConfigBuilder":
        """Set the default model.

        Args:
            model_key: Key of the model to set as default
        """
        if model_key in self.models:
            self.default_model = model_key
        else:
            logger.warning(f"Model {model_key} not found, cannot set as default")

        return self

    def build(self) -> Dict[str, Any]:
        """Build the final model configuration.

        Returns:
            Dictionary containing models, tiers, and default
        """
        if not self.default_model and self.models:
            # Set first economy model as default if not specified
            if self.tiers["Economy"]:
                self.default_model = self.tiers["Economy"][0]
            else:
                # Fall back to first available model
                self.default_model = list(self.models.keys())[0]

        return {"models": self.models, "tiers": self.tiers, "default": self.default_model}
