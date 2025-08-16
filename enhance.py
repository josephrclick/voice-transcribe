#!/usr/bin/env python3
"""
Prompt Enhancement Module for Voice Transcribe
Handles OpenAI API integration for improving transcripts as LLM prompts
"""

import os
import time
from typing import Optional, Tuple
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client if API key is available
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ImportError("OPENAI_API_KEY not set")
client = openai.OpenAI(api_key=api_key)

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

def enhance_prompt(transcript: str, style: str = "balanced") -> Tuple[Optional[str], Optional[str]]:
    """
    Enhance a voice transcript into an optimized LLM prompt
    
    Args:
        transcript: Raw transcript from Deepgram
        style: Enhancement style ('concise', 'balanced', 'detailed')
    
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
    
    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": ENHANCEMENT_PROMPTS[style]},
                {"role": "user", "content": transcript}
            ],
            max_tokens=1000,
            temperature=0.3,  # Lower temperature for consistency
            timeout=15.0  # 15 second timeout for longer transcriptions
        )
        
        enhanced = response.choices[0].message.content.strip()
        
        # Sanity check - enhancement shouldn't be empty or too short
        if not enhanced or len(enhanced) < 10:
            return None, "Enhancement produced invalid output"
        
        return enhanced, None
        
    except openai.APITimeoutError:
        return None, "Enhancement timed out (15s limit)"
    except openai.APIConnectionError:
        return None, "Connection error - check internet"
    except openai.APIError as e:
        return None, f"OpenAI API error: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def get_enhancement_styles():
    """Return available enhancement styles for UI"""
    return ["concise", "balanced", "detailed"]

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