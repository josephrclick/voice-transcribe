## Summary

This PR implements solid performance optimizations and refactoring foundations. The code quality is generally good, with proper error handling and testing. However, there are several areas that need attention regarding security, testing, and Python best practices.

## Strengths ✅

1.  **Performance Improvements**: Excellent implementation of subprocess caching with TTL management and cache hit tracking
2.  **Lazy Loading**: Well-implemented lazy loading for the enhancement module that reduces startup time
3.  **Builder Pattern**: Good use of builder patterns to prepare for reducing cyclomatic complexity
4.  **Test Foundation**: Characterization tests provide a good baseline for refactoring

## Critical Security Issues 🔴

### 1\. **Command Injection Vulnerability in SubprocessManager** (subprocess_utils.py:33-34)

```python
def _cache_key(self, cmd: list) -> str:
    """Generate a cache key from a command list."""
    return '|'.join(str(arg) for arg in cmd)
```

**Issue**: Using pipe character as separator could cause cache key collisions if command arguments contain pipes.  
**Recommendation**: Use a safer separator or hash the command:

```python
import hashlib
def _cache_key(self, cmd: list) -> str:
    return hashlib.sha256(json.dumps(cmd).encode()).hexdigest()
```

### 2\. **Potential API Key Exposure in Logs** (model_config.py)

Multiple locations log exception details that could potentially expose API keys:

- Line 362: `logger.warning(f"Parameter error with {attempt_model}, attempting migration: {e}")`
- Line 386: `logger.warning(f"Model {attempt_model} failed: {e}")`
- Line 391: `logger.error(f"All fallback models failed. Last error: {last_error}")`

**Recommendation**: Sanitize error messages before logging:

```python
def _sanitize_error(self, error: Exception) -> str:
    """Remove sensitive information from error messages"""
    error_str = str(error)
    # Remove potential API keys
    error_str = re.sub(r'(api[_-]?key|authorization|bearer|sk-)[^\s]*', '[REDACTED]', error_str, flags=re.IGNORECASE)
    return error_str
```

## Python Best Practices Issues 🟡

### 1\. **Global State in subprocess_utils.py** (Lines 152-176)

Using a global singleton instance `_global_manager` is an anti-pattern that makes testing harder.  
**Recommendation**: Consider dependency injection or factory pattern instead.

### 2\. **Broad Exception Handling** (Multiple locations)

- subprocess_utils.py:146: `except Exception as e:` - Too broad
- enhancement_builder.py:62: `except Exception as e:` - Too broad

**Recommendation**: Catch specific exceptions:

```python
except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
```

### 3\. **Missing Type Hints**

Several methods lack comprehensive type hints:

- `SubprocessManager.batch_run()` return type should be `List[Optional[subprocess.CompletedProcess]]`
- Builder pattern methods could benefit from return type hints
