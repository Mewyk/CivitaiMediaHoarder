"""Core type definitions for the Civitai Media Hoarder.

This module contains all shared type definitions, constants, and TypedDicts
used throughout the application.
"""

from __future__ import annotations

from enum import Enum
from typing import TypedDict


class LockPolicy(str, Enum):
    """Lock policy for file downloads."""

    BEST_EFFORT = "best_effort"
    BLOCK = "block"
    FAIL = "fail"


# Constants for Civitai API
CIVITAI_CDN_ID = "xG1nkqKTMzGDvpLrqFT7WA"
CIVITAI_IMAGE_API_BASE = "https://image.civitai.com"
CIVITAI_VIDEO_PARAMS = "original-video=true,quality=100"

# Default memory threshold for buffering downloads (2GB)
DEFAULT_MEMORY_THRESHOLD_BYTES = 2 * 1024 * 1024 * 1024


class ApiItem(TypedDict, total=False):
    """Minimal shape of an API item used in the codebase.

    Only fields that the code relies on are included here. Additional keys
    returned by the API are allowed but not required.
    """

    url: str


class InvalidVideoEntry(TypedDict):
    """Structure for an invalid video entry in reports."""

    filename: str
    path: str
    frames: int
    duration: float


class InvalidVideosReport(TypedDict):
    """Structure for the InvalidVideos.json report."""

    generated_at: str
    creators: dict[str, list[InvalidVideoEntry]]
