#!/usr/bin/env python3
"""
Prompt Enhancement Module for Voice Transcribe
Handles OpenAI API integration for improving transcripts as LLM prompts
"""

import logging
import os
import re
from typing import Dict, Optional, Tuple

import openai
from dotenv import load_dotenv

from model_config import ModelAdapter, model_registry


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


class FragmentProcessor:
    """Pre-process fragmented transcripts before OpenAI enhancement"""

    def __init__(self):
        # Common abbreviations that should not trigger merging
        self.abbreviations = {
            "Dr.",
            "Mr.",
            "Mrs.",
            "Ms.",
            "Prof.",
            "Sr.",
            "Jr.",
            "St.",
            "Mt.",
            "vs.",
            "No.",
            "etc.",
            "e.g.",
            "i.e.",
            "a.m.",
            "p.m.",
            "ca.",
            "approx.",
            "Inc.",
            "Ltd.",
            "Co.",
            "Corp.",
            "Ph.D.",
            "M.D.",
            "B.A.",
            "M.A.",
            "B.S.",
            "M.S.",
            "Jan.",
            "Feb.",
            "Mar.",
            "Apr.",
            "Jun.",
            "Jul.",
            "Aug.",
            "Sep.",
            "Sept.",
            "Oct.",
            "Nov.",
            "Dec.",
            "U.S.",
            "U.K.",
            "U.S.A.",
            "E.U.",
        }

        # Common single-word valid sentences
        self.valid_single_sentences = {
            "Yes.",
            "No.",
            "Okay.",
            "Right.",
            "Sure.",
            "Thanks.",
            "Hello.",
            "Goodbye.",
            "Stop.",
            "Wait.",
            "Please.",
            "Sorry.",
        }

        # Conjunctions that often start fragmented sentences
        self.starting_conjunctions = {"and", "but", "or", "so", "then", "now", "because", "although", "while"}

    def reconstruct_fragments(self, transcript: str) -> str:
        """Intelligently merge sentence fragments before enhancement"""

        if not transcript:
            return transcript

        # Split on sentence boundaries, keeping the sentence with its punctuation
        # Use a more robust regex that handles various sentence endings
        sentences = re.split(r"(?<=[.!?])\s+", transcript.strip())

        if not sentences:
            return transcript

        # Process sentences for merging
        reconstructed = []
        current_sentence = ""

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()

            if not sentence:
                continue

            # Check if this sentence is a valid standalone
            if self._is_valid_standalone(sentence):
                # Complete any pending merge
                if current_sentence:
                    if not current_sentence.endswith((".", "!", "?")):
                        current_sentence += "."
                    reconstructed.append(current_sentence)
                    current_sentence = ""
                # Add the standalone sentence
                reconstructed.append(sentence)
                continue

            # Get the next sentence for context (if available)
            next_sentence = sentences[i + 1].strip() if i < len(sentences) - 1 else ""

            # Determine if current sentence should be merged with next
            if self._should_merge_with_next(sentence, next_sentence):
                # Start or continue building a merged sentence
                if current_sentence:
                    # Remove period from current and append new fragment
                    if current_sentence.endswith("."):
                        current_sentence = current_sentence[:-1]
                    # Lowercase the first character of the fragment being added
                    if sentence:
                        if sentence.endswith((".", "!", "?")):
                            text_to_add = sentence[:-1]  # Remove ending punctuation
                        else:
                            text_to_add = sentence
                        current_sentence += " " + text_to_add[0].lower() + text_to_add[1:] if text_to_add else ""
                else:
                    # Start a new merged sentence
                    if sentence.endswith((".", "!", "?")):
                        current_sentence = sentence[:-1]  # Remove ending punctuation for merging
                    else:
                        current_sentence = sentence
            else:
                # Complete the current merge and add this sentence
                if current_sentence:
                    # Append current fragment to pending sentence
                    if current_sentence.endswith("."):
                        current_sentence = current_sentence[:-1]
                    if sentence:
                        if sentence.endswith((".", "!", "?")):
                            ending_punct = sentence[-1]
                            text_to_add = sentence[:-1]
                        else:
                            ending_punct = "."
                            text_to_add = sentence
                        current_sentence += " " + text_to_add[0].lower() + text_to_add[1:] if text_to_add else ""
                        current_sentence += ending_punct
                    else:
                        current_sentence += "."
                    reconstructed.append(current_sentence)
                    current_sentence = ""
                else:
                    # No pending merge, add sentence as-is
                    if not sentence.endswith((".", "!", "?")):
                        sentence += "."
                    reconstructed.append(sentence)

        # Don't forget the last sentence if there's a pending merge
        if current_sentence:
            if not current_sentence.endswith((".", "!", "?")):
                current_sentence += "."
            reconstructed.append(current_sentence)

        return " ".join(reconstructed)

    def _is_valid_standalone(self, segment: str) -> bool:
        """Check if a segment is a valid standalone sentence"""

        if not segment:
            return False

        # Check if it's a known valid single sentence
        if segment in self.valid_single_sentences:
            return True

        # Check if it contains an abbreviation (not just ends with)
        for abbrev in self.abbreviations:
            if abbrev in segment:
                # Make sure it's a proper sentence with the abbreviation
                words = segment.split()
                if len(words) >= 2:  # At least abbreviation + one other word
                    return True

        # Check if it's a list item (starts with number or bullet)
        if re.match(r"^\d+\.", segment) or segment.startswith(("- ", "• ", "* ")):
            return True

        # Check if it contains certain patterns that indicate completeness
        # URLs, emails, file paths
        if re.search(r"https?://|www\.|@|\.[a-z]{2,4}/", segment):
            return True

        # Decimal numbers, versions, times
        if re.search(r"\d+\.\d+|\d+:\d+|\d+\.\d+\.\d+", segment):
            return True

        # Check if it's a reasonably complete sentence (more than 4 words)
        words = segment.rstrip(".!?").split()
        if len(words) >= 5:
            return True

        return False

    def _should_merge_with_next(self, current: str, next_seg: str) -> bool:
        """Determine if current segment should be merged with the next one"""

        if not current or not next_seg:
            return False

        # Never merge if current ends with ? or !
        if current.endswith(("?", "!")):
            return False

        # If both are reasonably complete sentences, don't merge
        current_words = current.rstrip(".").split()
        next_words = next_seg.rstrip(".!?").split()

        # Don't merge two complete sentences (both >= 4 words)
        if len(current_words) >= 4 and len(next_words) >= 4:
            # Unless next starts with lowercase (clear continuation)
            next_text = next_seg.lstrip("- •* ")
            if next_text and not next_text[0].islower():
                return False

        # Check if current segment is very short (likely a fragment)
        if len(current_words) <= 2:
            # But not if it's a valid standalone
            if not self._is_valid_standalone(current):
                return True

        # Check if next segment starts with lowercase (continuation)
        next_text = next_seg.lstrip("- •* ")
        if next_text and next_text[0].islower():
            # But not if current contains an abbreviation that ends a sentence
            for abbrev in self.abbreviations:
                if current.endswith(abbrev):
                    # Check if this looks like the end of a sentence
                    # (e.g., "I met Dr. Smith." vs "Written by J.")
                    if abbrev in current and len(current_words) >= 3:
                        return False
            return True

        # Check if next starts with a conjunction
        next_first_word = next_text.split()[0].lower() if next_text.split() else ""
        if next_first_word in self.starting_conjunctions:
            # But only if current segment is short
            if len(current_words) <= 3:
                return True

        # Check if current ends with a preposition or conjunction
        if current_words:
            last_word = current_words[-1].rstrip(".,!?").lower()
            if last_word in {
                "the",
                "a",
                "an",
                "to",
                "of",
                "in",
                "on",
                "at",
                "by",
                "for",
                "with",
                "from",
                "and",
                "or",
                "but",
                "that",
                "which",
                "who",
            }:
                return True

        return False


