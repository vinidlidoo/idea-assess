"""Retry logic with exponential backoff for transient failures."""

import asyncio
import time
from typing import TypeVar, Callable
from collections.abc import Awaitable
from functools import wraps

# SDK doesn't export these error types, so define them
has_sdk_errors = False

class RateLimitError(Exception):
    """Placeholder for SDK RateLimitError."""
    def __init__(self, message: str = "", retry_after: float | None = None):
        super().__init__(message)
        self.retry_after: float | None = retry_after

class SDKTimeoutError(Exception):
    """Placeholder for SDK TimeoutError."""
    pass

class APIError(Exception):
    """Placeholder for SDK APIError."""
    pass


T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
        """
        self.max_retries: int = max_retries
        self.initial_delay: float = initial_delay
        self.max_delay: float = max_delay
        self.exponential_base: float = exponential_base
        self.jitter: bool = jitter
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.
        
        Args:
            attempt: Attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            import random
            # Add up to 25% jitter
            delay *= (0.75 + random.random() * 0.5)
        
        return delay


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args: object,
    config: RetryConfig | None = None,
    **kwargs: object
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for func
        config: Retry configuration (uses defaults if None)
        **kwargs: Keyword arguments for func
        
    Returns:
        Result from successful function call
        
    Raises:
        Last exception if all retries exhausted
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
            
        except RateLimitError as e:
            last_exception = e
            if attempt == config.max_retries:
                raise
            
            # Use server-provided retry_after if available
            if hasattr(e, 'retry_after') and e.retry_after:
                delay = e.retry_after
            else:
                delay = config.get_delay(attempt)
            
            print(f"⏳ Rate limited. Waiting {delay:.1f}s before retry {attempt + 1}/{config.max_retries}...")
            await asyncio.sleep(delay)
            
        except (SDKTimeoutError, asyncio.TimeoutError) as e:
            last_exception = e
            if attempt == config.max_retries:
                raise
            
            delay = config.get_delay(attempt)
            print(f"⏱️  Timeout. Waiting {delay:.1f}s before retry {attempt + 1}/{config.max_retries}...")
            await asyncio.sleep(delay)
            
        except APIError as e:
            last_exception = e
            # Check if it's a transient error
            error_message = str(e).lower()
            if any(phrase in error_message for phrase in ['temporary', 'transient', '503', '502', 'overloaded']):
                if attempt == config.max_retries:
                    raise
                
                delay = config.get_delay(attempt)
                print(f"⚠️  API error. Waiting {delay:.1f}s before retry {attempt + 1}/{config.max_retries}...")
                await asyncio.sleep(delay)
            else:
                # Non-transient error, don't retry
                raise
                
        except Exception:
            # For other exceptions, don't retry unless explicitly transient
            raise
    
    # This shouldn't be reached, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry logic error: no exception but no success")


def retry_on_transient_errors(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0
):
    """
    Decorator for adding retry logic to async functions.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        
    Usage:
        @retry_on_transient_errors(max_retries=5)
        async def my_api_call():
            ...
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay
    )
    
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> T:
            return await retry_with_backoff(func, *args, config=config, **kwargs)
        return wrapper
    
    return decorator


# Synchronous version for non-async functions
def retry_sync_with_backoff(
    func: Callable[..., T],
    *args: object,
    config: RetryConfig | None = None,
    **kwargs: object
) -> T:
    """
    Retry a synchronous function with exponential backoff.
    
    Args:
        func: Function to retry
        *args: Positional arguments for func
        config: Retry configuration (uses defaults if None)
        **kwargs: Keyword arguments for func
        
    Returns:
        Result from successful function call
        
    Raises:
        Last exception if all retries exhausted
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return func(*args, **kwargs)
            
        except Exception as e:
            last_exception = e
            if attempt == config.max_retries:
                raise
            
            delay = config.get_delay(attempt)
            print(f"⚠️  Error: {e}. Waiting {delay:.1f}s before retry {attempt + 1}/{config.max_retries}...")
            time.sleep(delay)
    
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry logic error: no exception but no success")