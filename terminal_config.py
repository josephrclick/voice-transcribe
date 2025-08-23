#!/usr/bin/env python3
"""Terminal detection configuration and constants."""

# Terminal window class/name patterns for detection
TERMINAL_PATTERNS = [
    # Standard terminal emulators
    "gnome-terminal-server",
    "gnome-terminal",
    "konsole",
    "xterm",
    "alacritty",
    "kitty",
    "terminator",
    "tilix",
    "urxvt",
    "rxvt",
    "st",
    "st-256color",
    "foot",
    "wezterm",
    "hyper",
    "yakuake",
    "org.gnome.terminal",
    "org.gnome.console",
    "terminal",
    # Additional patterns
    "guake",
    "tilda",
    "terminology",
    "sakura",
    "lxterminal",
    "mate-terminal",
    "xfce4-terminal",
    "qterminal",
]

# VS Code/Cursor and other IDE patterns that need special handling
CODE_IDE_PATTERNS = [
    "code",
    "cursor",
    "vscodium",
    "code-oss",
    "sublime_text",
    "atom",
]

# Terminal title keywords that indicate terminal focus in IDEs
TERMINAL_TITLE_KEYWORDS = [
    "terminal",
    "bash",
    "zsh",
    "fish",
    "shell",
    "console",
    "powershell",
    "cmd",
]


def is_terminal_pattern(text):
    """Check if text matches any terminal pattern."""
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in TERMINAL_PATTERNS)


def is_code_ide_pattern(text):
    """Check if text matches any code IDE pattern."""
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in CODE_IDE_PATTERNS)


def has_terminal_title_keyword(text):
    """Check if text contains terminal-related keywords."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in TERMINAL_TITLE_KEYWORDS)
