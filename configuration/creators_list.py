"""Creators list management for separate CreatorsList.json file.

This module handles loading and saving the creators list separately from
the main configuration, providing better separation of concerns.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

from models.config import CreatorConfig


class CreatorsListManager:
    """Manages the CreatorsList.json file separately from Configuration.json."""

    DEFAULT_FILENAME = "CreatorsList.json"

    def __init__(self, creators_file: str | Path | None = None) -> None:
        """Initialize the creators list manager.

        Args:
            creators_file: Path to the creators list file.
                          Defaults to CreatorsList.json in current directory.
        """
        if creators_file is None:
            self.creators_file = Path(self.DEFAULT_FILENAME)
        else:
            self.creators_file = Path(creators_file)

    def exists(self) -> bool:
        """Check if the creators list file exists."""
        return self.creators_file.exists()

    def load(self) -> list[CreatorConfig]:
        """Load creators from the creators list file.

        Returns:
            List of CreatorConfig objects.

        Raises:
            SystemExit: If the file cannot be read or parsed.
        """
        if not self.exists():
            return []

        try:
            with open(self.creators_file, "r", encoding="utf-8") as f:
                data: object = json.load(f)
        except json.JSONDecodeError as e:
            sys.exit(f"Error parsing {self.creators_file}: {e}")
        except OSError as e:
            sys.exit(f"Error reading {self.creators_file}: {e}")

        if not isinstance(data, dict):
            sys.exit(f"Invalid {self.creators_file}: expected object at root")

        creators_raw: object = data.get("creators", [])
        if not isinstance(creators_raw, list):
            sys.exit(f"Invalid {self.creators_file}: 'creators' must be a list")

        creators: list[CreatorConfig] = []
        invalid_entries: list[str] = []

        for idx, creator_value in enumerate(creators_raw, 1):
            try:
                creator = CreatorConfig.from_value(
                    cast(str | dict[str, object], creator_value)
                )
                creators.append(creator)
            except ValueError as e:
                entry_str = str(creator_value)
                entry_repr = entry_str if len(entry_str) < 50 else entry_str[:47] + "..."
                invalid_entries.append(f"Entry #{idx}: {e} ({entry_repr})")

        if invalid_entries:
            print(
                f"\nWarning: Skipped {len(invalid_entries)} invalid creator(s) "
                f"in {self.creators_file}:",
                file=sys.stderr,
            )
            for entry_error in invalid_entries:
                print(f"  - {entry_error}", file=sys.stderr)
            print("", file=sys.stderr)

        return creators

    def save(self, creators: list[CreatorConfig]) -> None:
        """Save creators to the creators list file.

        Args:
            creators: List of CreatorConfig objects to save.

        Raises:
            OSError: If the file cannot be written.
        """
        data = {
            "creators": [c.to_value() for c in creators]
        }
        with open(self.creators_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_creators(
        self,
        new_creators: list[CreatorConfig],
        existing: list[CreatorConfig],
    ) -> tuple[list[CreatorConfig], list[str], list[str]]:
        """Add new creators to the list, avoiding duplicates.

        Args:
            new_creators: Creators to add.
            existing: Existing creators list.

        Returns:
            Tuple of (updated_list, added_names, skipped_names).
        """
        existing_names = {c.username.lower() for c in existing}
        result = list(existing)
        added: list[str] = []
        skipped: list[str] = []

        for creator in new_creators:
            if creator.username.lower() in existing_names:
                skipped.append(creator.username)
            else:
                result.append(creator)
                existing_names.add(creator.username.lower())
                added.append(creator.username)

        return result, added, skipped

    def remove_creator(
        self,
        username: str,
        existing: list[CreatorConfig],
    ) -> tuple[list[CreatorConfig], bool]:
        """Remove a creator from the list.

        Args:
            username: Creator username to remove.
            existing: Existing creators list.

        Returns:
            Tuple of (updated_list, was_removed).
        """
        username_lower = username.lower()
        result: list[CreatorConfig] = []
        removed = False

        for creator in existing:
            if creator.username.lower() == username_lower:
                removed = True
            else:
                result.append(creator)

        return result, removed

    def find_creator(
        self,
        username: str,
        creators: list[CreatorConfig],
    ) -> CreatorConfig | None:
        """Find a creator by username (case-insensitive).

        Args:
            username: Creator username to find.
            creators: List of creators to search.

        Returns:
            CreatorConfig if found, None otherwise.
        """
        username_lower = username.lower()
        for creator in creators:
            if creator.username.lower() == username_lower:
                return creator
        return None


