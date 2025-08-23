#!/usr/bin/env python3
"""Application configuration and constants."""

import os

# Audio Configuration
AUDIO_CONFIG = {
    'SAMPLE_RATE': 16000,
    'CHUNK_DURATION': 0.1,  # 100ms chunks
}

# Deepgram Configuration
DEEPGRAM_CONFIG = {
    'MODEL': os.environ.get('DEEPGRAM_MODEL', 'nova-3'),
    'LANGUAGE': os.environ.get('DEEPGRAM_LANGUAGE', 'en-US'),
    'SMART_FORMAT': True,
    'PUNCTUATE': True,
    'DIARIZE': False,
    'ENDPOINTING': 300,  # Default endpointing threshold in ms
}

# Enhancement Configuration
ENHANCEMENT_CONFIG = {
    'DEFAULT_STYLE': 'balanced',
    'DEFAULT_MODEL': os.environ.get('ENHANCEMENT_MODEL', 'gpt-4o-mini'),
    'MAX_TOKENS': 500,
    'TEMPERATURE': 0.3,
    'TIMEOUT': 10,  # seconds
}

# UI Colors
COLORS = {
    'bg': '#1e1e2e',              # Dark background
    'button_idle': '#45475a',      # Gray
    'button_recording': '#f38ba8', # Red/Pink
    'button_hover': '#89b4fa',     # Blue
    'text': '#cdd6f4',            # Light text
    'accent': '#89b4fa',          # Blue accent
    'success': '#a6e3a1',         # Green
    'danger': '#f38ba8',          # Red
    'enhanced_bg': '#313244',     # Slightly lighter for enhanced panel
    'warning': '#f9e2af',         # Yellow for warnings
}

# Application Settings
APP_CONFIG = {
    'TITLE': 'Voice Transcribe v3.3',
    'HISTORY_FILE': os.path.expanduser('~/.local/share/voice-transcribe/history.jsonl'),
    'CONFIG_FILE': os.path.expanduser('~/.config/voice-transcribe/config.json'),
    'WINDOW_WIDTH': 700,
    'WINDOW_HEIGHT': 900,
}

# Timing Configuration
TIMING_CONFIG = {
    'PASTE_DELAY': 0.5,  # Delay before auto-paste in seconds
    'STATUS_RESET_DELAY': 2,  # Delay before resetting status messages
    'CLIPBOARD_STATUS_DURATION': 2,  # How long to show clipboard status
    'TERMINAL_DETECTION_CACHE_TTL': 2,  # Cache TTL in seconds
}

# Default Preferences
DEFAULT_PREFERENCES = {
    'prompt_mode': False,
    'enhancement_style': 'balanced',
    'punctuation_sensitivity': 'balanced',
    'endpointing_threshold': 300,
    'enable_profanity': False,
    'enable_capitalization': True,
    'fragment_threshold': 0.85,
    'custom_keyterms': [],  # Nova-3 keyterm prompting
}

def get_config(section, key, default=None):
    """Get configuration value with environment override support."""
    env_key = f"{section.upper()}_{key.upper()}"
    env_value = os.environ.get(env_key)
    
    if env_value is not None:
        # Convert string to appropriate type
        if default is not None:
            if isinstance(default, bool):
                return env_value.lower() in ('true', '1', 'yes')
            elif isinstance(default, int):
                try:
                    return int(env_value)
                except ValueError:
                    return default
            elif isinstance(default, float):
                try:
                    return float(env_value)
                except ValueError:
                    return default
        return env_value
    
    # Return from config dict or default
    config_dict = globals().get(f"{section}_CONFIG", {})
    return config_dict.get(key, default)