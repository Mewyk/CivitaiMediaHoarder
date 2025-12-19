"""Configuration file management with validation and CRUD operations."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import cast

from configuration.creators_list import CreatorsListManager
from models.config import AppConfig, CreatorConfig, MediaTypeConfig
from models.types import LockPolicy


class ConfigManager:
    """Manages loading, validating, and modifying configuration files.

    Handles Configuration.json (settings) and CreatorsList.json (creators)
    as separate files.
    """

    def __init__(
        self,
        config_file: str = "Configuration.json",
        creators_file: str = "CreatorsList.json",
    ) -> None:
        """Initialize ConfigManager.

        Args:
            config_file: Path to the configuration file.
            creators_file: Path to the creators list file.
        """
        self.config_file = config_file
        self.creators_manager = CreatorsListManager(creators_file)
    
    def validate_config_dict(self, config: dict[str, object]) -> list[str]:
        """Validate configuration dictionary structure.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            List of error messages (empty if valid).
        """
        errors: list[str] = []

        # Validate api_key
        if "api_key" not in config:
            errors.append("Missing required field: 'api_key'")
        elif not isinstance(config["api_key"], str) or not config["api_key"]:
            errors.append("Field 'api_key' must be a non-empty string")

        # Validate default_output
        if "default_output" not in config:
            errors.append("Missing required field: 'default_output'")
        elif not isinstance(config["default_output"], str) or not config["default_output"]:
            errors.append("Field 'default_output' must be a non-empty string")

        # Validate nsfw
        if "nsfw" not in config:
            errors.append("Missing required field: 'nsfw'")
        elif not isinstance(config["nsfw"], bool):
            errors.append("Field 'nsfw' must be a boolean (true or false)")

        # Validate rate_limit
        if "rate_limit" not in config:
            errors.append("Missing required field: 'rate_limit'")
        elif not isinstance(config["rate_limit"], bool):
            errors.append("Field 'rate_limit' must be a boolean (true or false)")

        # Validate request_timeout
        if "request_timeout" not in config:
            errors.append("Missing required field: 'request_timeout'")
        elif not isinstance(config["request_timeout"], int) or config["request_timeout"] <= 0:
            errors.append("Field 'request_timeout' must be a positive integer")

        # Validate download_timeout
        if "download_timeout" not in config:
            errors.append("Missing required field: 'download_timeout'")
        elif not isinstance(config["download_timeout"], int) or config["download_timeout"] <= 0:
            errors.append("Field 'download_timeout' must be a positive integer")

        # Validate max_retries
        if "max_retries" not in config:
            errors.append("Missing required field: 'max_retries'")
        elif not isinstance(config["max_retries"], int) or config["max_retries"] < 1:
            errors.append("Field 'max_retries' must be an integer >= 1")

        # Validate retry_backoff_sec
        if "retry_backoff_sec" not in config:
            errors.append("Missing required field: 'retry_backoff_sec'")
        elif not isinstance(config["retry_backoff_sec"], int) or config["retry_backoff_sec"] <= 0:
            errors.append("Field 'retry_backoff_sec' must be a positive integer")

        # Validate image_extensions
        if "image_extensions" not in config:
            errors.append("Missing required field: 'image_extensions'")
        elif not isinstance(config["image_extensions"], list) or not config["image_extensions"]:
            errors.append("Field 'image_extensions' must be a non-empty list")

        # Validate video_extensions
        if "video_extensions" not in config:
            errors.append("Missing required field: 'video_extensions'")
        elif not isinstance(config["video_extensions"], list) or not config["video_extensions"]:
            errors.append("Field 'video_extensions' must be a non-empty list")

        # Validate default_media_types
        if "default_media_types" not in config:
            errors.append("Missing required field: 'default_media_types'")
        elif not isinstance(config["default_media_types"], dict):
            errors.append("Field 'default_media_types' must be a dictionary")
        else:
            media_types_dict = cast(dict[str, object], config["default_media_types"])
            for key in ["images", "videos", "other"]:
                if key not in media_types_dict:
                    errors.append(f"Field 'default_media_types' missing required key: '{key}'")
                elif not isinstance(media_types_dict[key], bool):
                    errors.append(f"Field 'default_media_types.{key}' must be a boolean")

        # Optional: memory_threshold_bytes
        if "memory_threshold_bytes" in config:
            if not isinstance(config["memory_threshold_bytes"], int) or config["memory_threshold_bytes"] < 0:
                errors.append("Field 'memory_threshold_bytes' must be a non-negative integer")

        # Optional: download_lock_policy
        if "download_lock_policy" in config:
            valid_policies = [p.value for p in LockPolicy]
            if (
                not isinstance(config["download_lock_policy"], str)
                or config["download_lock_policy"] not in valid_policies
            ):
                errors.append(
                    f"Field 'download_lock_policy' must be one of: {', '.join(valid_policies)}"
                )

        return errors
    
    def load_config(self) -> AppConfig:
        """Load and validate configuration from files.

        Loads settings from Configuration.json and creators from CreatorsList.json.

        Returns:
            AppConfig instance.

        Raises:
            SystemExit: If configuration file is missing or invalid.
        """
        if not os.path.exists(self.config_file):
            sys.exit(
                f"Missing {self.config_file}. Please create it with the required fields.\n"
                f"See README.md for configuration documentation."
            )

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            sys.exit(f"Error parsing {self.config_file}: {e}")
        except OSError as e:
            sys.exit(f"Error reading {self.config_file}: {e}")

        # Validate configuration
        errors = self.validate_config_dict(data)
        if errors:
            error_msg = f"\n{self.config_file} validation failed:\n"
            for error in errors:
                error_msg += f"  - {error}\n"
            sys.exit(error_msg)

        # Load creators from CreatorsList.json
        creators = self.creators_manager.load()

        # Parse into AppConfig
        try:
            return AppConfig.from_dict(cast(dict[str, object], data), creators=creators)
        except (KeyError, ValueError, TypeError) as e:
            sys.exit(f"Error loading configuration: {e}")

    def save_config(self, config: AppConfig) -> None:
        """Save configuration to files.

        Settings go to Configuration.json, creators go to CreatorsList.json.

        Args:
            config: AppConfig instance to save.

        Raises:
            OSError: If unable to write to file.
        """
        # Save settings (without creators)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(include_creators=False), f, indent=2)

        # Save creators
        self.creators_manager.save(config.creators)

    def add_creator(
        self,
        usernames: list[str],
        media_types: dict[str, bool] | None = None,
    ) -> None:
        """Add one or more creators to the configuration.

        If media_types is provided and creator already exists, updates their settings.

        Args:
            usernames: List of creator usernames.
            media_types: Optional media type preferences (applied to all creators).

        Raises:
            SystemExit: If usernames list is empty or contains duplicates.
        """
        if not usernames:
            sys.exit("Error: No creator usernames provided")

        # Clean and validate usernames
        cleaned_names: list[str] = []
        for name in usernames:
            if not name or not name.strip():
                sys.exit("Error: Creator username cannot be empty")
            cleaned_names.append(name.strip())

        # Load current config
        config = self.load_config()

        # Build mapping of existing creators (case-insensitive)
        existing_creators_map: dict[str, CreatorConfig] = {
            creator.username.lower(): creator for creator in config.creators
        }

        # Track results
        new_creators: list[CreatorConfig] = []
        updated_creators: list[str] = []
        unchanged_creators: list[str] = []
        seen_in_new: set[str] = set()
        duplicates_in_list: list[str] = []

        for name in cleaned_names:
            name_lower = name.lower()

            # Check for duplicates within the provided list
            if name_lower in seen_in_new:
                duplicates_in_list.append(name)
                continue

            seen_in_new.add(name_lower)

            # Check if creator already exists
            if name_lower in existing_creators_map:
                # If media_types is provided, check if update is needed
                if media_types:
                    existing_creator = existing_creators_map[name_lower]

                    # Get the base settings (existing custom or global defaults)
                    if existing_creator.media_types is not None:
                        base_dict = existing_creator.media_types.to_dict()
                    else:
                        # Using global defaults, so use them as base
                        base_dict = config.default_media_types.to_dict()

                    # Merge: start with base, override with provided media_types
                    merged_dict = base_dict.copy()
                    merged_dict.update(media_types)
                    new_media_config = MediaTypeConfig.from_dict(merged_dict)

                    # Check if settings are actually different from current state
                    current_dict = (
                        existing_creator.media_types.to_dict()
                        if existing_creator.media_types
                        else config.default_media_types.to_dict()
                    )
                    settings_changed = any(
                        merged_dict.get(key) != current_dict.get(key)
                        for key in ["images", "videos", "other"]
                    )

                    if settings_changed:
                        existing_creator.media_types = new_media_config
                        updated_creators.append(existing_creator.username)
                    else:
                        unchanged_creators.append(existing_creator.username)
                else:
                    # No media_types provided, skip existing creator
                    duplicates_in_list.append(name)
            else:
                # Create new creator
                if media_types:
                    # Merge with global defaults so unspecified flags use defaults
                    base_dict = config.default_media_types.to_dict()
                    merged_dict = base_dict.copy()
                    merged_dict.update(media_types)
                    media_config = MediaTypeConfig.from_dict(merged_dict)
                    new_creator = CreatorConfig(username=name, media_types=media_config)
                else:
                    new_creator = CreatorConfig(username=name)

                new_creators.append(new_creator)

        # Report skipped creators
        if duplicates_in_list:
            print(
                f"✗ Skipped {len(duplicates_in_list)} creator(s) already in master "
                "list (use media type flags to update):"
            )
            for name in duplicates_in_list:
                print(f"  - {name}")

        if unchanged_creators:
            print(f"➤ Skipped {len(unchanged_creators)} creator(s) with unchanged settings:")
            for name in unchanged_creators:
                print(f"  - {name}")

        # If no valid creators to add or update, exit
        if not new_creators and not updated_creators:
            sys.exit("Error: No creators to add or update")

        # Add all new creators to config
        config.creators.extend(new_creators)

        # Save
        self.save_config(config)

        # Print success messages
        if updated_creators:
            if len(updated_creators) == 1:
                print(
                    f"✓ Successfully updated creator '{updated_creators[0]}' "
                    "in the master list"
                )
            else:
                print(
                    f"✓ Successfully updated {len(updated_creators)} creator(s) "
                    "in the master list:"
                )
                for name in updated_creators:
                    print(f"  - {name}")

        if new_creators:
            if len(new_creators) == 1:
                print(
                    f"✓ Successfully added creator '{new_creators[0].username}' "
                    "to the master list"
                )
            else:
                print(
                    f"✓ Successfully added {len(new_creators)} creators "
                    "to the master list:"
                )
                for creator in new_creators:
                    print(f"  - {creator.username}")

        if media_types:
            enabled = [k for k, v in media_types.items() if v]
            print(
                f"  Media types: {', '.join(enabled) if enabled else 'none (using defaults)'}"
            )

    def remove_creator(self, username: str) -> None:
        """Remove a creator from the configuration.

        Args:
            username: Creator username to remove.

        Raises:
            SystemExit: If username is invalid or not found.
        """
        if not username or not username.strip():
            sys.exit("Error: Creator username cannot be empty")

        username = username.strip()

        # Load current config
        config = self.load_config()

        # Find and remove
        original_count = len(config.creators)
        config.creators = [
            creator
            for creator in config.creators
            if creator.username.lower() != username.lower()
        ]

        if len(config.creators) == original_count:
            sys.exit(f"Error: Creator '{username}' not found in the master list")

        # Save
        self.save_config(config)

        print(f"✓ Successfully removed creator '{username}' from the master list")

    def get_creator_media_config(
        self,
        creator: CreatorConfig,
        default_media_types: MediaTypeConfig,
    ) -> MediaTypeConfig:
        """Get effective media type configuration for a creator.

        Args:
            creator: Creator configuration.
            default_media_types: Default media type configuration.

        Returns:
            Merged media type configuration.
        """
        # If creator has no custom media types, use defaults
        if creator.media_types is None:
            return default_media_types

        # Otherwise, merge creator's custom settings with defaults
        return default_media_types.merge_with(creator.media_types.to_dict())

    def purge_deleted_creators(self, usernames: list[str]) -> None:
        """Remove deleted creators from configuration.

        Saves purged creators to PurgedCreators.json for reference.

        Args:
            usernames: List of creator usernames to purge.
        """
        if not usernames:
            return

        # Load current config
        config = self.load_config()

        # Find creators to purge (case-insensitive)
        username_lower_set = {name.lower() for name in usernames}
        creators_to_purge: list[CreatorConfig] = []
        remaining_creators: list[CreatorConfig] = []

        for creator in config.creators:
            if creator.username.lower() in username_lower_set:
                creators_to_purge.append(creator)
            else:
                remaining_creators.append(creator)

        if not creators_to_purge:
            print("No creators found to purge.")
            return

        # Update config with remaining creators
        config.creators = remaining_creators
        self.save_config(config)

        # Load or create purged creators file
        purged_file = Path("PurgedCreators.json")
        purged_data: dict[str, object] = {}

        if purged_file.exists():
            try:
                with open(purged_file, "r", encoding="utf-8") as f:
                    loaded_data: object = json.load(f)
                    if isinstance(loaded_data, dict):
                        purged_data = cast(dict[str, object], loaded_data)
                    else:
                        purged_data = {}
            except (json.JSONDecodeError, OSError):
                purged_data = {}

        # Ensure purged_creators key exists and is a list
        if "purged_creators" not in purged_data:
            purged_data["purged_creators"] = []
        elif not isinstance(purged_data["purged_creators"], list):
            purged_data["purged_creators"] = []

        # Add timestamp and append purged creators
        timestamp = datetime.now().isoformat()

        purged_list = cast(list[dict[str, object]], purged_data["purged_creators"])

        for creator in creators_to_purge:
            purged_entry: dict[str, object] = {
                "username": creator.username,
                "purged_at": timestamp,
            }
            if creator.media_types is not None:
                purged_entry["media_types"] = creator.media_types.to_dict()

            purged_list.append(purged_entry)

        purged_data["purged_creators"] = purged_list

        # Save purged creators file
        with open(purged_file, "w", encoding="utf-8") as f:
            json.dump(purged_data, f, indent=2)