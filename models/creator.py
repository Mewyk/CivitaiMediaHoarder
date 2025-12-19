"""Creator data model and related functionality."""

from __future__ import annotations

from dataclasses import dataclass

from models.types import ApiItem


@dataclass
class Creator:
    """Represents a Civitai creator and their content."""

    username: str
    items: list[ApiItem]

    def __post_init__(self) -> None:
        """Validate creator data."""
        if not self.username or not self.username.strip():
            raise ValueError("Creator username cannot be empty")
        self.username = self.username.strip()

    @property
    def total_items(self) -> int:
        """Total number of items for this creator."""
        return len(self.items)

    def get_urls(self) -> list[str]:
        """Get all media URLs from items."""
        urls: list[str] = []
        for item in self.items:
            url = item.get("url")
            if url:
                urls.append(str(url))
        return urls
