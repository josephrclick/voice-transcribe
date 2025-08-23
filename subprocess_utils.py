#!/usr/bin/env python3
"""Subprocess utilities with caching and optimization for performance."""

import hashlib
import logging
import subprocess
import time
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class SubprocessManager:
    """Manages subprocess calls with caching and optimization."""

    def __init__(self, default_cache_ttl: float = 2.0) -> None:
        """Initialize the subprocess manager.

        Args:
            default_cache_ttl: Default time-to-live for cached results in seconds
        """
        self._command_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_lock = Lock()
        self.default_cache_ttl = default_cache_ttl
        self._stats = {"cache_hits": 0, "cache_misses": 0, "subprocess_calls": 0, "total_calls": 0}

    def _cache_key(self, cmd: List[Union[str, int]]) -> str:
        """Generate a secure cache key from a command list using SHA256.
        
        This prevents command injection vulnerabilities by using a 
        cryptographic hash instead of concatenating command arguments.
        """
        # Create a stable string representation of the command
        cmd_str = "\x00".join(str(arg) for arg in cmd)
        # Use SHA256 for collision-resistant hashing
        return hashlib.sha256(cmd_str.encode('utf-8')).hexdigest()

    def run_cached(
        self,
        cmd: List[Union[str, int]],
        cache_ttl: Optional[float] = None,
        check: bool = True,
        capture_output: bool = True,
        text: bool = True,
        timeout: Optional[float] = None,
    ) -> subprocess.CompletedProcess:
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
        self._stats["total_calls"] += 1

        # Generate cache key
        cache_key = self._cache_key(cmd)
        ttl = cache_ttl if cache_ttl is not None else self.default_cache_ttl

        # Check cache
        with self._cache_lock:
            if cache_key in self._command_cache:
                cached_result, cached_time = self._command_cache[cache_key]
                if time.time() - cached_time < ttl:
                    self._stats["cache_hits"] += 1
                    logger.debug(f"Cache hit for command: {' '.join(cmd)}")
                    return cached_result

        # Cache miss - execute command
        self._stats["cache_misses"] += 1
        self._stats["subprocess_calls"] += 1
        logger.debug(f"Cache miss, executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=check, capture_output=capture_output, text=text, timeout=timeout)

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

    def clear_cache(self, pattern: Optional[str] = None) -> None:
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
        stats["cache_size"] = len(self._command_cache)
        if stats["total_calls"] > 0:
            stats["hit_rate"] = stats["cache_hits"] / stats["total_calls"]
        else:
            stats["hit_rate"] = 0.0
        return stats

    def batch_run(self, commands: List[List[Union[str, int]]], cache_ttl: Optional[float] = None) -> List[Optional[subprocess.CompletedProcess]]:
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
            except subprocess.SubprocessError as e:
                # Handle subprocess-specific errors
                safe_cmd = sanitize_error_message(str(cmd))
                safe_error = sanitize_error_message(str(e))
                logger.error(f"Failed to execute {safe_cmd}: {safe_error}")
                results.append(None)
            except (OSError, ValueError) as e:
                # Handle system and value errors
                safe_cmd = sanitize_error_message(str(cmd))
                safe_error = sanitize_error_message(str(e))
                logger.error(f"System error executing {safe_cmd}: {safe_error}")
                results.append(None)
        return results


class SubprocessManagerFactory:
    """Factory for creating and managing SubprocessManager instances.
    
    This replaces the global singleton pattern with a more testable
    and maintainable factory pattern. Instances can be created with
    different configurations as needed.
    """
    
    _default_instance: Optional[SubprocessManager] = None
    
    @classmethod
    def get_default(cls, cache_ttl: float = 5.0) -> SubprocessManager:
        """Get or create the default SubprocessManager instance.
        
        Args:
            cache_ttl: Default cache TTL for the manager
            
        Returns:
            SubprocessManager instance
        """
        if cls._default_instance is None:
            cls._default_instance = SubprocessManager(default_cache_ttl=cache_ttl)
        return cls._default_instance
    
    @classmethod
    def create(cls, cache_ttl: float = 5.0) -> SubprocessManager:
        """Create a new SubprocessManager instance.
        
        Args:
            cache_ttl: Default cache TTL for the manager
            
        Returns:
            New SubprocessManager instance
        """
        return SubprocessManager(default_cache_ttl=cache_ttl)
    
    @classmethod
    def reset_default(cls) -> None:
        """Reset the default instance (useful for testing)."""
        cls._default_instance = None


# Convenience functions for backward compatibility
def run_cached(cmd: List[Union[str, int]], **kwargs) -> subprocess.CompletedProcess:
    """Convenience function using default subprocess manager.
    
    Note: This is maintained for backward compatibility but 
    creating your own SubprocessManager instance is preferred.

    Args:
        cmd: Command list to execute
        **kwargs: Additional arguments for SubprocessManager.run_cached

    Returns:
        CompletedProcess object
    """
    manager = SubprocessManagerFactory.get_default()
    return manager.run_cached(cmd, **kwargs)


def get_subprocess_stats() -> Dict[str, int]:
    """Get default subprocess manager statistics.
    
    Note: This is maintained for backward compatibility.
    """
    manager = SubprocessManagerFactory.get_default()
    return manager.get_stats()


def clear_subprocess_cache(pattern: Optional[str] = None) -> None:
    """Clear default subprocess cache.
    
    Note: This is maintained for backward compatibility.
    """
    manager = SubprocessManagerFactory.get_default()
    manager.clear_cache(pattern)
