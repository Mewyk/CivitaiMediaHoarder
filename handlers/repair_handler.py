"""Handler for repair operations.

This module provides repair handlers that identify and fix corrupted video files
by removing them and redownloading from source.
"""

from __future__ import annotations

from pathlib import Path

from configuration.manager import ConfigManager
from core.component_factory import ComponentFactory, install_sigint_handler
from core.operation_results import OperationType, RepairOperationSummary
from core.repair_manager import RepairManager
from models.config import AppConfig
from terminal.cli import ParsedArgs


def handle_repair_videos(
    parsed: ParsedArgs,
    config_manager: ConfigManager,
) -> RepairOperationSummary:
    """Handle --repair command.

    Repairs invalid videos found in the InvalidVideos.json report by:
    1. Removing the corrupted files
    2. Redownloading them from source

    Args:
        parsed: Parsed command-line arguments.
        config_manager: ConfigManager instance.

    Returns:
        Results of the repair operation.
    """
    config: AppConfig = config_manager.load_config()

    repair_manager = RepairManager()
    report_path = Path(repair_manager.REPORT_FILENAME)

    components = ComponentFactory.create_all(config, enable_debug=False)
    install_sigint_handler(components.display_manager)

    total_attempted, total_succeeded = repair_manager.repair_videos(
        report_path=report_path,
        config=config,
        auto_yes=parsed.yes,
        file_manager=components.file_manager,
        downloader=components.downloader,
        display_manager=components.display_manager,
    )

    invalid_videos_json_kept = report_path.exists()
    components.display_manager.console.clear()

    # Per-creator stats not returned by repair_manager
    per_creator_stats: dict[str, tuple[int, int]] = {}

    return RepairOperationSummary(
        operation_type=OperationType.REPAIR,
        successful=(
            1 if total_succeeded == total_attempted and total_attempted > 0 else 0
        ),
        failed=0 if total_succeeded == total_attempted else 1,
        total=1 if total_attempted > 0 else 0,
        warnings=[],
        files_removed=total_attempted,
        files_redownloaded=total_succeeded,
        per_creator_stats=per_creator_stats,
        invalid_videos_json_kept=invalid_videos_json_kept,
    )
