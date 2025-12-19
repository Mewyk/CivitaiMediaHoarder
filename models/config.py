"""Configuration data models."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import cast

from models.types import LockPolicy, DEFAULT_MEMORY_THRESHOLD_BYTES


@dataclass
class MediaTypeConfig:
    """Configuration for media type preferences."""

    images: bool
    videos: bool
    other: bool

    @classmethod
    def from_dict(cls, data: dict[str, bool]) -> MediaTypeConfig:
        """Create MediaTypeConfig from dictionary."""
        return cls(
            images=data.get("images", False),
            videos=data.get("videos", False),
            other=data.get("other", False)
        )

    def to_dict(self) -> dict[str, bool]:
        """Convert to dictionary."""
        return {
            "images": self.images,
            "videos": self.videos,
            "other": self.other
        }

    def merge_with(self, override: dict[str, bool]) -> MediaTypeConfig:
        """Create new MediaTypeConfig with overrides applied."""
        return MediaTypeConfig(
            images=override.get("images", self.images),
            videos=override.get("videos", self.videos),
            other=override.get("other", self.other)
        )


@dataclass
class CreatorConfig:
    """Configuration for a single creator."""

    username: str
    media_types: MediaTypeConfig | None = None

    @classmethod
    def from_value(cls, value: str | dict[str, object]) -> CreatorConfig:
        """Create CreatorConfig from either string or dict format.

        Args:
            value: Either a username string or dict with username and media_types.

        Returns:
            CreatorConfig instance.

        Raises:
            ValueError: If value format is invalid.
        """
        if isinstance(value, str):
            if not value or not value.strip():
                raise ValueError("Creator username cannot be empty")
            return cls(username=value.strip(), media_types=None)
        else:
            # Must be dict based on Union type
            username = value.get("username", "")
            if not username or not isinstance(username, str) or not username.strip():
                raise ValueError(
                    "Creator entry missing 'username' field or username is empty"
                )

            media_types_dict = value.get("media_types", {})
            if not isinstance(media_types_dict, dict):
                media_types_dict = {}
            # Narrow type for static analysis
            media_types_dict = cast(dict[str, object], media_types_dict)
            # Cast to proper type for MediaTypeConfig
            media_types_data: dict[str, bool] = {}
            for key in ["images", "videos", "other"]:
                val = media_types_dict.get(key)
                if isinstance(val, bool):
                    media_types_data[key] = val
            media_types = (
                MediaTypeConfig.from_dict(media_types_data)
                if media_types_data
                else None
            )

            return cls(username=username.strip(), media_types=media_types)

    def to_value(self) -> str | dict[str, object]:
        """Convert to either string or dict format.

        Returns string if using default media types, dict otherwise.
        """
        # If no custom media types, return just username
        if self.media_types is None:
            return self.username
        else:
            return {
                "username": self.username,
                "media_types": self.media_types.to_dict()
            }


@dataclass
class AppConfig:
    """Main application configuration."""

    api_key: str
    default_output: str
    nsfw: bool
    rate_limit: bool
    request_timeout: int
    download_timeout: int
    max_retries: int
    retry_backoff_sec: int
    image_extensions: list[str]
    video_extensions: list[str]
    default_media_types: MediaTypeConfig
    creators: list[CreatorConfig]
    # Optional downloader configuration
    memory_threshold_bytes: int = DEFAULT_MEMORY_THRESHOLD_BYTES
    download_lock_policy: LockPolicy = LockPolicy.BEST_EFFORT

    def __init__(
        self,
        api_key: str,
        default_output: str,
        nsfw: bool,
        rate_limit: bool,
        request_timeout: int,
        download_timeout: int,
        max_retries: int,
        retry_backoff_sec: int,
        image_extensions: list[str],
        video_extensions: list[str],
        default_media_types: MediaTypeConfig,
        creators: list[CreatorConfig],
        memory_threshold_bytes: int = DEFAULT_MEMORY_THRESHOLD_BYTES,
        download_lock_policy: LockPolicy = LockPolicy.BEST_EFFORT,
    ) -> None:
        """Initialize AppConfig with all parameters."""
        self.api_key = api_key
        self.default_output = default_output
        self.nsfw = nsfw
        self.rate_limit = rate_limit
        self.request_timeout = request_timeout
        self.download_timeout = download_timeout
        self.max_retries = max_retries
        self.retry_backoff_sec = retry_backoff_sec
        self.image_extensions = image_extensions
        self.video_extensions = video_extensions
        self.default_media_types = default_media_types
        self.creators = creators
        self.memory_threshold_bytes = memory_threshold_bytes
        self.download_lock_policy = download_lock_policy

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
        creators: list[CreatorConfig] | None = None,
    ) -> AppConfig:
        """Create AppConfig from dictionary (loaded from JSON).

        Args:
            data: Configuration dictionary from JSON.
            creators: Optional pre-loaded creators list. If provided,
                     the 'creators' key in data is ignored.

        Returns:
            AppConfig instance.
        """
        # Parse creators if not provided externally
        if creators is None:
            creator_list: list[CreatorConfig] = []
            invalid_entries: list[str] = []

            creators_raw = cast(list[object], data.get("creators", []))
            for idx, creator_value in enumerate(creators_raw, 1):
                try:
                    creator_list.append(
                        CreatorConfig.from_value(
                            cast(str | dict[str, object], creator_value)
                        )
                    )
                except ValueError as e:
                    entry_str = str(creator_value)
                    entry_repr = (
                        entry_str if len(entry_str) < 50 else entry_str[:47] + "..."
                    )
                    invalid_entries.append(f"Entry #{idx}: {e} ({entry_repr})")
                    continue

            if invalid_entries:
                print(
                    f"\nWarning: Skipped {len(invalid_entries)} invalid creator(s) "
                    "in configuration:",
                    file=sys.stderr,
                )
                for entry_error in invalid_entries:
                    print(f"  - {entry_error}", file=sys.stderr)
                print("", file=sys.stderr)
        else:
            creator_list = creators

        # Cast and validate top-level fields
        api_key = cast(str, data["api_key"])
        default_output = cast(str, data["default_output"])
        nsfw = cast(bool, data["nsfw"])
        rate_limit = cast(bool, data["rate_limit"])
        request_timeout = int(cast(int, data["request_timeout"]))
        download_timeout = int(cast(int, data["download_timeout"]))
        max_retries = int(cast(int, data["max_retries"]))
        retry_backoff_sec = int(cast(int, data["retry_backoff_sec"]))
        image_extensions = cast(list[str], data["image_extensions"])
        video_extensions = cast(list[str], data["video_extensions"])
        default_media_types = MediaTypeConfig.from_dict(
            cast(dict[str, bool], data["default_media_types"])
        )

        memory_threshold_bytes = int(
            cast(int, data.get("memory_threshold_bytes", DEFAULT_MEMORY_THRESHOLD_BYTES))
        )
        lock_policy_str = cast(
            str, data.get("download_lock_policy", LockPolicy.BEST_EFFORT.value)
        )
        try:
            download_lock_policy = LockPolicy(lock_policy_str)
        except ValueError:
            download_lock_policy = LockPolicy.BEST_EFFORT

        return cls(
            api_key=api_key,
            default_output=default_output,
            nsfw=nsfw,
            rate_limit=rate_limit,
            request_timeout=request_timeout,
            download_timeout=download_timeout,
            max_retries=max_retries,
            retry_backoff_sec=retry_backoff_sec,
            image_extensions=image_extensions,
            video_extensions=video_extensions,
            default_media_types=default_media_types,
            creators=creator_list,
            memory_threshold_bytes=memory_threshold_bytes,
            download_lock_policy=download_lock_policy,
        )

    def to_dict(self, include_creators: bool = False) -> dict[str, object]:
        """Convert to dictionary for JSON serialization.

        Args:
            include_creators: If True, include creators in output.
                            If False, omit creators (for separate file).

        Returns:
            Configuration dictionary.
        """
        result: dict[str, object] = {
            "api_key": self.api_key,
            "default_output": self.default_output,
            "nsfw": self.nsfw,
            "rate_limit": self.rate_limit,
            "request_timeout": self.request_timeout,
            "download_timeout": self.download_timeout,
            "max_retries": self.max_retries,
            "retry_backoff_sec": self.retry_backoff_sec,
            "image_extensions": self.image_extensions,
            "video_extensions": self.video_extensions,
            "default_media_types": self.default_media_types.to_dict(),
            "memory_threshold_bytes": self.memory_threshold_bytes,
            "download_lock_policy": self.download_lock_policy.value,
        }
        if include_creators:
            result["creators"] = [c.to_value() for c in self.creators]
        return result
