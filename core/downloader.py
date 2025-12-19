"""Media download functionality with progress tracking."""

from __future__ import annotations

import os
import random
import time
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

from core.extension_tracker import get_extension_tracker
from core.file_manager import FileManager
from core.retry_queue import RetryQueue, RetryQueueConfig
from models.types import ApiItem, DEFAULT_MEMORY_THRESHOLD_BYTES, LockPolicy
from utilities.extension_handler import ExtensionHandler
from utilities.logging_utils import log_exception, safe_log
from utilities.media import media_type_from_extension, update_video_url
from utilities.network import request_with_retries

msvcrt: ModuleType | None = None
try:
    import msvcrt as _msvcrt

    msvcrt = _msvcrt
except ImportError:
    msvcrt = None

fcntl: ModuleType | None = None
try:
    import fcntl as _fcntl

    fcntl = _fcntl
except ImportError:
    fcntl = None

if TYPE_CHECKING:
    from core.display_manager import DisplayManager


class MediaDownloader:
    """Handles downloading of media files with progress tracking."""

    def __init__(
        self,
        file_manager: FileManager,
        video_extensions: list[str],
        image_extensions: list[str],
        download_timeout: int = 60,
        max_retries: int = 3,
        retry_backoff_sec: int = 2,
        rate_limit: bool = False,
        memory_threshold_bytes: int = DEFAULT_MEMORY_THRESHOLD_BYTES,
        lock_policy: LockPolicy = LockPolicy.BEST_EFFORT,
        enable_retry_queue: bool = True,
    ) -> None:
        """Initialize MediaDownloader.

        Args:
            file_manager: FileManager instance for file operations.
            video_extensions: List of valid video file extensions.
            image_extensions: List of valid image file extensions.
            download_timeout: Download timeout in seconds.
            max_retries: Maximum number of retry attempts.
            retry_backoff_sec: Backoff time between retries in seconds.
            rate_limit: Whether to apply rate limiting delays between downloads.
            memory_threshold_bytes: Threshold for in-memory buffering (bytes).
            lock_policy: File locking policy for concurrent downloads.
            enable_retry_queue: Whether to use background retry queue for failed downloads.
        """
        self.file_manager = file_manager
        self.video_extensions = video_extensions
        self.image_extensions = image_extensions
        self.extension_handler = ExtensionHandler()
        self.extension_tracker = get_extension_tracker()
        self.downloaded_extensions: dict[str, int] = {}
        self.download_timeout = download_timeout
        self.max_retries = max_retries
        self.retry_backoff_sec = retry_backoff_sec
        self.rate_limit = rate_limit
        self.memory_threshold_bytes = memory_threshold_bytes
        self.lock_policy = lock_policy
        self.headers = {"User-Agent": "CivitaiFetcher/2.0"}

        # Initialize retry queue if enabled
        self._retry_queue: RetryQueue | None = None
        self._enable_retry_queue = enable_retry_queue
        if enable_retry_queue:
            retry_config = RetryQueueConfig(
                max_retries=max_retries,
                retry_delay_sec=float(retry_backoff_sec),
                download_timeout=download_timeout,
            )
            self._retry_queue = RetryQueue(
                config=retry_config,
                download_func=self._retry_download,
            )
    
    def _retry_download(self, item: ApiItem, creator: str, out_path: Path) -> bool:
        """Attempt to download a single file for retry queue.

        Args:
            item: API item with URL
            creator: Creator username
            out_path: Output path for the file

        Returns:
            True if download succeeded, False otherwise.
        """
        url = item.get("url")
        if not url:
            return False

        download_url = update_video_url(url, self.video_extensions)

        try:
            resp = request_with_retries(
                url=download_url,
                headers=self.headers,
                params=None,
                stream=True,
                timeout=(30, self.download_timeout),
                max_retries=1,  # Single attempt for retry queue
                retry_backoff_sec=self.retry_backoff_sec,
            )

            # Note: Content-Length is checked by request_with_retries
            # but not needed here for retry downloads

            out_dir = out_path.parent
            out_dir.mkdir(parents=True, exist_ok=True)

            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Validate and correct extension
            try:
                corrected_path = self.extension_handler.validate_and_correct_file(
                    out_path,
                    self.image_extensions,
                    self.video_extensions,
                    apply_rename=True,
                )
                if corrected_path != out_path:
                    self.extension_tracker.record_correction(
                        str(out_path),
                        out_path.suffix.lower(),
                        corrected_path.suffix.lower(),
                    )
            except OSError as e:
                log_exception(e, "Extension validation failed during retry download")

            return True

        except Exception as e:
            # Clean up partial file
            try:
                if out_path.exists():
                    out_path.unlink()
            except OSError:
                pass
            log_exception(e, f"Retry download failed for {download_url}")
            return False
    
    def start_retry_queue(self) -> None:
        """Start the background retry queue worker."""
        if self._retry_queue is not None:
            self._retry_queue.start()

    def stop_retry_queue(self, wait: bool = True) -> None:
        """Stop the background retry queue worker.

        Args:
            wait: If True, wait for queue to finish processing.
        """
        if self._retry_queue is not None:
            self._retry_queue.stop(wait=wait)

    def wait_for_retries(self, timeout: float | None = None) -> bool:
        """Wait for all retry queue items to complete.

        Args:
            timeout: Maximum time to wait in seconds.

        Returns:
            True if all retries completed, False if timed out.
        """
        if self._retry_queue is None:
            return True
        return self._retry_queue.wait_for_completion(timeout=timeout)

    def get_retry_stats(self) -> dict[str, int]:
        """Get statistics from the retry queue.

        Returns:
            Dictionary with 'pending', 'successful', and 'failed' counts.
        """
        if self._retry_queue is None:
            return {"pending": 0, "successful": 0, "failed": 0}
        return self._retry_queue.get_stats()
    
    def download_files(
        self,
        items: list[ApiItem],
        creator: str,
        display_manager: DisplayManager,
    ) -> tuple[int, int, int]:
        """Download files for a list of items with post-download extension validation.

        After each successful download, validates the actual file type using magic bytes
        and corrects the extension if needed. This ensures files downloaded with incorrect
        extensions (e.g., WebM file with .mp4 extension) are automatically corrected.

        Args:
            items: List of item dictionaries with URLs
            creator: Creator username
            display_manager: Display manager for progress updates

        Returns:
            Tuple of (total_downloaded, images_downloaded, videos_downloaded)
        """
        successful_downloads = 0
        images_downloaded = 0
        videos_downloaded = 0

        for item in items:
            url = item.get("url")
            if not url:
                display_manager.update_download_progress(successful_downloads)
                continue

            download_url = update_video_url(url, self.video_extensions)

            # Determine media type for logging
            file_ext = (
                download_url.rsplit(".", 1)[-1].lower() if "." in download_url else ""
            )
            if f".{file_ext}" in [ext.lower() for ext in self.video_extensions]:
                media_type_label = "video"
            elif f".{file_ext}" in [ext.lower() for ext in self.image_extensions]:
                media_type_label = "image"
            else:
                media_type_label = "media"

            safe_log(f"Preparing {media_type_label} for download\n", level="INFO")
            out_path = self.file_manager.get_output_path(creator, download_url)

            if out_path.exists():
                display_manager.update_download_progress(successful_downloads)
                if self.rate_limit:
                    time.sleep(random.uniform(0.1, 0.2))
                continue

            # Download strategy: buffer small files in memory, stream large files to disk
            try:
                resp = request_with_retries(
                    url=download_url,
                    headers=self.headers,
                    params=None,
                    stream=True,
                    timeout=(30, self.download_timeout),
                    max_retries=self.max_retries,
                    retry_backoff_sec=self.retry_backoff_sec,
                )

                # Decide buffering strategy based on Content-Length header
                content_length = None
                try:
                    cl = resp.headers.get("Content-Length")
                    if cl is not None:
                        content_length = int(cl)
                except (ValueError, TypeError):
                    content_length = None

                if (
                    content_length is not None
                    and content_length <= self.memory_threshold_bytes
                ):
                    buf = bytearray()
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            buf.extend(chunk)

                    try:
                        out_dir = out_path.parent
                        out_dir.mkdir(parents=True, exist_ok=True)
                        with open(out_path, "wb") as f:
                            try:
                                f.write(buf)
                            except KeyboardInterrupt:
                                try:
                                    f.flush()
                                except OSError:
                                    pass
                                raise
                    finally:
                        del buf

                    try:
                        corrected_path = self.extension_handler.validate_and_correct_file(
                            out_path,
                            self.image_extensions,
                            self.video_extensions,
                            apply_rename=True,
                        )
                        if corrected_path != out_path:
                            self.extension_tracker.record_correction(
                                str(out_path),
                                out_path.suffix.lower(),
                                corrected_path.suffix.lower(),
                            )
                            out_path = corrected_path
                    except OSError as e:
                        log_exception(e, "Extension validation failed")

                    ext = out_path.suffix.lower()
                    self.downloaded_extensions[ext] = (
                        self.downloaded_extensions.get(ext, 0) + 1
                    )
                else:
                    out_dir = out_path.parent
                    out_dir.mkdir(parents=True, exist_ok=True)

                    f = open(out_path, "wb")
                    lock_acquired = False
                    try:
                        try:
                            if msvcrt is not None:
                                if self.lock_policy == LockPolicy.BLOCK:
                                    msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                                    lock_acquired = True
                                elif self.lock_policy == LockPolicy.FAIL:
                                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                                    lock_acquired = True
                                else:
                                    try:
                                        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                                        lock_acquired = True
                                    except OSError:
                                        lock_acquired = False
                            elif fcntl is not None:
                                if self.lock_policy == LockPolicy.BLOCK:
                                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                                    lock_acquired = True
                                elif self.lock_policy == LockPolicy.FAIL:
                                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                                    lock_acquired = True
                                else:
                                    try:
                                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                                        lock_acquired = True
                                    except OSError:
                                        lock_acquired = False
                        except OSError:
                            pass

                        if self.lock_policy == LockPolicy.FAIL and not lock_acquired:
                            raise RuntimeError(
                                "Failed to acquire lock for file and policy is 'fail'"
                            )

                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                try:
                                    f.write(chunk)
                                except KeyboardInterrupt:
                                    try:
                                        f.flush()
                                    except OSError:
                                        pass
                                    raise
                        try:
                            f.flush()
                            os.fsync(f.fileno())
                        except OSError:
                            pass
                    finally:
                        try:
                            if lock_acquired:
                                try:
                                    if msvcrt is not None:
                                        f.seek(0)
                                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                                    elif fcntl is not None:
                                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                                except OSError:
                                    pass
                        finally:
                            try:
                                f.close()
                            except OSError:
                                pass

                        try:
                            corrected_path = (
                                self.extension_handler.validate_and_correct_file(
                                    out_path,
                                    self.image_extensions,
                                    self.video_extensions,
                                    apply_rename=True,
                                )
                            )
                            if corrected_path != out_path:
                                self.extension_tracker.record_correction(
                                    str(out_path),
                                    out_path.suffix.lower(),
                                    corrected_path.suffix.lower(),
                                )
                                out_path = corrected_path
                        except OSError as e:
                            log_exception(e, "Extension validation failed")

                        ext = out_path.suffix.lower()
                        self.downloaded_extensions[ext] = (
                            self.downloaded_extensions.get(ext, 0) + 1
                        )

                file_extension = out_path.suffix.lower()
                media_type = media_type_from_extension(
                    file_extension,
                    self.image_extensions,
                    self.video_extensions,
                )
                safe_log(
                    f"Downloaded file: {out_path} media_type={media_type}\n",
                    level="INFO",
                )
                if media_type == "Images":
                    images_downloaded += 1
                elif media_type == "Videos":
                    videos_downloaded += 1

                successful_downloads += 1

                if media_type == "Images":
                    display_manager.update_verification_progress(
                        checked=images_downloaded,
                        invalid=0,
                        media_type="Images",
                    )
                elif media_type == "Videos":
                    display_manager.update_verification_progress(
                        checked=videos_downloaded,
                        invalid=0,
                        media_type="Videos",
                    )
            except KeyboardInterrupt:
                try:
                    if out_path.exists():
                        out_path.unlink()
                except OSError:
                    pass
                safe_log(
                    f"Download interrupted by user for url={url}\n", level="WARNING"
                )
                raise
            except Exception as e:
                try:
                    if out_path.exists():
                        out_path.unlink()
                except OSError:
                    pass

                error_msg = str(e)
                safe_log(
                    f"Download failed for url={download_url}: {error_msg}\n",
                    level="ERROR",
                )

                # Add to retry queue if enabled
                if self._retry_queue is not None and self._enable_retry_queue:
                    self._retry_queue.add(
                        item=item,
                        creator=creator,
                        url=download_url,
                        out_path=out_path,
                        error=error_msg,
                    )
                continue

            display_manager.update_download_progress(successful_downloads)

            try:
                self.file_manager.invalidate_folder_cache(out_path.parent)
            except OSError as e:
                log_exception(e, "Failed to invalidate folder cache")

            # Apply rate limiting if enabled
            if self.rate_limit:
                time.sleep(random.uniform(3, 6))

        return (successful_downloads, images_downloaded, videos_downloaded)