# Enhancement style prompts with fragment awareness
ENHANCEMENT_PROMPTS = {
    "concise": """You are a prompt optimization expert. The following voice transcript may contain over-punctuated sentence fragments due to transcription errors.

First, intelligently merge any fragments that should be part of the same sentence. Then rewrite as a clear, concise prompt for an AI assistant.

Remove filler words, fix grammar, merge fragments naturally, and structure it for maximum clarity while preserving the user's intent. Keep it brief but complete.

Example input: "So I need. A Python function. That reads. CSV files."
Example output: "Create a Python function that reads CSV files."

Important: Preserve abbreviations (Dr., U.S.), decimals (3.14), times (3:30 p.m.), and legitimate list structures.""",
    "balanced": """You are a prompt optimization expert. This voice transcript may contain fragmented sentences due to transcription punctuation errors.

Your task:
1. Identify and merge sentence fragments that belong together
2. Fix grammar and remove filler words
3. Add helpful context and structure
4. Clarify ambiguous requests
5. Preserve the user's intent and tone

Make it clear and effective without being overly verbose. Focus on creating a cohesive, well-structured prompt from potentially fragmented input.

Example: "Good morning. Everyone. Let's discuss. The project timeline." → "Good morning everyone, let's discuss the project timeline."

Note: Respect abbreviations, decimals, URLs, version numbers, and legitimate list boundaries.""",
    "detailed": """You are a prompt optimization expert. The input transcript likely contains over-punctuated sentence fragments due to voice transcription errors.

Process this transcript by:
1. Intelligently merging sentence fragments into coherent thoughts
2. Fixing all grammar and transcription errors
3. Adding relevant context and background
4. Breaking down complex requests into clear steps
5. Suggesting additional details that might be helpful
6. Structuring for maximum AI comprehension

Be thorough but maintain focus on the user's goal. Transform fragmented input into a comprehensive, well-structured prompt.

Note: Input may look like "So I want. To create. A machine learning. Model that. Predicts customer. Behavior." - merge these fragments into natural, flowing sentences.

Important: Preserve technical terms, abbreviations (Ph.D., e.g.), decimals, times, URLs, and maintain legitimate list structures.""",
}


