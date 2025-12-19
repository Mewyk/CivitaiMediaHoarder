"""File management for metadata and media organization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from models.config import MediaTypeConfig
from models.types import ApiItem
from utilities.extension_handler import ExtensionHandler
from utilities.file_matcher import FileMatcherUtil
from utilities.logging_utils import log_exception
from utilities.media import (
    get_extension_from_url,
    media_type_from_extension,
    safe_filename_from_url,
)


class FileManager:
    """Manages file I/O operations for creator data and media."""

    def __init__(
        self,
        output_folder: str,
        image_extensions: list[str],
        video_extensions: list[str],
    ) -> None:
        """Initialize FileManager.

        Args:
            output_folder: Base output directory path.
            image_extensions: List of valid image file extensions.
            video_extensions: List of valid video file extensions.
        """
        self.output_folder = Path(output_folder)
        self.image_extensions = image_extensions
        self.video_extensions = video_extensions
        self.extension_handler = ExtensionHandler()
        self.file_matcher = FileMatcherUtil()
        self._folder_scan_cache: dict[str, set[str]] = {}

    def get_creator_path(self, creator: str) -> Path:
        """Get the base path for a creator's content."""
        return self.output_folder / creator

    def ensure_creator_directories(self, creator: str) -> None:
        """Create necessary directories for a creator."""
        base_path = self.get_creator_path(creator)
        base_path.mkdir(parents=True, exist_ok=True)

    def load_ignore_list(self, creator: str) -> set[str]:
        """Load the ignore.txt file for a creator if it exists.

        Args:
            creator: Creator username

        Returns:
            Set of filenames to ignore (empty set if ignore.txt doesn't exist)
        """
        ignore_file = self.get_creator_path(creator) / "ignore.txt"

        if not ignore_file.exists():
            return set()

        ignored_files: set[str] = set()

        try:
            with open(ignore_file, "r", encoding="utf-8") as f:
                for line in f:
                    filename = line.strip()
                    if filename:
                        ignored_files.add(filename)
        except (IOError, OSError) as e:
            log_exception(e, f"Failed to load ignore list for {creator}")
            return set()

        return ignored_files

    def count_items_by_type(self, items: list[ApiItem]) -> dict[str, int]:
        """Count items by media type.

        Args:
            items: Items to count

        Returns:
            Dict with counts: {'videos': X, 'images': Y, 'other': Z}
        """
        counts = {"videos": 0, "images": 0, "other": 0}

        for item in items:
            url = item.get("url")
            if not url:
                continue

            ext = get_extension_from_url(url)
            media_type_folder = media_type_from_extension(
                ext, self.image_extensions, self.video_extensions
            )

            if media_type_folder == "Videos":
                counts["videos"] += 1
            elif media_type_folder == "Images":
                counts["images"] += 1
            else:
                counts["other"] += 1

        return counts

    def export_creator_data(self, items: list[ApiItem], creator: str) -> None:
        """Export API data to a JSON file for external use or backup.

        Saves all API items for a creator to a JSON file with updated video URLs.
        This is optional functionality controlled by the --save-metadata flag.

        Args:
            items: Items fetched from API
            creator: Creator username
        """
        base_path = self.get_creator_path(creator)

        out_file = base_path / f"{creator}_all_data.json"
        # Update video URLs to include preferred download parameters
        from utilities.media import update_video_url

        items_copy: list[ApiItem] = []
        for item in items:
            try:
                new_item = dict(item)
                url = new_item.get("url")
                if isinstance(url, str):
                    new_item["url"] = update_video_url(url, self.video_extensions)
                items_copy.append(cast(ApiItem, new_item))
            except (KeyError, TypeError) as e:
                log_exception(e, "Failed to update video URL in export")
                items_copy.append(item)

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(items_copy, f, indent=2)

    def filter_existing_files(
        self,
        items: list[ApiItem],
        creator: str,
        ignore_enabled: bool = True,
    ) -> list[ApiItem]:
        """Filter out items whose files already exist or are in the ignore list.

        Uses extension-agnostic matching: finds files by base name regardless of extension.

        Args:
            items: Items to check
            creator: Creator username
            ignore_enabled: If True, load and use ignore.txt to skip files

        Returns:
            List of items that need to be downloaded
        """
        result: list[ApiItem] = []
        creator_base = self.get_creator_path(creator)

        ignored_files: set[str] = set()
        if ignore_enabled:
            ignored_files = self.load_ignore_list(creator)

        all_extensions = self.image_extensions + self.video_extensions

        # Group items by folder for efficient single-scan per folder
        items_by_folder: dict[str, list[tuple[str, ApiItem]]] = {}

        for item in items:
            url = item.get("url")
            if not isinstance(url, str):
                continue

            filename = safe_filename_from_url(url)
            if ignore_enabled and filename in ignored_files:
                continue

            ext = get_extension_from_url(url)
            media_type_folder = media_type_from_extension(
                ext, self.image_extensions, self.video_extensions
            )

            media_folder = str((creator_base / media_type_folder))
            items_by_folder.setdefault(media_folder, []).append((filename, item))

        valid_exts_lower = [e.lower() for e in all_extensions]

        for folder_path_str, entries in items_by_folder.items():
            folder_path = Path(folder_path_str)
            existing_bases: set[str] | None = self._folder_scan_cache.get(
                folder_path_str
            )
            if existing_bases is None:
                existing_bases = set()
                try:
                    if folder_path.exists() and folder_path.is_dir():
                        for file_path in folder_path.iterdir():
                            if not file_path.is_file():
                                continue
                            if file_path.suffix.lower() in valid_exts_lower:
                                existing_bases.add(
                                    FileMatcherUtil.extract_base_name(file_path.name)
                                )
                except (OSError, PermissionError) as e:
                    log_exception(e, f"Failed to scan folder {folder_path}")
                    existing_bases = set()
                self._folder_scan_cache[folder_path_str] = existing_bases

            for filename, item in entries:
                base = FileMatcherUtil.extract_base_name(filename)
                if base in existing_bases:
                    continue
                result.append(item)

        return result

    def filter_items_by_media_type(
        self,
        items: list[ApiItem],
        media_config: MediaTypeConfig,
    ) -> list[ApiItem]:
        """Filter items by enabled media types.

        Args:
            items: Items to filter
            media_config: Media type configuration

        Returns:
            Filtered list of items
        """
        filtered_items: list[ApiItem] = []
        media_dict = media_config.to_dict()

        for item in items:
            url = item.get("url")
            if not url:
                continue

            ext = get_extension_from_url(url)
            media_type_folder = media_type_from_extension(
                ext, self.image_extensions, self.video_extensions
            )
            media_type_key = media_type_folder.lower()

            if media_dict.get(media_type_key, False):
                filtered_items.append(item)

        return filtered_items

    def get_media_folder(self, creator: str, url: str) -> Path:
        """Get the appropriate media folder for a URL.

        Args:
            creator: Creator username
            url: Media URL

        Returns:
            Path to the media type folder
        """
        ext = get_extension_from_url(url)
        media_type_folder = media_type_from_extension(
            ext, self.image_extensions, self.video_extensions
        )

        folder = self.get_creator_path(creator) / media_type_folder
        folder.mkdir(parents=True, exist_ok=True)

        return folder

    def invalidate_folder_cache(self, folder: Path) -> None:
        """Invalidate the cached scan for a folder.

        Call this after writing a file into the folder so subsequent checks
        will re-scan if necessary.

        Args:
            folder: Path to the folder to invalidate
        """
        key = str(folder)
        self._folder_scan_cache.pop(key, None)

    def get_output_path(self, creator: str, url: str) -> Path:
        """Get the full output path for a media file.

        Args:
            creator: Creator username
            url: Media URL (must not be None)

        Returns:
            Full path where file should be saved
        """
        folder = self.get_media_folder(creator, url)
        filename = safe_filename_from_url(url)
        return folder / filename

    def get_all_creator_folders(self) -> list[str]:
        """Get list of all creator folder names in the output directory.

        Returns:
            List of creator folder names
        """
        creator_folders: list[str] = []

        if not self.output_folder.exists():
            return creator_folders

        for item in self.output_folder.iterdir():
            if item.is_dir():
                creator_folders.append(item.name)

        return creator_folders

    def find_creator_folder_case_insensitive(self, creator_name: str) -> Path | None:
        """Find a creator folder with case-insensitive matching.

        Args:
            creator_name: Creator name to search for

        Returns:
            Path to the creator folder, or None if not found
        """
        if not self.output_folder.exists():
            return None

        creator_name_lower = creator_name.lower()

        for item in self.output_folder.iterdir():
            if item.is_dir() and item.name.lower() == creator_name_lower:
                return item

        return None

    def get_video_files_in_folder(
        self, folder: Path, video_extensions: list[str]
    ) -> list[Path]:
        """Get all video files in a folder (non-recursive).

        Args:
            folder: Path to the folder to search
            video_extensions: List of video file extensions

        Returns:
            List of paths to video files
        """
        video_files: list[Path] = []

        if not folder.exists() or not folder.is_dir():
            return video_files

        for item in folder.iterdir():
            if item.is_file() and item.suffix.lower() in video_extensions:
                video_files.append(item)

        return video_files
