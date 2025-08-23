#!/usr/bin/env python3
"""Subprocess utilities with caching and optimization for performance."""

import subprocess
import time
import logging
from typing import Optional, Dict, Tuple, Any
from threading import Lock

logger = logging.getLogger(__name__)


class SubprocessManager:
    """Manages subprocess calls with caching and optimization."""
    
    def __init__(self, default_cache_ttl: float = 2.0):
        """Initialize the subprocess manager.
        
        Args:
            default_cache_ttl: Default time-to-live for cached results in seconds
        """
        self._command_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_lock = Lock()
        self.default_cache_ttl = default_cache_ttl
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'subprocess_calls': 0,
            'total_calls': 0
        }
    
    def _cache_key(self, cmd: list) -> str:
        """Generate a cache key from a command list."""
        return '|'.join(str(arg) for arg in cmd)
    
    def run_cached(self, 
                   cmd: list, 
                   cache_ttl: Optional[float] = None,
                   check: bool = True,
                   capture_output: bool = True,
                   text: bool = True,
                   timeout: Optional[float] = None) -> subprocess.CompletedProcess:
        """Run a subprocess command with caching.
        
        Args:
            cmd: Command list to execute
            cache_ttl: Time-to-live for this cache entry (uses default if None)
            check: Whether to check return code
            capture_output: Whether to capture stdout/stderr
            text: Whether to decode output as text
            timeout: Command timeout in seconds
            
        Returns:
            CompletedProcess object (cached or fresh)
        """
        self._stats['total_calls'] += 1
        
        # Generate cache key
        cache_key = self._cache_key(cmd)
        ttl = cache_ttl if cache_ttl is not None else self.default_cache_ttl
        
        # Check cache
        with self._cache_lock:
            if cache_key in self._command_cache:
                cached_result, cached_time = self._command_cache[cache_key]
                if time.time() - cached_time < ttl:
                    self._stats['cache_hits'] += 1
                    logger.debug(f"Cache hit for command: {' '.join(cmd)}")
                    return cached_result
        
        # Cache miss - execute command
        self._stats['cache_misses'] += 1
        self._stats['subprocess_calls'] += 1
        logger.debug(f"Cache miss, executing: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=capture_output,
                text=text,
                timeout=timeout
            )
            
            # Cache successful results
            if not check or result.returncode == 0:
                with self._cache_lock:
                    self._command_cache[cache_key] = (result, time.time())
            
            return result
            
        except subprocess.CalledProcessError as e:
            # Don't cache failures
            logger.debug(f"Command failed: {e}")
            raise
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Command timed out: {e}")
            raise
    
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cached results.
        
        Args:
            pattern: If provided, only clear cache entries containing this pattern
        """
        with self._cache_lock:
            if pattern:
                keys_to_remove = [k for k in self._command_cache if pattern in k]
                for key in keys_to_remove:
                    del self._command_cache[key]
                logger.debug(f"Cleared {len(keys_to_remove)} cache entries matching '{pattern}'")
            else:
                count = len(self._command_cache)
                self._command_cache.clear()
                logger.debug(f"Cleared all {count} cache entries")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = self._stats.copy()
        stats['cache_size'] = len(self._command_cache)
        if stats['total_calls'] > 0:
            stats['hit_rate'] = stats['cache_hits'] / stats['total_calls']
        else:
            stats['hit_rate'] = 0.0
        return stats
    
    def batch_run(self, commands: list, cache_ttl: Optional[float] = None) -> list:
        """Run multiple commands efficiently.
        
        Args:
            commands: List of command lists to execute
            cache_ttl: Time-to-live for cache entries
            
        Returns:
            List of CompletedProcess objects
        """
        results = []
        for cmd in commands:
            try:
                result = self.run_cached(cmd, cache_ttl=cache_ttl)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to execute {cmd}: {e}")
                results.append(None)
        return results


# Global instance for convenience
_global_manager = SubprocessManager()


def run_cached(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    """Convenience function using global subprocess manager.
    
    Args:
        cmd: Command list to execute
        **kwargs: Additional arguments for SubprocessManager.run_cached
        
    Returns:
        CompletedProcess object
    """
    return _global_manager.run_cached(cmd, **kwargs)


def get_subprocess_stats() -> Dict[str, int]:
    """Get global subprocess manager statistics."""
    return _global_manager.get_stats()


def clear_subprocess_cache(pattern: Optional[str] = None):
    """Clear global subprocess cache."""
    _global_manager.clear_cache(pattern)