#!/usr/bin/env python3
"""Paste strategies for different environments and window types."""

import subprocess
import logging
import time
import pyperclip
from abc import ABC, abstractmethod
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class PasteStrategy(ABC):
    """Abstract base class for paste strategies."""
    
    @abstractmethod
    def name(self) -> str:
        """Return the name of this strategy."""
        pass
    
    @abstractmethod
    def supports(self, session_type: str, is_terminal: bool) -> bool:
        """Check if this strategy supports the given context."""
        pass
    
    @abstractmethod
    def execute(self) -> bool:
        """Execute the paste operation. Return True if successful."""
        pass


class XdotoolCtrlShiftVStrategy(PasteStrategy):
    """Paste using xdotool with Ctrl+Shift+V (for terminals on X11)."""
    
    def name(self) -> str:
        return "xdotool-ctrl-shift-v"
    
    def supports(self, session_type: str, is_terminal: bool) -> bool:
        return session_type == 'x11' and is_terminal
    
    def execute(self) -> bool:
        try:
            subprocess.run(
                ['xdotool', 'key', '--clearmodifiers', 'ctrl+shift+v'],
                check=True,
                capture_output=True
            )
            logger.info("Auto-pasted to terminal with xdotool (ctrl+shift+v)")
            return True
        except subprocess.CalledProcessError as e:
            logger.debug(f"xdotool ctrl+shift+v failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error with xdotool ctrl+shift+v: {e}")
            return False


class XdotoolShiftInsertStrategy(PasteStrategy):
    """Paste using xdotool with Shift+Insert (universal terminal fallback)."""
    
    def name(self) -> str:
        return "xdotool-shift-insert"
    
    def supports(self, session_type: str, is_terminal: bool) -> bool:
        return session_type == 'x11' and is_terminal
    
    def execute(self) -> bool:
        try:
            subprocess.run(
                ['xdotool', 'key', '--clearmodifiers', 'shift+Insert'],
                check=True,
                capture_output=True
            )
            logger.info("Auto-pasted to terminal with xdotool (shift+Insert)")
            return True
        except subprocess.CalledProcessError as e:
            logger.debug(f"xdotool shift+Insert failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error with xdotool shift+Insert: {e}")
            return False


class XdotoolTypeStrategy(PasteStrategy):
    """Type content directly using xdotool (last resort for terminals)."""
    
    def name(self) -> str:
        return "xdotool-type"
    
    def supports(self, session_type: str, is_terminal: bool) -> bool:
        return session_type == 'x11' and is_terminal
    
    def execute(self) -> bool:
        try:
            content = pyperclip.paste()
            if not content:
                logger.debug("No content in clipboard to type")
                return False
            
            subprocess.run(
                ['xdotool', 'type', '--clearmodifiers', '--delay', '10', content],
                check=True,
                capture_output=True
            )
            logger.info("Auto-typed content into terminal with xdotool")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"xdotool type failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error with xdotool type: {e}")
            return False


class XdotoolCtrlVStrategy(PasteStrategy):
    """Paste using xdotool with Ctrl+V (for non-terminals on X11)."""
    
    def name(self) -> str:
        return "xdotool-ctrl-v"
    
    def supports(self, session_type: str, is_terminal: bool) -> bool:
        return session_type == 'x11' and not is_terminal
    
    def execute(self) -> bool:
        try:
            subprocess.run(
                ['xdotool', 'key', '--clearmodifiers', 'ctrl+v'],
                check=True,
                capture_output=True
            )
            logger.info("Auto-pasted with xdotool (ctrl+v)")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"xdotool ctrl+v failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error with xdotool ctrl+v: {e}")
            return False


class WtypeCtrlShiftVStrategy(PasteStrategy):
    """Paste using wtype with Ctrl+Shift+V (for terminals on Wayland)."""
    
    def name(self) -> str:
        return "wtype-ctrl-shift-v"
    
    def supports(self, session_type: str, is_terminal: bool) -> bool:
        return session_type == 'wayland' and is_terminal
    
    def execute(self) -> bool:
        try:
            subprocess.run(
                ['wtype', '-M', 'ctrl', '-M', 'shift', '-k', 'v', 
                 '-m', 'ctrl', '-m', 'shift'],
                check=True,
                capture_output=True
            )
            logger.info("Auto-pasted to terminal with wtype (ctrl+shift+v)")
            return True
        except subprocess.CalledProcessError as e:
            logger.debug(f"wtype ctrl+shift+v failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error with wtype ctrl+shift+v: {e}")
            return False


