"""Civitai API client for fetching creator content."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from models.types import ApiItem
from utilities.logging_utils import safe_log
from utilities.network import request_with_retries

if TYPE_CHECKING:
    from core.display_manager import DisplayManager


class CivitaiClient:
    """Client for interacting with the Civitai API.
    
    Provides methods to fetch creator content from the Civitai platform with
    automatic pagination and retry logic.
    """

    API_BASE = "https://civitai.com/api/v1/images"

    def __init__(
        self,
        api_key: str,
        request_timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_sec: int = 2,
    ) -> None:
        """Initialize Civitai API client.

        Args:
            api_key: Civitai API key for authentication.
            request_timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
            retry_backoff_sec: Backoff time between retries in seconds.
        """
        self.api_key = api_key
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.retry_backoff_sec = retry_backoff_sec
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "CivitaiFetcher/2.0",
        }

    def fetch_creator_items(
        self,
        username: str,
        display_manager: DisplayManager,
        nsfw: bool = True,
    ) -> list[ApiItem]:
        """Fetch all items for a creator from the Civitai API.

        Args:
            username: Creator username
            display_manager: Display manager for progress updates
            nsfw: Whether to include NSFW content

        Returns:
            List of item dictionaries from the API
        """
        all_items: list[ApiItem] = []
        cursor: str | None = None
        request_count = 1

        while True:
            # Params for the request (use concrete simple types)
            params: dict[str, str | int | bool] = {
                "username": username,
                "limit": 100,
                "nsfw": nsfw,
            }

            if cursor is not None:
                params["cursor"] = cursor
            else:
                params["page"] = request_count

            # Make request with retry logic
            cursor_val = cursor if cursor is not None else "0"
            safe_log(
                f"Api Request ({username}): Page {request_count} | Cursor {cursor_val}\n",
                level="DEBUG",
            )

            resp = request_with_retries(
                url=self.API_BASE,
                headers=self.headers,
                params=params,
                stream=False,
                timeout=self.request_timeout,
                max_retries=self.max_retries,
                retry_backoff_sec=self.retry_backoff_sec,
            )

            data = resp.json()
            items_raw = data.get("items", [])
            safe_log(
                f"Api Response ({username}): Page {request_count} | Items {len(items_raw)}\n",
                level="DEBUG",
            )
            items: list[ApiItem] = cast(list[ApiItem], items_raw)

            all_items.extend(items)

            # Update display manager
            display_manager.update_api_progress(request_count, len(all_items))

            # Check for next page
            meta = data.get("metadata", {})
            next_cursor = meta.get("nextCursor")
            next_page = meta.get("nextPage")

            # Stop if no items were returned (prevents infinite loop)
            if len(items) == 0:
                break

            if next_cursor is not None:
                cursor = next_cursor
                request_count += 1
                continue

            if next_page:
                cursor = None
                request_count += 1
                continue

            break

        return all_items
