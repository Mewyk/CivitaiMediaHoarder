"""Handler for update operations.

This module provides update handlers that process creators and return
UpdateOperationSummary objects with detailed results.
"""

from __future__ import annotations

from configuration.manager import ConfigManager
from core.component_factory import ComponentFactory, install_sigint_handler
from core.extension_tracker import get_extension_tracker
from core.operation_results import OperationType, UpdateOperationSummary
from models.config import CreatorConfig, MediaTypeConfig
from terminal.cli import ParsedArgs
from utilities.debug_logger import get_logger
from utilities.logging_utils import safe_log


def handle_update(
    parsed: ParsedArgs,
    config_manager: ConfigManager,
) -> UpdateOperationSummary:
    """Handle --update command.

    When creators are specified, processes only those creators.
    When no creators are specified, processes all creators from config.

    For each creator:
    - If in config: use their media settings
    - If not in config: use default media types

    Args:
        parsed: Parsed command-line arguments.
        config_manager: ConfigManager instance.

    Returns:
        Results of the update operation.
    """
    config = config_manager.load_config()

    # Get creator names from parsed args
    creator_names: list[str] = parsed.creators

    existing_creators: dict[str, CreatorConfig] = {
        creator.username.lower(): creator for creator in config.creators
    }

    creators_to_process: list[tuple[str, MediaTypeConfig]] = []

    if creator_names:
        # Process only specified creators
        for name in creator_names:
            name_lower = name.lower()
            if name_lower in existing_creators:
                creator_config = existing_creators[name_lower]
                media_config = config_manager.get_creator_media_config(
                    creator_config,
                    config.default_media_types,
                )
                creators_to_process.append((creator_config.username, media_config))
            else:
                creators_to_process.append((name, config.default_media_types))
    else:
        # No creators specified - process all from config
        if not config.creators:
            return UpdateOperationSummary(
                operation_type=OperationType.UPDATE,
                successful=0,
                failed=0,
                total=0,
                warnings=["No creators found in configuration"],
            )
        for creator_config in config.creators:
            media_config = config_manager.get_creator_media_config(
                creator_config,
                config.default_media_types,
            )
            creators_to_process.append((creator_config.username, media_config))

    safe_log(
        f"Creators to process: {[c for c, _ in creators_to_process]}\n",
        level="INFO",
    )

    enable_debug = get_logger() is not None
    components = ComponentFactory.create_all(config, enable_debug=enable_debug)

    safe_log("Components initialized\n", level="INFO")
    install_sigint_handler(components.display_manager)

    ignore_enabled = not parsed.ignore_off
    auto_purge = parsed.auto_purge
    save_metadata = parsed.save_metadata

    (
        deleted_creators,
        failed_creator_list,
        successful_creators,
        failed_creators,
        total_api_items,
        total_files_needing_download,
        total_files_downloaded,
        total_images_downloaded,
        total_videos_downloaded,
    ) = components.processor.process_creators(
        creators=creators_to_process,
        nsfw=config.nsfw,
        auto_purge=auto_purge,
        ignore_enabled=ignore_enabled,
        save_metadata=save_metadata,
    )

    safe_log(
        f"Update summary: total_api_items={total_api_items}, "
        f"files_needed={total_files_needing_download}, "
        f"files_downloaded={total_files_downloaded}\n",
        level="INFO",
    )

    # Get all corrections from centralized tracker
    extension_tracker = get_extension_tracker()
    all_corrections = extension_tracker.get_all_corrections()

    components.display_manager.console.clear()

    # Note: UpdateOperationSummary inherits from OperationSummary with these fields:
    # operation_type, successful, failed, total, warnings
    return UpdateOperationSummary(
        operation_type=OperationType.UPDATE,
        successful=successful_creators,
        failed=failed_creators,
        total=len(creators_to_process),
        warnings=[],
        api_items_total=total_api_items,
        files_downloaded=total_files_downloaded,
        files_needed=total_files_needing_download,
        images_downloaded=total_images_downloaded,
        videos_downloaded=total_videos_downloaded,
        images_needed=0,
        videos_needed=0,
        extension_corrections=all_corrections,
        downloaded_extensions=components.downloader.downloaded_extensions,
        deleted_creators=deleted_creators,
        failed_creators=failed_creator_list,
    )
