"""Handler for verification operations.

This module provides verification handlers that process images and videos,
returning VerifyOperationSummary objects with detailed verification results.
"""

from __future__ import annotations

from pathlib import Path

from configuration.manager import ConfigManager
from core.component_factory import install_sigint_handler
from core.display_manager import DisplayManager
from core.extension_tracker import get_extension_tracker
from core.operation_results import OperationType, VerifyOperationSummary
from core.repair_manager import RepairManager
from core.verification_results import VerificationSummary
from models.types import InvalidVideoEntry
from terminal.cli import ParsedArgs, VerifyMode
from utilities.logging_utils import log_exception
from utilities.video_validator import VideoValidator


def _count_files_fast(folder: Path, extensions: list[str] | None = None) -> int:
    """Count files in a folder without creating intermediate lists.

    Uses generator-based counting to avoid memory overhead of list().

    Args:
        folder: Path to the folder to count files in.
        extensions: Optional list of extensions to filter by.

    Returns:
        Number of files matching the criteria.
    """
    if not folder.exists():
        return 0
    if extensions is None:
        return sum(1 for f in folder.iterdir() if f.is_file())
    ext_set = set(extensions)
    return sum(
        1
        for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in ext_set
    )


def handle_verify_unified(
    parsed: ParsedArgs,
    config_manager: ConfigManager,
) -> VerifyOperationSummary:
    """Unified verification handler for both Images and Videos.

    Single entry point for all verify commands:
    - --verify (both images and videos)
    - --verify-images (images only)
    - --verify-videos (videos only)

    Args:
        parsed: Parsed command-line arguments.
        config_manager: ConfigManager instance.

    Returns:
        Results of the verification operation.
    """
    config = config_manager.load_config()
    output_folder = Path(config.default_output)

    if not output_folder.exists():
        display = DisplayManager()
        display.console.print(
            f"[orange3]Output folder not found: {output_folder}[/orange3]"
        )
        return VerifyOperationSummary(
            operation_type=OperationType.VERIFY,
            successful=0,
            failed=0,
            total=0,
            warnings=["Output folder not found"],
        )

    # Parse which verification modes are active
    verify_images = parsed.verify_mode == VerifyMode.IMAGES
    verify_videos = parsed.verify_mode == VerifyMode.VIDEOS
    verify_both = parsed.verify_mode == VerifyMode.ALL

    # Get creator names from parsed args
    creator_names: list[str] = parsed.creators

    # Find creators to scan
    if creator_names:
        creator_names_lower = {name.lower() for name in creator_names}
        creators_to_scan = [
            item
            for item in output_folder.iterdir()
            if item.is_dir() and item.name.lower() in creator_names_lower
        ]
    else:
        creators_to_scan = [
            item for item in output_folder.iterdir() if item.is_dir()
        ]

    if not creators_to_scan:
        display = DisplayManager()
        display.console.print("[orange3]No creators found to verify.[/orange3]")
        return VerifyOperationSummary(
            operation_type=OperationType.VERIFY,
            successful=0,
            failed=0,
            total=0,
            warnings=["No creators found"],
        )

    summary = VerificationSummary(
        creators_processed=len(creators_to_scan),
        creators_failed=0,
    )

    should_verify_images = verify_images or verify_both
    should_verify_videos = verify_videos or verify_both

    validator = VideoValidator()
    display_manager = DisplayManager()
    install_sigint_handler(display_manager)

    total_creators = len(creators_to_scan)
    invalids: dict[str, list[InvalidVideoEntry]] = {}
    failed_creator_list: list[tuple[str, str]] = []

    # Use panel mode for consistent UI with update handler
    display_manager.set_panel_mode(True, total_creators)
    display_manager.start()

    for creator_index, creator_folder in enumerate(creators_to_scan, start=1):
        current_creator_name = creator_folder.name

        # Update global progress and start this creator
        display_manager.update_global_progress(creator_index - 1)
        display_manager.start_creator(current_creator_name)

        try:
            if should_verify_images:
                images_folder = creator_folder / "Images"
                image_count = _count_files_fast(images_folder)

                display_manager.activate_download_ui(image_count, "Images")

                image_results, invalid_images, incorrect_images = (
                    validator.scan_creator_images(
                        creator_folder,
                        config.image_extensions,
                        display_manager,
                        summary.images.checked,
                        0,
                        summary.images.invalid,
                        summary.images.incorrect,
                        video_extensions=config.video_extensions,
                        apply_corrections=parsed.repair,
                    )
                )

                summary.images.checked += len(image_results)
                summary.images.invalid += invalid_images
                summary.images.incorrect += incorrect_images
                display_manager.complete_video_verification("Images")

            if should_verify_videos:
                videos_folder = creator_folder / "Videos"
                video_count = _count_files_fast(
                    videos_folder, config.video_extensions
                )

                display_manager.activate_download_ui(video_count, "Videos")

                video_results, invalid_videos, incorrect_videos = (
                    validator.scan_creator_videos(
                        creator_folder,
                        config.video_extensions,
                        display_manager,
                        summary.videos.checked,
                        0,
                        summary.videos.invalid,
                        summary.videos.incorrect,
                        image_extensions=config.image_extensions,
                        apply_corrections=parsed.repair,
                        media_type="Videos",
                    )
                )

                summary.videos.checked += len(video_results)
                summary.videos.invalid += invalid_videos
                summary.videos.incorrect += incorrect_videos
                display_manager.complete_video_verification("Videos")

                # Track invalid videos for report
                if invalid_videos > 0:
                    invalid_entry_list: list[InvalidVideoEntry] = []
                    for filename, (is_valid, frames, duration) in (
                        video_results.items()
                    ):
                        if not is_valid:
                            creator_path = (
                                output_folder
                                / current_creator_name
                                / "Videos"
                                / filename
                            )
                            invalid_entry_list.append({
                                "filename": filename,
                                "path": str(creator_path.resolve()),
                                "frames": frames,
                                "duration": duration,
                            })
                    if invalid_entry_list:
                        invalids[current_creator_name] = invalid_entry_list

            display_manager.complete_creator()

        except Exception as e:
            summary.creators_failed += 1
            failed_creator_list.append((current_creator_name, str(e)))
            log_exception(e, f"Failed to verify creator {current_creator_name}")

    display_manager.update_global_progress(total_creators)
    display_manager.stop(print_final_state=False)
    display_manager.console.clear()

    # Get corrections from centralized tracker
    extension_tracker = get_extension_tracker()

    result = VerifyOperationSummary(
        operation_type=OperationType.VERIFY,
        successful=len(creators_to_scan) - summary.creators_failed,
        failed=summary.creators_failed,
        total=len(creators_to_scan),
        warnings=[],
        creators_processed=summary.creators_processed,
        creators_failed=summary.creators_failed,
        images_total=summary.images.checked,
        images_invalid=summary.images.invalid,
        images_incorrect=summary.images.incorrect,
        videos_total=summary.videos.checked,
        videos_invalid=summary.videos.invalid,
        videos_incorrect=summary.videos.incorrect,
        extension_corrections=extension_tracker.get_all_corrections(),
        display_manager=display_manager,
        failed_creators_list=failed_creator_list,
        invalids=invalids,
        repair_manager=RepairManager(),
    )

    return result