def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (1 token ≈ 4 characters)"""
    return len(text) // 4


def estimate_tokens_with_fragments(text: str) -> int:
    """Enhanced token estimation accounting for fragment processing overhead"""
    base_tokens = len(text) // 4

    # Add overhead for fragment processing
    # Count sentence boundaries to estimate fragmentation level
    fragment_count = text.count(". ") + text.count("? ") + text.count("! ")

    if fragment_count > 10:  # High fragmentation
        overhead = int(base_tokens * 0.2)  # 20% overhead for processing
    elif fragment_count > 5:
        overhead = int(base_tokens * 0.1)  # 10% overhead
    else:
        overhead = 0

    return base_tokens + overhead


def enhance_prompt(
    transcript: str,
    style: str = "balanced",
    model_key: Optional[str] = None,
    model_name: Optional[str] = None,
    fragment_processing_config: Optional[Dict] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Enhance a voice transcript into an optimized LLM prompt

    Args:
        transcript: Raw transcript from Deepgram
        style: Enhancement style ('concise', 'balanced', 'detailed')
        model_key: Model key/ID from UI selection (preferred over model_name)
        model_name: Specific model to use (deprecated, use model_key)
        fragment_processing_config: Optional config for fragment processing

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

    # Get fragment processing configuration
    if fragment_processing_config is None:
        fragment_processing_config = {}

    # Check if fragment processing is enabled (default: True)
    fragment_processing_enabled = fragment_processing_config.get("enabled", True)

    # Pre-process fragments if enabled
    if fragment_processing_enabled:
        fragment_processor = FragmentProcessor()
        processed_transcript = fragment_processor.reconstruct_fragments(transcript)
    else:
        processed_transcript = transcript

    # Log fragment processing for analytics
    if processed_transcript != transcript:
        original_segments = len([s for s in re.split(r"[.!?]\s+", transcript) if s.strip()])
        processed_segments = len([s for s in re.split(r"[.!?]\s+", processed_transcript) if s.strip()])
        logger.info(f"Fragment processing applied: {original_segments} → {processed_segments} segments")

    # Check token limits with fragment-aware estimation
    if estimate_tokens_with_fragments(processed_transcript) > 3000:
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
        # Prepare messages with processed transcript
        messages = [
            {"role": "system", "content": ENHANCEMENT_PROMPTS[style]},
            {"role": "user", "content": processed_transcript},  # Use processed version
        ]

        # Prepare additional parameters
        # Use model's configured max_tokens_value (increased for GPT-5 to account for reasoning tokens)
        max_tokens = model_config.max_tokens_value

        call_params = {
            "model_name": model_name,
            "messages": messages,
            "max_tokens": max_tokens,  # Will be mapped to correct parameter
            "temperature": 0.3,  # Will be constrained to model limits
            "style": style,  # Pass style for GPT-5 temperature constraint handling
        }

        # GPT-5 verbosity bug workaround:
        # GPT-5 has a bug where ANY verbosity parameter combined with reasoning_effort
        # causes empty content to be returned. We must omit verbosity entirely.
        # GPT-4.1 models also do NOT support verbosity parameter at all.
        # So we skip verbosity for both GPT-4.1 and GPT-5 models.
        if (
            model_config.supports_verbosity
            and "gpt-4.1" not in model_config.model_name
            and "gpt-5" not in model_config.model_name
        ):
            # Only add verbosity for future models that properly support it
            verbosity_map = {"concise": "low", "balanced": "medium", "detailed": "high"}
            call_params["verbosity"] = verbosity_map.get(style, "medium")

        # Add reasoning_effort parameter for GPT-5 models
        # IMPORTANT: GPT-5 has a bug where reasoning_effort='medium' or 'high'
        # causes empty content to be returned. We must use 'low' only.
        if model_config.supports_reasoning_effort:
            # GPT-5 bug workaround: always use 'low' reasoning_effort
            call_params["reasoning_effort"] = "low"
            logger.info("Using reasoning_effort='low' for GPT-5 (API bug workaround)")

            # For GPT-5 models with temperature constraints, use fixed temperature
            if model_config.temperature_constrained:
                call_params["temperature"] = 1.0  # GPT-5 only accepts temperature=1.0
                logger.info("Using fixed temperature 1.0 for GPT-5 model (API constraint)")

        # Use model adapter for API call with automatic fallback
        response = model_adapter.call_with_fallback(**call_params)

        if not response:
            return None, "Enhancement failed - API call returned no response"

        # Extract content from response
        enhanced = response.choices[0].message.content.strip()

        # Log token usage and cost
        if hasattr(response, "usage"):
            cost = model_config.estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)
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
        if any(
            param in error_str for param in ["max_tokens", "max_completion_tokens", "reasoning_effort", "verbosity"]
        ):
            logger.warning(f"Parameter error detected, model adapter will handle fallback: {sanitize_error_message(str(e))}")
        return None, f"OpenAI API error: {sanitize_error_message(str(e))}"
    except (ValueError, TypeError, AttributeError, KeyError) as e:
        # Handle common Python runtime errors
        safe_error = sanitize_error_message(str(e))
        logger.error(f"Unexpected error in enhancement: {safe_error}")
        return None, f"Unexpected error: {safe_error}"


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
        model_info.append(
            {
                "name": m.model_name,
                "display": m.display_name,
                "status": status,
                "available_from": m.available_from,
                "tier": tier_info["tier"],
                "tier_color": tier_info["color"],
                "cost_per_1k_input": m.cost_per_1k_input,
                "cost_per_1k_output": m.cost_per_1k_output,
                "supports_gpt5_features": m.supports_reasoning_effort,
                "context_window": m.context_window,
            }
        )
    return model_info


def get_models_by_tier():
    """Return models grouped by tier for UI"""
    models = model_registry.get_available_models()
    by_tier = {"economy": [], "standard": [], "premium": [], "flagship": []}

    for model in models:
        tier_info = model.get_tier_info()
        by_tier[model.tier].append(
            {
                "name": model.model_name,
                "display": model.display_name,
                "cost_input": model.cost_per_1k_input,
                "cost_output": model.cost_per_1k_output,
                "features": {
                    "verbosity": model.supports_verbosity,
                    "reasoning_effort": model.supports_reasoning_effort,
                    "json_mode": model.supports_json_mode,
                },
            }
        )

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
