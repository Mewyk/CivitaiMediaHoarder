"""Centralized extension correction tracking.

This module provides a single source of truth for tracking file extension
corrections made during download, verification, and repair operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class ExtensionCorrection:
    """Represents a single extension correction."""

    file_path: str
    old_extension: str
    new_extension: str

    @property
    def filename(self) -> str:
        """Get just the filename from the path."""
        return Path(self.file_path).name

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            "filename": self.filename,
            "full_path": self.file_path,
            "old_extension": self.old_extension,
            "new_extension": self.new_extension,
        }


class ExtensionCorrectionTracker:
    """Centralized tracker for extension corrections.

    Provides thread-safe tracking of extension corrections across all
    components. Use a single instance shared between FileManager,
    MediaDownloader, and VideoValidator.
    """

    def __init__(self) -> None:
        """Initialize the tracker."""
        self._corrections: dict[str, tuple[str, str]] = {}

    def record(
        self,
        file_path: str | Path,
        old_extension: str,
        new_extension: str,
    ) -> None:
        """Record an extension correction.

        Args:
            file_path: Path to the file that was corrected.
            old_extension: Original extension (e.g., '.mp4').
            new_extension: Corrected extension (e.g., '.webm').
        """
        path_str = str(file_path)
        self._corrections[path_str] = (old_extension, new_extension)

    # Alias for record method
    record_correction = record

    def get_all(self) -> dict[str, tuple[str, str]]:
        """Get all recorded corrections.

        Returns:
            Dictionary mapping file paths to (old_ext, new_ext) tuples.
        """
        return self._corrections.copy()

    def get_all_corrections(self) -> dict[str, tuple[str, str]]:
        """Get all recorded corrections.

        Returns:
            Dictionary mapping file paths to (old_ext, new_ext) tuples.
        """
        return self.get_all()

    def get_correction(self, file_path: str | Path) -> tuple[str, str] | None:
        """Get correction for a specific file.

        Args:
            file_path: Path to the file.

        Returns:
            Tuple of (old_ext, new_ext) or None if not corrected.
        """
        return self._corrections.get(str(file_path))

    def merge(self, other: dict[str, tuple[str, str]]) -> None:
        """Merge corrections from another source.

        Args:
            other: Dictionary of corrections to merge.
        """
        self._corrections.update(other)

    def clear(self) -> None:
        """Clear all recorded corrections."""
        self._corrections.clear()

    def __len__(self) -> int:
        """Return number of corrections."""
        return len(self._corrections)

    def __bool__(self) -> bool:
        """Return True if any corrections recorded."""
        return bool(self._corrections)

    def __iter__(self) -> Iterator[ExtensionCorrection]:
        """Iterate over corrections as ExtensionCorrection objects."""
        for file_path, (old_ext, new_ext) in self._corrections.items():
            yield ExtensionCorrection(
                file_path=file_path,
                old_extension=old_ext,
                new_extension=new_ext,
            )

    def get_summary(self) -> dict[str, int]:
        """Get summary of correction types.

        Returns:
            Dictionary mapping "old_ext → new_ext" to count.
        """
        summary: dict[str, int] = {}
        for old_ext, new_ext in self._corrections.values():
            key = f"{old_ext} → {new_ext}"
            summary[key] = summary.get(key, 0) + 1
        return summary

    def to_list(self) -> list[dict[str, str]]:
        """Convert all corrections to a list of dictionaries.

        Suitable for JSON serialization in reports.

        Returns:
            List of correction dictionaries.
        """
        return [correction.to_dict() for correction in self]


# Global singleton for shared tracking across components
_global_tracker: ExtensionCorrectionTracker | None = None


def get_correction_tracker() -> ExtensionCorrectionTracker:
    """Get or create the global extension correction tracker.

    Returns:
        The global ExtensionCorrectionTracker instance.
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ExtensionCorrectionTracker()
    return _global_tracker


def get_extension_tracker() -> ExtensionCorrectionTracker:
    """Get or create the global ExtensionCorrectionTracker instance.

    Returns:
        The global ExtensionCorrectionTracker instance.
    """
    return get_correction_tracker()


def reset_correction_tracker() -> None:
    """Reset the global tracker. Useful for testing."""
    global _global_tracker
    if _global_tracker is not None:
        _global_tracker.clear()


class ExtensionTracker(ExtensionCorrectionTracker):
    """Extension correction tracker.
    
    This class tracks file extension corrections during downloads.
    """
    pass
