"""Creator processing orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from api.client import CivitaiClient
from core.downloader import MediaDownloader
from core.file_manager import FileManager
from models.config import MediaTypeConfig
from models.types import ApiItem
from utilities.logging_utils import log_exception, safe_log
from utilities.media import get_extension_from_url, media_type_from_extension
from utilities.network import UserNotFoundError

if TYPE_CHECKING:
    from core.display_manager import DisplayManager


class CreatorProcessor:
    """Orchestrates the processing of a single creator."""

    def __init__(
        self,
        api_client: CivitaiClient,
        file_manager: FileManager,
        downloader: MediaDownloader,
        display_manager: DisplayManager,
    ) -> None:
        """Initialize CreatorProcessor.

        Args:
            api_client: CivitaiClient instance for API requests.
            file_manager: FileManager instance for file operations.
            downloader: MediaDownloader instance for downloading media.
            display_manager: DisplayManager instance for progress output.
        """
        self.api_client = api_client
        self.file_manager = file_manager
        self.downloader = downloader
        self.display_manager = display_manager

    def _count_media_types(self, items: list[ApiItem]) -> tuple[int, int]:
        """Count images and videos in items list.

        Args:
            items: List of item dictionaries with URLs

        Returns:
            Tuple of (images_count, videos_count)
        """
        images_count = 0
        videos_count = 0

        for item in items:
            url = item.get("url")
            if not url:
                continue

            ext = get_extension_from_url(url)
            media_type = media_type_from_extension(
                ext,
                self.file_manager.image_extensions,
                self.file_manager.video_extensions,
            )

            if media_type == "Images":
                images_count += 1
            elif media_type == "Videos":
                videos_count += 1

        return (images_count, videos_count)

    def process_creator(
        self,
        creator: str,
        nsfw: bool,
        media_config: MediaTypeConfig,
        ignore_enabled: bool = True,
        save_metadata: bool = False,
    ) -> tuple[int, int, int, int, int]:
        """Process a single creator: fetch, filter, optionally save metadata, and download.

        Args:
            creator: Creator username
            nsfw: Whether to include NSFW content
            media_config: Media type configuration
            ignore_enabled: If True, use ignore.txt to skip files
            save_metadata: If True, export API data to JSON file

        Returns:
            Tuple of (total_api_items, files_needing_download, files_downloaded,
                     images_downloaded, videos_downloaded)
        """
        self.display_manager.start_creator(creator, media_config)
        safe_log(f"Starting processing creator={creator}\n", level="INFO")

        self.file_manager.ensure_creator_directories(creator)
        self.display_manager.start_api_fetch()

        items = self.api_client.fetch_creator_items(creator, self.display_manager, nsfw)

        safe_log(f"Fetched {len(items)} items for creator={creator}\n", level="INFO")

        page_count = max(1, (len(items) + 99) // 100)
        self.display_manager.complete_api_fetch(page_count, len(items))

        if save_metadata:
            self.file_manager.export_creator_data(items, creator)
            safe_log(f"Exported metadata for creator={creator}\n", level="INFO")

        items_matching_filter = self.file_manager.filter_items_by_media_type(
            items, media_config
        )
        items_needing_download = self.file_manager.filter_existing_files(
            items_matching_filter, creator, ignore_enabled
        )

        safe_log(
            f"Items matching filter={len(items_matching_filter)}, "
            f"needing_download={len(items_needing_download)} for creator={creator}\n",
            level="INFO",
        )

        already_downloaded = len(items_matching_filter) - len(items_needing_download)

        images_needed, videos_needed = self._count_media_types(items_needing_download)

        self.display_manager.activate_download_ui(images_needed, "Images")
        self.display_manager.activate_download_ui(videos_needed, "Videos")

        self.display_manager.start_local_update(
            existing=already_downloaded,
            total=len(items_matching_filter),
            to_download=len(items_needing_download),
        )

        files_downloaded = 0
        images_downloaded = 0
        videos_downloaded = 0

        if len(items_needing_download) > 0:
            # Start retry queue before downloading
            self.downloader.start_retry_queue()

            files_downloaded, images_downloaded, videos_downloaded = (
                self.downloader.download_files(
                    items_needing_download,
                    creator,
                    display_manager=self.display_manager,
                )
            )

            # Wait for any pending retries to complete
            retry_stats = self.downloader.get_retry_stats()
            if retry_stats["pending"] > 0:
                safe_log(
                    f"Waiting for {retry_stats['pending']} pending retries...\n",
                    level="INFO",
                )
                self.downloader.wait_for_retries(timeout=300)  # 5 minute timeout

            # Stop retry queue
            self.downloader.stop_retry_queue(wait=False)

            # Add successful retries to download count
            final_stats = self.downloader.get_retry_stats()
            files_downloaded += final_stats["successful"]

            safe_log(
                f"Downloaded for creator={creator}: files={files_downloaded}, "
                f"images={images_downloaded}, videos={videos_downloaded}\n",
                level="INFO",
            )
            if final_stats["successful"] > 0:
                safe_log(
                    f"Successful retries: {final_stats['successful']}\n", level="INFO"
                )
            if final_stats["failed"] > 0:
                safe_log(
                    f"Permanently failed downloads: {final_stats['failed']}\n",
                    level="WARNING",
                )

        self.display_manager.complete_video_verification("Images")
        self.display_manager.complete_video_verification("Videos")

        self.display_manager.complete_local_update()

        return (
            len(items),
            len(items_needing_download),
            files_downloaded,
            images_downloaded,
            videos_downloaded,
        )

    def process_creators(
        self,
        creators: list[tuple[str, MediaTypeConfig]],
        nsfw: bool,
        auto_purge: bool = False,
        ignore_enabled: bool = True,
        save_metadata: bool = False,
    ) -> tuple[list[str], list[tuple[str, str]], int, int, int, int, int, int, int]:
        """Process multiple creators with aggregate statistics.

        Args:
            creators: List of (username, media_config) tuples
            nsfw: Whether to include NSFW content
            auto_purge: If True, automatically purge deleted users without prompting
            ignore_enabled: If True, use ignore.txt to skip files
            save_metadata: If True, export API data to JSON file for each creator

        Returns:
            Tuple of (deleted_creators, failed_creator_list, successful_creators,
                     failed_creators, total_api_items, total_files_needing_download,
                     total_files_downloaded, total_images_downloaded, total_videos_downloaded)
        """
        if not creators:
            if self.display_manager:
                self.display_manager.print_message("No creators to process.")
            else:
                print("No creators to process.")
            return ([], [], 0, 0, 0, 0, 0, 0, 0)

        total_creators = len(creators)
        successful_creators = 0
        failed_creators = 0
        total_api_items = 0
        total_files_needing_download = 0
        total_files_downloaded = 0
        total_images_downloaded = 0
        total_videos_downloaded = 0

        failed_creator_list: list[tuple[str, str]] = []
        deleted_creators: list[str] = []

        self.display_manager.set_panel_mode(True, total_creators)
        self.display_manager.start()

        for creator_index, (username, media_config) in enumerate(creators, start=1):
            try:
                self.display_manager.update_global_progress(creator_index - 1)

                api_items, needing_download, downloaded, images_dl, videos_dl = (
                    self.process_creator(
                        username, nsfw, media_config, ignore_enabled, save_metadata
                    )
                )
                safe_log(
                    f"Creator processed: {username} api_items={api_items} "
                    f"needing_download={needing_download} downloaded={downloaded}\n",
                    level="INFO",
                )
                successful_creators += 1
                total_api_items += api_items
                total_files_needing_download += needing_download
                total_files_downloaded += downloaded
                total_images_downloaded += images_dl
                total_videos_downloaded += videos_dl
                try:
                    self.display_manager.update_global_downloaded(total_files_downloaded)
                except AttributeError:
                    pass
            except UserNotFoundError:
                failed_creators += 1
                deleted_creators.append(username)
                failed_creator_list.append((username, "User not found"))
                continue
            except Exception as e:
                failed_creators += 1
                failed_creator_list.append((username, str(e)))
                log_exception(e, f"Failed to process creator {username}")
                continue

        self.display_manager.update_global_progress(total_creators)
        self.display_manager.stop(print_final_state=False)

        return (
            deleted_creators,
            failed_creator_list,
            successful_creators,
            failed_creators,
            total_api_items,
            total_files_needing_download,
            total_files_downloaded,
            total_images_downloaded,
            total_videos_downloaded,
        )
