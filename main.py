#!/usr/bin/env python3
"""Civitai Media Hoarder - Main CLI Entry Point.

A tool for downloading media from Civitai creators with flexible filtering
and management capabilities.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import cast

from configuration.manager import ConfigManager
from core.component_factory import ComponentFactory
from core.display_manager import DisplayManager
from core.result_printer import ResultPrinter
from handlers.repair_handler import handle_repair_videos as _handle_repair_videos
from handlers.update_handler import handle_update as _handle_update
from handlers.verify_handler import handle_verify_unified as _handle_verify_unified
from models.config import CreatorConfig, MediaTypeConfig
from terminal import OperationMode, ParsedArgs, parse_arguments
from utilities.debug_logger import buffer as debug_buffer, finalize, get_logger, init_debug


def handle_add(parsed: ParsedArgs, config_manager: ConfigManager) -> None:
    """Handle --add command.

    Adds one or more creators to the config, then processes them.

    Args:
        parsed: Parsed command-line arguments.
        config_manager: ConfigManager instance.
    """
    creator_names = parsed.creators
    if not creator_names:
        sys.exit("Error: No valid creator names provided")

    # Build media types dict from parsed flags
    media_types = parsed.media_types.to_dict() if parsed.media_types.has_any() else None

    # Add creators to config
    config_manager.add_creator(creator_names, media_types)

    # Load config to get the updated list and settings
    config = config_manager.load_config()

    # Build list of (username, MediaTypeConfig) tuples for processing
    creators_to_process: list[tuple[str, MediaTypeConfig]] = []

    # Find the newly added creators in config
    existing_creators: dict[str, CreatorConfig] = {
        creator.username.lower(): creator for creator in config.creators
    }

    for name in creator_names:
        name_lower = name.lower()
        if name_lower in existing_creators:
            creator_config = existing_creators[name_lower]
            media_config = config_manager.get_creator_media_config(
                creator_config, config.default_media_types
            )
            creators_to_process.append((creator_config.username, media_config))

    if not creators_to_process:
        return

    # Create all components using factory
    enable_debug = get_logger() is not None
    components = ComponentFactory.create_all(config, enable_debug=enable_debug)

    # Process the newly added creators
    (
        deleted_creators,
        failed_creator_list,
        successful_creators,
        _failed_creators_count,
        total_api_items,
        total_files_needing_download,
        total_files_downloaded,
        _total_images_downloaded,
        _total_videos_downloaded,
    ) = components.processor.process_creators(
        creators=creators_to_process,
        nsfw=config.nsfw,
        auto_purge=False,
        ignore_enabled=True,
        save_metadata=parsed.save_metadata,
    )

    # Display results using ResultPrinter
    from core.extension_tracker import get_extension_tracker
    from core.operation_results import OperationType, UpdateOperationSummary

    extension_tracker = get_extension_tracker()

    summary = UpdateOperationSummary(
        operation_type=OperationType.UPDATE,
        successful=successful_creators,
        failed=len(failed_creator_list),
        total=len(creators_to_process),
        warnings=[],
        api_items_total=total_api_items,
        files_downloaded=total_files_downloaded,
        files_needed=total_files_needing_download,
        images_downloaded=0,
        videos_downloaded=0,
        images_needed=0,
        videos_needed=0,
        extension_corrections=extension_tracker.get_all_corrections(),
        downloaded_extensions={},
        deleted_creators=deleted_creators,
        failed_creators=failed_creator_list,
    )

    printer = ResultPrinter(components.display_manager.console)
    printer.print_update_summary(summary)


def handle_remove(parsed: ParsedArgs, config_manager: ConfigManager) -> None:
    """Handle --remove command.

    Args:
        parsed: Parsed command-line arguments.
        config_manager: ConfigManager instance.
    """
    if not parsed.creators:
        sys.exit("Error: No creator specified for removal")
    config_manager.remove_creator(parsed.creators[0])


def handle_update(parsed: ParsedArgs, config_manager: ConfigManager) -> None:
    """Handle --update command.

    Updates specified creators, or all creators if none specified.
    Delegates to handlers module and prints results using ResultPrinter.

    Args:
        parsed: Parsed command-line arguments.
        config_manager: ConfigManager instance.
    """
    summary = _handle_update(parsed, config_manager)

    display_manager = DisplayManager()
    printer = ResultPrinter(display_manager.console)
    printer.print_update_summary(summary)

    # Handle maintenance/purging if needed
    if summary.deleted_creators and parsed.auto_purge:
        deleted_content = (
            "The following creators were purged:\n"
            + "\n".join(f"  - {name}" for name in summary.deleted_creators)
        )
        printer.print_confirmation_panel(deleted_content, title="Maintenance | Completed")


def handle_verify(parsed: ParsedArgs, config_manager: ConfigManager) -> None:
    """Handle verification of media files.

    Delegates to the verify handler and prints results.

    Args:
        parsed: Parsed command-line arguments.
        config_manager: ConfigManager instance.
    """
    summary = _handle_verify_unified(parsed, config_manager)

    display_manager = summary.display_manager
    failed_creators = summary.failed_creators_list
    invalids = summary.invalids
    repair_manager_ref = summary.repair_manager

    if display_manager:
        printer = ResultPrinter(display_manager.console)
        printer.print_verify_summary(summary)

        if failed_creators:
            printer.print_error_panel(failed_creators)

        if invalids and repair_manager_ref:
            report_path = Path(repair_manager_ref.REPORT_FILENAME)
            saved = repair_manager_ref.save_report(
                invalids, report_path, auto_yes=parsed.yes
            )

            if saved:
                display_manager.console.print(
                    f"\n[green]Report saved to: {repair_manager_ref.REPORT_FILENAME}[/green]"
                )
                display_manager.console.print("[dim]Use --repair to fix these videos.[/dim]")


def handle_repair(parsed: ParsedArgs, config_manager: ConfigManager) -> None:
    """Handle --repair command.

    Delegates to handlers module and prints results using ResultPrinter.

    Args:
        parsed: Parsed command-line arguments.
        config_manager: ConfigManager instance.
    """
    summary = _handle_repair_videos(parsed, config_manager)

    display_manager = DisplayManager()
    printer = ResultPrinter(display_manager.console)
    printer.print_repair_summary(summary)


def setup_exception_hook() -> None:
    """Configure global exception handling for debug logging."""

    def _excepthook(
        exc_type: type[BaseException],
        exc_value: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            debug_buffer(
                f"Unhandled exception: {exc_type.__name__}: {exc_value}\n",
                level="ERROR",
            )
        except Exception:
            pass
        try:
            finalize()
        except Exception:
            pass
        try:
            sys.__excepthook__(exc_type, cast(BaseException, exc_value), exc_tb)
        except Exception:
            pass

    sys.excepthook = _excepthook


def main() -> None:
    """Main entry point for the CLI application."""
    parsed = parse_arguments()
    config_manager = ConfigManager()

    # Initialize debug logging if requested
    if parsed.debug:
        logdir = Path("logs")
        init_debug(logdir)
        debug_buffer(
            f"Debug mode enabled at "
            f"{datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}\n",
            level="INFO",
        )

    setup_exception_hook()

    try:
        if parsed.mode == OperationMode.ADD:
            handle_add(parsed, config_manager)
        elif parsed.mode == OperationMode.REMOVE:
            handle_remove(parsed, config_manager)
        elif parsed.mode == OperationMode.UPDATE:
            handle_update(parsed, config_manager)
        elif parsed.mode in (
            OperationMode.VERIFY,
            OperationMode.VERIFY_IMAGES,
            OperationMode.VERIFY_VIDEOS,
        ):
            handle_verify(parsed, config_manager)
        elif parsed.mode == OperationMode.REPAIR:
            handle_repair(parsed, config_manager)
    except KeyboardInterrupt:
        try:
            debug_buffer(
                "User interrupted execution (KeyboardInterrupt)\n", level="WARNING"
            )
        except Exception:
            pass
    finally:
        try:
            finalize()
        except Exception:
            pass


if __name__ == "__main__":
    main()
