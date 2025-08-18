#!/usr/bin/env python3
"""
Prompt Enhancement Module for Voice Transcribe
Handles OpenAI API integration for improving transcripts as LLM prompts
"""

import os
import time
import logging
from typing import Optional, Tuple
import openai
from dotenv import load_dotenv
from model_config import model_registry, ModelAdapter

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client if API key is available
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ImportError("OPENAI_API_KEY not set")
client = openai.OpenAI(api_key=api_key)

# Initialize model adapter for dynamic parameter handling
model_adapter = ModelAdapter(client)

# Enhancement style prompts
ENHANCEMENT_PROMPTS = {
    "concise": """You are a prompt optimization expert. Rewrite the following voice transcript as a clear, concise prompt for an AI assistant. 
Remove filler words, fix grammar, and structure it for maximum clarity while preserving the user's intent.
Keep it brief but complete.""",
    
    "balanced": """You are a prompt optimization expert. Transform this voice transcript into a well-structured prompt for an AI assistant.
- Fix grammar and remove filler words
- Add helpful context and structure
- Clarify ambiguous requests
- Preserve the user's intent and tone
Make it clear and effective without being overly verbose.""",
    
    "detailed": """You are a prompt optimization expert. Enhance this voice transcript into a comprehensive prompt for an AI assistant.
- Fix all grammar and transcription errors
- Add relevant context and background
- Break down complex requests into clear steps
- Suggest additional details that might be helpful
- Structure it for maximum AI comprehension
Be thorough but maintain focus on the user's goal."""
}

def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (1 token ≈ 4 characters)"""
    return len(text) // 4

def enhance_prompt(transcript: str, style: str = "balanced", model_key: Optional[str] = None, model_name: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Enhance a voice transcript into an optimized LLM prompt
    
    Args:
        transcript: Raw transcript from Deepgram
        style: Enhancement style ('concise', 'balanced', 'detailed')
        model_key: Model key/ID from UI selection (preferred over model_name)
        model_name: Specific model to use (deprecated, use model_key)
    
    Returns:
        Tuple of (enhanced_prompt, error_message)
        If successful, error_message is None
        If failed, enhanced_prompt is None
    """
    
    # Quick validation
    if not transcript or not transcript.strip():
        return None, "Empty transcript"
    
    if style not in ENHANCEMENT_PROMPTS:
        style = "balanced"
    
    # Check token limits (leaving room for response)
    if estimate_tokens(transcript) > 3000:
        return None, "Transcript too long for enhancement"
    
    # Get model configuration (prefer model_key over model_name)
    if model_key:
        model_config = model_registry.get(model_key)
        if not model_config:
            logger.warning(f"Model {model_key} not found, using default")
            model_config = model_registry.get_default_model()
            model_name = model_config.model_name
        else:
            model_name = model_key
    elif model_name:
        model_config = model_registry.get(model_name)
        if not model_config:
            logger.warning(f"Model {model_name} not found, using default")
            model_config = model_registry.get_default_model()
            model_name = model_config.model_name
    else:
        model_config = model_registry.get_default_model()
        model_name = model_config.model_name
    
    # Check if model is available
    if not model_config.is_available():
        logger.info(f"Model {model_name} not available, using default")
        model_config = model_registry.get_default_model()
        model_name = model_config.model_name
    
    try:
        # Prepare messages
        messages = [
            {"role": "system", "content": ENHANCEMENT_PROMPTS[style]},
            {"role": "user", "content": transcript}
        ]
        
        # Prepare additional parameters
        call_params = {
            "model_name": model_name,
            "messages": messages,
            "max_tokens": 1000,  # Will be mapped to correct parameter
            "temperature": 0.3,  # Will be constrained to model limits
            "style": style  # Pass style for GPT-5 temperature constraint handling
        }
        
        # Add verbosity parameter if model supports it (GPT-4.1/GPT-5 feature)
        if model_config.supports_verbosity:
            # Map enhancement style to verbosity level
            # Note: GPT-4.1 models only support "medium" verbosity
            if "gpt-4.1" in model_config.model_name:
                call_params["verbosity"] = "medium"  # GPT-4.1 constraint
            else:
                verbosity_map = {
                    "concise": "low",
                    "balanced": "medium",
                    "detailed": "high"
                }
                call_params["verbosity"] = verbosity_map.get(style, "medium")
        
        # Add reasoning_effort parameter for GPT-5 models
        if model_config.supports_reasoning_effort:
            # Map enhancement style to reasoning effort
            reasoning_effort_map = {
                "concise": "low",
                "balanced": "medium", 
                "detailed": "high"
            }
            call_params["reasoning_effort"] = reasoning_effort_map.get(style, "medium")
            
            # For GPT-5 models with temperature constraints, use fixed temperature
            if model_config.temperature_constrained:
                call_params["temperature"] = 1.0  # GPT-5 only accepts temperature=1.0
                logger.info(f"Using fixed temperature 1.0 for GPT-5 model (API constraint)")
        
        # Use model adapter for API call with automatic fallback
        response = model_adapter.call_with_fallback(**call_params)
        
        if not response:
            return None, "Enhancement failed - API call returned no response"
        
        enhanced = response.choices[0].message.content.strip()
        
        # Log token usage and cost
        if hasattr(response, 'usage'):
            cost = model_config.estimate_cost(
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )
            tier_info = model_config.get_tier_info()
            logger.info(
                f"Enhancement completed - Model: {model_config.display_name} ({tier_info['tier']}), "
                f"Style: {style}, Cost: ${cost:.4f}"
            )
        
        # Sanity check - enhancement shouldn't be empty or too short
        if not enhanced or len(enhanced) < 10:
            return None, "Enhancement produced invalid output"
        
        return enhanced, None
        
    except openai.APITimeoutError:
        return None, "Enhancement timed out (15s limit)"
    except openai.APIConnectionError:
        return None, "Connection error - check internet"
    except openai.APIError as e:
        # Check for parameter-related errors and attempt migration
        error_str = str(e).lower()
        if any(param in error_str for param in ["max_tokens", "max_completion_tokens", "reasoning_effort", "verbosity"]):
            logger.warning(f"Parameter error detected, model adapter will handle fallback: {e}")
        return None, f"OpenAI API error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in enhancement: {e}")
        return None, f"Unexpected error: {str(e)}"

