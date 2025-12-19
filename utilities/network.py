"""Network utilities for HTTP requests with retry logic."""

from __future__ import annotations

import time
from typing import cast

import requests


class UserNotFoundError(Exception):
    """Raised when the API returns a 'User not found' error.

    This is a local copy to avoid circular imports.
    The canonical version is in core.exceptions.
    """

    def __init__(self, username: str = "unknown") -> None:
        """Initialize UserNotFoundError.

        Args:
            username: The username that was not found.
        """
        self.username = username
        super().__init__(f"User not found: {username}")


def request_with_retries(
    url: str,
    headers: dict[str, str],
    params: dict[str, str | int | bool] | None = None,
    stream: bool = False,
    timeout: int | tuple[int, int | None] = 30,
    max_retries: int = 3,
    retry_backoff_sec: int = 2,
) -> requests.Response:
    """Make an HTTP GET request with automatic retry logic.

    Args:
        url: The URL to request.
        headers: HTTP headers to include.
        params: Query parameters.
        stream: Whether to stream the response.
        timeout: Request timeout (single value or tuple).
        max_retries: Maximum number of retry attempts.
        retry_backoff_sec: Base backoff time between retries.

    Returns:
        requests.Response object.

    Raises:
        UserNotFoundError: If the API returns a "User not found" error.
        Exception: If all retry attempts fail.
    """
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(
                url,
                headers=headers,
                params=params,
                stream=stream,
                timeout=timeout,
            )

            # Check for "User not found" error in JSON response before raising
            # This can appear in error responses (e.g., 500 status codes)
            # This is a special case that should not be retried
            try:
                data: object = resp.json()
                if isinstance(data, dict):
                    data_dict = cast(dict[str, object], data)
                    if data_dict.get("error") == "User not found":
                        # Extract username from URL if possible
                        username = "unknown"
                        if params and "username" in params:
                            username = str(params["username"])
                        raise UserNotFoundError(username)
            except (ValueError, KeyError):
                # Not JSON or missing expected keys, proceed normally
                pass

            resp.raise_for_status()
            return resp
        except UserNotFoundError:
            # Don't retry for user not found errors, propagate immediately
            raise
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                backoff_time = retry_backoff_sec * attempt
                time.sleep(backoff_time)
            else:
                raise

    # This should never be reached, but helps type checker
    raise last_exc if last_exc else Exception("Request failed")
