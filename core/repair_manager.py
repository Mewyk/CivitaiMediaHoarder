"""Video repair management for corrupted video detection and redownloading."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from rich.panel import Panel
from rich.prompt import Confirm

from core.display_manager import DisplayManager
from core.downloader import MediaDownloader
from core.file_manager import FileManager
from models.config import AppConfig
from models.types import (
    ApiItem,
    CIVITAI_CDN_ID,
    CIVITAI_IMAGE_API_BASE,
    CIVITAI_VIDEO_PARAMS,
    InvalidVideoEntry,
    InvalidVideosReport,
)
from utilities.extension_handler import ExtensionHandler


class RepairManager:
    """Manages invalid video reports and repair operations."""

    REPORT_FILENAME = "InvalidVideos.json"

    def __init__(self) -> None:
        """Initialize RepairManager."""
        self.extension_handler = ExtensionHandler()
    
    @staticmethod
    def build_download_url(filename: str) -> str:
        """
        Build Civitai download URL from filename.
        
        URL Format: {ImageApiBaseUrl}/{CdnId}/{MediaApiId}/{Parameters}/{MediaApiId}.{Extension}
        
        Example:
        https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/80b4f36f-7cbb-4a96-a05a-8d1b060d8a7a/original-video=true,quality=100/80b4f36f-7cbb-4a96-a05a-8d1b060d8a7a.mp4
        
        Args:
            filename: The video filename (e.g., "80b4f36f-7cbb-4a96-a05a-8d1b060d8a7a.mp4")
            
        Returns:
            Full download URL
        """
        file_path = Path(filename)
        media_api_id = file_path.stem
        file_extension = file_path.suffix

        url = (
            f"{CIVITAI_IMAGE_API_BASE}/{CIVITAI_CDN_ID}/{media_api_id}/"
            f"{CIVITAI_VIDEO_PARAMS}/{media_api_id}{file_extension}"
        )
        
        return url
    
    def load_report(self, report_path: Path) -> InvalidVideosReport | None:
        """
        Load invalid videos report from JSON file.
        
        Args:
            report_path: Path to the report file
            
        Returns:
            Report dictionary, or None if file doesn't exist or is invalid
        """
        if not report_path.exists():
            return None
        
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                raw_data: object = json.load(f)

                if not isinstance(raw_data, dict):
                    return None

                data_dict: dict[str, object] = cast(dict[str, object], raw_data)

                if "generated_at" not in data_dict or "creators" not in data_dict:
                    return None

                generated_at_field: object = data_dict["generated_at"]
                if not isinstance(generated_at_field, str):
                    return None

                creators_field: object = data_dict["creators"]
                if not isinstance(creators_field, dict):
                    return None

                creators_dict: dict[str, object] = cast(dict[str, object], creators_field)

                for creator_videos_raw in creators_dict.values():
                    if not isinstance(creator_videos_raw, list):
                        return None

                return cast(InvalidVideosReport, data_dict)
        except (json.JSONDecodeError, IOError):
            return None
    
    def save_report(
        self,
        invalids: dict[str, list[InvalidVideoEntry]],
        report_path: Path,
        auto_yes: bool
    ) -> bool:
        """
        Save invalid videos report to JSON file.
        
        Args:
            invalids: Dictionary mapping creator -> list of invalid video entries
            report_path: Path to save the report
            auto_yes: If True, automatically overwrite existing report
            
        Returns:
            True if report was saved, False if user declined overwrite
        """
        if report_path.exists() and not auto_yes:
            while True:
                response = input(
                    f"\n{self.REPORT_FILENAME} already exists. Overwrite? (yes/no): "
                ).strip().lower()
                if response in ["yes", "y"]:
                    break
                elif response in ["no", "n"]:
                    print("Report not saved.")
                    return False
                else:
                    print("Please enter 'yes' or 'no'.")

        report: InvalidVideosReport = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "creators": invalids
        }

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving report: {e}")
            return False
    
    def repair_videos(
        self,
        report_path: Path,
        config: AppConfig,
        auto_yes: bool,
        file_manager: FileManager,
        downloader: MediaDownloader,
        display_manager: DisplayManager
    ) -> tuple[int, int]:
        """
        Repair invalid videos by deleting and redownloading them.
        
        After redownloading, validates each file's actual format and corrects extension if needed.
        This ensures repaired files have correct extensions even if API returned incorrect ones.
        
        Args:
            report_path: Path to the invalid videos report
            config: Application configuration
            auto_yes: If True, automatically confirm repair
            file_manager: FileManager instance
            downloader: MediaDownloader instance
            display_manager: DisplayManager for output
            
        Returns:
            Tuple of (total_attempted, total_succeeded)
        """
        report = self.load_report(report_path)
        if report is None:
            display_manager.console.print(
                f"Error: No {self.REPORT_FILENAME} found. Run --verify-videos first.",
                style="red"
            )
            return (0, 0)

        creators_data: dict[str, list[InvalidVideoEntry]] = report["creators"]

        if not creators_data:
            display_manager.console.print("No invalid videos found in report.")
            return (0, 0)

        total_videos = 0
        for videos_list in creators_data.values():
            total_videos += len(videos_list)

        if not auto_yes:
            content = f"Found {total_videos} invalid video(s) across {len(creators_data)} creator(s).\n\n[orange3]This will delete corrupted files and redownload them.[/orange3]"
            display_manager.console.print()
            display_manager.console.print(Panel(
                content, 
                title="[bold orange3]⚠ Repair Confirmation", 
                border_style="orange3", 
                padding=(1, 2)
            ))
            
            if not Confirm.ask("[orange3]Proceed with repair?[/orange3]"):
                display_manager.console.print("[dim]Repair cancelled.[/dim]")
                return (0, 0)

        display_manager.console.print()
        display_manager.set_header_progress("Video Repair Process", 0, total_videos)
        display_manager.start()

        total_items_processed = 0
        total_succeeded = 0

        for creator_name, invalid_videos in creators_data.items():
            display_manager.start_creator(creator_name)
            display_manager.start_repair_section(len(invalid_videos))

            display_manager.start_removal_phase()
            removed_count = 0
            
            for video_entry in invalid_videos:
                video_path_str: str = video_entry["path"]
                video_path = Path(video_path_str).resolve()
                
                try:
                    if video_path.exists():
                        video_path.unlink()
                except OSError:
                    pass
                
                removed_count += 1
                display_manager.update_removal_progress(removed_count)
            
            display_manager.complete_removal_phase()

            display_manager.start_download_phase()
            downloaded_count = 0

            for video_entry in invalid_videos:
                filename: str = video_entry["filename"]
                download_url = self.build_download_url(filename)
                item: ApiItem = {"url": download_url}

                try:
                    downloads = downloader.download_files(
                        [item],
                        creator_name,
                        display_manager
                    )
                    total_downloaded, _images_dl, _videos_dl = downloads
                    if total_downloaded > 0:
                        total_succeeded += 1
                except Exception:
                    pass

                downloaded_count += 1
                total_items_processed += 1
                display_manager.update_download_progress_repair(downloaded_count)
                display_manager.set_header_progress("Video Repair Process", total_items_processed, total_videos)
            
            display_manager.complete_download_phase()
            display_manager.complete_repair_section()

        display_manager.set_header_progress("Repair Complete", total_videos, total_videos)
        display_manager.stop()

        for creator_name, invalid_videos in creators_data.items():
            creator_count = len(invalid_videos)
            display_manager.console.print(f"[cyan]{creator_name}: {creator_count} video(s) processed[/cyan]")

        summary_panel_content = "\n".join([f"Total repaired: {total_succeeded}/{total_videos}"])
        display_manager.console.print(Panel(
            summary_panel_content,
            title="[bold cyan]Repair | Summary",
            title_align="left",
            border_style="cyan",
            padding=(1, 2)
        ))

        if total_succeeded == total_videos and total_videos > 0:
            try:
                report_path.unlink()
                display_manager.console.print(f"[green]{self.REPORT_FILENAME} removed.[/green]")
            except OSError as e:
                display_manager.console.print(f"[orange3]Warning: Could not delete {self.REPORT_FILENAME}: {e}[/orange3]")
        elif total_videos > 0:
            display_manager.console.print(f"[orange3]{self.REPORT_FILENAME} kept (some repairs failed).[/orange3]")
        
        return (total_videos, total_succeeded)