def get_enhancement_styles():
    """Return available enhancement styles for UI"""
    return ["concise", "balanced", "detailed"]

def get_available_models():
    """Return currently available models for UI"""
    models = model_registry.get_available_models()
    return [(m.model_name, m.display_name) for m in models]

def get_all_models():
    """Return all models (including future ones) for UI"""
    models = model_registry.get_all_models()
    model_info = []
    for m in models:
        status = "Available" if m.is_available() else "Coming Soon"
        if m.deprecated:
            status = "Deprecated"
        
        tier_info = m.get_tier_info()
        model_info.append({
            "name": m.model_name,
            "display": m.display_name,
            "status": status,
            "available_from": m.available_from,
            "tier": tier_info["tier"],
            "tier_color": tier_info["color"],
            "cost_per_1k_input": m.cost_per_1k_input,
            "cost_per_1k_output": m.cost_per_1k_output,
            "supports_gpt5_features": m.supports_reasoning_effort,
            "context_window": m.context_window
        })
    return model_info

def get_models_by_tier():
    """Return models grouped by tier for UI"""
    models = model_registry.get_available_models()
    by_tier = {"economy": [], "standard": [], "premium": []}
    
    for model in models:
        tier_info = model.get_tier_info()
        by_tier[model.tier].append({
            "name": model.model_name,
            "display": model.display_name,
            "cost_input": model.cost_per_1k_input,
            "cost_output": model.cost_per_1k_output,
            "features": {
                "verbosity": model.supports_verbosity,
                "reasoning_effort": model.supports_reasoning_effort,
                "json_mode": model.supports_json_mode
            }
        })
    
    return by_tier

def get_usage_statistics():
    """Get usage statistics from the model adapter"""
    return model_adapter.get_usage_stats()

def reset_usage_statistics():
    """Reset usage statistics"""
    model_adapter.reset_usage_stats()
    logger.info("Enhancement usage statistics reset")

def estimate_enhancement_cost(transcript: str, model_name: str = None) -> float:
    """Estimate cost for enhancing a transcript with a specific model"""
    if not model_name:
        model_name = "gpt-4o-mini"
    
    config = model_registry.get(model_name)
    if not config:
        return 0.0
    
    # Estimate tokens (rough approximation)
    input_tokens = estimate_tokens(transcript) + 50  # Add system prompt tokens
    output_tokens = min(input_tokens * 1.5, config.max_tokens_value)  # Estimate output
    
    return config.estimate_cost(input_tokens, output_tokens)

# Quick test function
if __name__ == "__main__":
    test_transcript = "um so like I need a python function that uh reads a CSV file and you know removes all the duplicate rows but keeps the first one"
    print("Testing enhancement...")
    enhanced, error = enhance_prompt(test_transcript, "balanced")
    if enhanced:
        print(f"Original: {test_transcript}")
        print(f"Enhanced: {enhanced}")
    else:
        print(f"Error: {error}")