"""Unified result and summary objects for all operations.

This module provides data structures that represent the results of various
operations (update, verify, repair). These are immutable data classes that
can be passed through the application and formatted for display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from models.types import InvalidVideoEntry

if TYPE_CHECKING:
    from core.display_manager import DisplayManager
    from core.repair_manager import RepairManager


class OperationType(Enum):
    """Enumeration of operation types."""

    UPDATE = "update"
    VERIFY = "verify"
    REPAIR = "repair"


@dataclass
class OperationSummary:
    """
    Base class for all operation summaries.
    
    Represents the high-level outcome of an operation with success/failure metrics
    and common fields. Operation-specific summaries extend this class.
    """
    
    operation_type: OperationType
    successful: int
    failed: int
    total: int
    warnings: list[str] = field(default_factory=lambda: [])
    
    def success_rate(self) -> float:
        """
        Calculate the success rate of the operation.
        
        Returns:
            float: Percentage of successful items (0.0 to 1.0)
        """
        return self.successful / self.total if self.total > 0 else 0.0
    
    def has_failures(self) -> bool:
        """
        Check if the operation had any failures.
        
        Returns:
            bool: True if any operations failed
        """
        return self.failed > 0
    
    def has_warnings(self) -> bool:
        """
        Check if there are any warnings.
        
        Returns:
            bool: True if warnings list is not empty
        """
        return len(self.warnings) > 0


@dataclass
class UpdateOperationSummary(OperationSummary):
    """
    Results from an update operation.
    
    Tracks creators processed, API data fetched, files downloaded,
    extension corrections, and any failures or deletions.
    """
    
    api_items_total: int = 0
    files_downloaded: int = 0
    files_needed: int = 0
    images_downloaded: int = 0
    videos_downloaded: int = 0
    images_needed: int = 0
    videos_needed: int = 0
    extension_corrections: dict[str, tuple[str, str]] = field(default_factory=lambda: {})
    deleted_creators: list[str] = field(default_factory=lambda: [])
    failed_creators: list[tuple[str, str]] = field(default_factory=lambda: [])
    # Downloaded extensions counts collected from downloader (extension -> count)
    downloaded_extensions: dict[str, int] = field(default_factory=lambda: {})
    
    def __post_init__(self) -> None:
        """Validate that operation_type is set correctly."""
        self.operation_type = OperationType.UPDATE
    
    def correction_count(self) -> int:
        """
        Get the total number of extension corrections applied.
        
        Returns:
            int: Number of files with corrected extensions
        """
        return len(self.extension_corrections)
    
    def deleted_creator_count(self) -> int:
        """
        Get the count of creators that were not found and removed.
        
        Returns:
            int: Number of deleted/purged creators
        """
        return len(self.deleted_creators)
    
    def get_correction_types(self) -> dict[str, int]:
        """
        Get correction types grouped by transformation (e.g., jpg->png).
        
        Returns:
            Dict mapping "OldExt->NewExt" to count of occurrences
        """
        corrections_by_type: dict[str, int] = {}
        for _, (old_ext, new_ext) in self.extension_corrections.items():
            key = f"{old_ext} → {new_ext}"
            corrections_by_type[key] = corrections_by_type.get(key, 0) + 1
        return corrections_by_type
    
    def get_media_types_downloaded(self) -> list[str]:
        """
        Get list of media types that were downloaded (based on corrections).

        Returns:
            List of media type names (e.g., ['Png', 'Mp4'])
        """
        types: list[str] = []
        # Prefer explicit downloaded_extensions if available
        if self.downloaded_extensions:
            for ext in sorted(self.downloaded_extensions.keys()):
                # Format extension ('.mp4' -> 'MP4')
                types.append(ext.lstrip('.').upper())
            return types

        # Fallback: infer from extension_corrections new extensions
        seen: set[str] = set()
        for _, (_old, new_ext) in self.extension_corrections.items():
            if new_ext and new_ext not in seen:
                seen.add(new_ext)
                types.append(new_ext.lstrip('.').upper())

        return types


@dataclass
class VerifyOperationSummary(OperationSummary):
    """
    Results from a verify operation.

    Tracks verification of both images and videos, including counts of
    invalid files, incorrect extensions, and extension corrections applied.
    """

    creators_processed: int = 0
    creators_failed: int = 0
    images_total: int = 0
    images_invalid: int = 0
    images_incorrect: int = 0
    videos_total: int = 0
    videos_invalid: int = 0
    videos_incorrect: int = 0
    extension_corrections: dict[str, tuple[str, str]] = field(default_factory=lambda: {})
    # References for follow-up operations (repair, reports)
    # These are optional and populated by handlers when needed
    display_manager: DisplayManager | None = field(default=None, repr=False)
    failed_creators_list: list[tuple[str, str]] = field(default_factory=lambda: [], repr=False)
    invalids: dict[str, list[InvalidVideoEntry]] = field(default_factory=lambda: {}, repr=False)
    repair_manager: RepairManager | None = field(default=None, repr=False)
    
    def __post_init__(self) -> None:
        """Validate that operation_type is set correctly."""
        self.operation_type = OperationType.VERIFY
    
    def correction_count(self) -> int:
        """
        Get the total number of extension corrections applied.
        
        Returns:
            int: Number of files with corrected extensions
        """
        return len(self.extension_corrections)
    
    def total_files_checked(self) -> int:
        """
        Get the total number of files checked (images + videos).
        
        Returns:
            int: Total files checked
        """
        return self.images_total + self.videos_total
    
    def total_issues_found(self) -> int:
        """
        Get the total number of issues found (invalid + incorrect extensions).
        
        Returns:
            int: Total issues across all files
        """
        return (
            self.images_invalid + self.images_incorrect +
            self.videos_invalid + self.videos_incorrect
        )
    
    def has_verification_issues(self) -> bool:
        """
        Check if there are any verification issues found.
        
        Returns:
            bool: True if any invalid or incorrect files found
        """
        return self.total_issues_found() > 0


@dataclass
class RepairOperationSummary(OperationSummary):
    """
    Results from a repair operation.
    
    Tracks files removed, files redownloaded, and per-creator statistics
    for video repair operations.
    """
    
    files_removed: int = 0
    files_redownloaded: int = 0
    per_creator_stats: dict[str, tuple[int, int]] = field(default_factory=lambda: {})
    invalid_videos_json_kept: bool = False
    
    def __post_init__(self) -> None:
        """Validate that operation_type is set correctly."""
        self.operation_type = OperationType.REPAIR
    
    def get_creator_stats(self, creator_name: str) -> tuple[int, int]:
        """
        Get repair statistics for a specific creator.
        
        Args:
            creator_name: Name of the creator to query
            
        Returns:
            Tuple of (files_removed, files_redownloaded) for creator
        """
        return self.per_creator_stats.get(creator_name, (0, 0))
    
    def total_creators_repaired(self) -> int:
        """
        Get the number of creators that had repairs.
        
        Returns:
            int: Number of creators with statistics
        """
        return len(self.per_creator_stats)
    
    def all_repairs_successful(self) -> bool:
        """
        Check if all repairs were successful.
        
        For a repair to be successful, files_redownloaded must match
        files_removed for each creator.
        
        Returns:
            bool: True if all repairs succeeded
        """
        if not self.per_creator_stats:
            return True
        
        for removed, redownloaded in self.per_creator_stats.values():
            if removed != redownloaded:
                return False
        
        return True