class WtypeShiftInsertStrategy(PasteStrategy):
    """Paste using wtype with Shift+Insert (for terminals on Wayland)."""
    
    def name(self) -> str:
        return "wtype-shift-insert"
    
    def supports(self, session_type: str, is_terminal: bool) -> bool:
        return session_type == 'wayland' and is_terminal
    
    def execute(self) -> bool:
        try:
            subprocess.run(
                ['wtype', '-M', 'shift', '-k', 'Insert', '-m', 'shift'],
                check=True,
                capture_output=True
            )
            logger.info("Auto-pasted to terminal with wtype (shift+Insert)")
            return True
        except subprocess.CalledProcessError as e:
            logger.debug(f"wtype shift+Insert failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error with wtype shift+Insert: {e}")
            return False


class WtypeDirectStrategy(PasteStrategy):
    """Type content directly using wtype (fallback for all Wayland)."""
    
    def name(self) -> str:
        return "wtype-direct"
    
    def supports(self, session_type: str, is_terminal: bool) -> bool:
        return session_type == 'wayland'
    
    def execute(self) -> bool:
        try:
            content = pyperclip.paste()
            if not content:
                logger.debug("No content in clipboard to type")
                return False
            
            subprocess.run(
                ['wtype', content],
                check=True,
                capture_output=True
            )
            logger.info("Auto-typed content with wtype")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"wtype direct typing failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error with wtype direct: {e}")
            return False


class WtypeCtrlVStrategy(PasteStrategy):
    """Paste using wtype with Ctrl+V (for non-terminals on Wayland)."""
    
    def name(self) -> str:
        return "wtype-ctrl-v"
    
    def supports(self, session_type: str, is_terminal: bool) -> bool:
        return session_type == 'wayland' and not is_terminal
    
    def execute(self) -> bool:
        try:
            subprocess.run(
                ['wtype', '-M', 'ctrl', '-k', 'v', '-m', 'ctrl'],
                check=True,
                capture_output=True
            )
            logger.info("Auto-pasted with wtype (ctrl+v)")
            return True
        except subprocess.CalledProcessError as e:
            logger.debug(f"wtype ctrl+v failed: {e}")
            # Try direct typing as fallback
            return WtypeDirectStrategy().execute()
        except Exception as e:
            logger.error(f"Unexpected error with wtype ctrl+v: {e}")
            return False


class PasteStrategyManager:
    """Manages and executes paste strategies based on context."""
    
    def __init__(self):
        """Initialize with all available strategies in priority order."""
        self.strategies = [
            # X11 Terminal strategies (in order of preference)
            XdotoolCtrlShiftVStrategy(),
            XdotoolShiftInsertStrategy(),
            XdotoolTypeStrategy(),
            
            # X11 Non-terminal strategies
            XdotoolCtrlVStrategy(),
            
            # Wayland Terminal strategies (in order of preference)
            WtypeCtrlShiftVStrategy(),
            WtypeShiftInsertStrategy(),
            
            # Wayland Non-terminal strategies
            WtypeCtrlVStrategy(),
            
            # Wayland fallback (works for both terminal and non-terminal)
            WtypeDirectStrategy(),
        ]
    
    def execute_paste(self, session_type: str, is_terminal: bool) -> bool:
        """Execute the appropriate paste strategy based on context.
        
        Args:
            session_type: 'x11' or 'wayland'
            is_terminal: Whether the active window is a terminal
            
        Returns:
            True if paste was successful, False otherwise
        """
        applicable_strategies = [
            s for s in self.strategies 
            if s.supports(session_type, is_terminal)
        ]
        
        if not applicable_strategies:
            logger.warning(f"No paste strategies available for {session_type}, terminal={is_terminal}")
            return False
        
        logger.debug(f"Trying {len(applicable_strategies)} paste strategies for {session_type}, terminal={is_terminal}")
        
        for strategy in applicable_strategies:
            logger.debug(f"Attempting paste with {strategy.name()}")
            if strategy.execute():
                return True
        
        logger.error(f"All paste strategies failed for {session_type}, terminal={is_terminal}")
        return False