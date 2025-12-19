"""Centralized logging utilities for safe exception handling.

This module provides a unified approach to exception handling that:
1. Logs errors to debug log when debug mode is enabled
2. Never crashes the application due to logging failures
3. Provides context about where errors occurred
"""

from __future__ import annotations

import functools
from typing import Callable, ParamSpec, TypeVar

from utilities.debug_logger import buffer as debug_buffer, get_logger


P = ParamSpec("P")
R = TypeVar("R")


def log_exception(
    exception: BaseException,
    context: str = "",
    level: str = "DEBUG",
) -> None:
    """Log an exception with context in a safe manner.

    This function never raises exceptions. It attempts to log the error
    to the debug buffer if available, otherwise silently ignores.

    Args:
        exception: The exception that was caught.
        context: Description of what was being attempted when error occurred.
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    if get_logger() is None:
        return

    try:
        exc_name = type(exception).__name__
        exc_msg = str(exception) or "(no message)"
        if context:
            debug_buffer(f"{context}: {exc_name}: {exc_msg}\n", level=level)
        else:
            debug_buffer(f"{exc_name}: {exc_msg}\n", level=level)
    except Exception:
        # Last resort: we cannot let logging crash the app
        pass


def safe_log(message: str, level: str = "DEBUG") -> None:
    """Log a message in a safe manner.

    This function never raises exceptions. It attempts to log the message
    to the debug buffer if available, otherwise silently ignores.

    Args:
        message: The message to log.
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    if get_logger() is None:
        return

    try:
        debug_buffer(message, level=level)
    except Exception:
        pass


def safe_operation(
    context: str,
    default: R | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R | None]]:
    """Decorator that catches exceptions and logs them safely.

    Use this for non-critical operations where failures should be logged
    but not propagate to crash the application.

    Args:
        context: Description of the operation for logging.
        default: Value to return if an exception occurs.

    Returns:
        Decorator function.

    Example:
        @safe_operation("cache update", default=False)
        def update_cache() -> bool:
            # ... implementation
            return True
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R | None]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_exception(e, context)
                return default
        return wrapper
    return decorator


def suppress_for_logging(func: Callable[P, None]) -> Callable[P, None]:
    """Decorator that suppresses all exceptions for logging-only functions.

    Use this for pure logging operations where we never want exceptions
    to propagate.

    Args:
        func: The function to wrap.

    Returns:
        Wrapped function that never raises.

    Example:
        @suppress_for_logging
        def log_download_stats(stats: dict) -> None:
            debug_buffer(f"Stats: {stats}\n", level="INFO")
    """
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            func(*args, **kwargs)
        except Exception:
            pass
    return wrapper
