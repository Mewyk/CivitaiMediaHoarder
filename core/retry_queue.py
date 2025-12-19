"""Retry queue for failed downloads.

This module provides a threaded retry mechanism for downloads that fail
due to timeouts or transient errors. Failed downloads are queued and
retried in a background thread.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from models.types import ApiItem
from utilities.logging_utils import safe_log

if TYPE_CHECKING:
    from core.display_manager import DisplayManager


@dataclass
class FailedDownload:
    """Represents a failed download item pending retry."""

    item: ApiItem
    creator: str
    url: str
    out_path: Path
    retry_count: int = 0
    last_error: str = ""


@dataclass
class RetryQueueConfig:
    """Configuration for the retry queue."""

    max_retries: int = 3
    retry_delay_sec: float = 5.0
    download_timeout: int = 60


class RetryQueue:
    """Thread-safe queue for retrying failed downloads.

    Failed downloads are added to the queue and processed by a background
    thread. If a download fails again, it's moved to the back of the queue
    until it reaches the max retry limit.
    """

    def __init__(
        self,
        config: RetryQueueConfig,
        download_func: Callable[[ApiItem, str, Path], bool],
        display_manager: DisplayManager | None = None,
    ):
        """Initialize the retry queue.

        Args:
            config: Queue configuration.
            download_func: Function to call for download attempts.
                          Should return True on success, False on failure.
            display_manager: Optional display manager for progress updates.
        """
        self._config = config
        self._download_func = download_func
        self._display_manager = display_manager

        self._queue: deque[FailedDownload] = deque()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

        self._successful_retries: int = 0
        self._permanently_failed: list[FailedDownload] = []
        self._is_running: bool = False

    def add(
        self,
        item: ApiItem,
        creator: str,
        url: str,
        out_path: Path,
        error: str = "",
    ) -> None:
        """Add a failed download to the retry queue.

        Args:
            item: The API item that failed.
            creator: Creator username.
            url: Download URL.
            out_path: Target output path.
            error: Error message from the failed attempt.
        """
        failed = FailedDownload(
            item=item,
            creator=creator,
            url=url,
            out_path=out_path,
            retry_count=1,
            last_error=error,
        )

        with self._lock:
            self._queue.append(failed)

        safe_log(
            f"Added to retry queue: {out_path.name} "
            f"(attempt 1/{self._config.max_retries})\n",
            level="WARNING",
        )

    def start(self) -> None:
        """Start the background retry worker thread."""
        if self._is_running:
            return

        self._stop_event.clear()
        self._is_running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="RetryQueueWorker",
            daemon=True,
        )
        self._worker_thread.start()

        safe_log("Retry queue worker started\n", level="INFO")

    def stop(self, wait: bool = True, timeout: float = 30.0) -> None:
        """Stop the background retry worker thread.

        Args:
            wait: If True, wait for the worker to finish processing.
            timeout: Maximum time to wait in seconds.
        """
        if not self._is_running:
            return

        self._stop_event.set()

        if wait and self._worker_thread is not None:
            self._worker_thread.join(timeout=timeout)

        self._is_running = False

        safe_log("Retry queue worker stopped\n", level="INFO")

    def wait_for_completion(self, timeout: float | None = None) -> bool:
        """Wait for all queued items to be processed.

        Args:
            timeout: Maximum time to wait in seconds. None means wait forever.

        Returns:
            True if queue is empty, False if timed out.
        """
        start_time = time.time()

        while True:
            with self._lock:
                if len(self._queue) == 0:
                    return True

            if timeout is not None and (time.time() - start_time) >= timeout:
                return False

            time.sleep(0.1)

    @property
    def pending_count(self) -> int:
        """Get the number of items pending retry."""
        with self._lock:
            return len(self._queue)

    @property
    def successful_retries(self) -> int:
        """Get the number of successful retries."""
        return self._successful_retries

    @property
    def permanently_failed(self) -> list[FailedDownload]:
        """Get the list of permanently failed downloads."""
        return self._permanently_failed.copy()

    def get_stats(self) -> dict[str, int]:
        """Get queue statistics.

        Returns:
            Dictionary with 'pending', 'successful', and 'failed' counts.
        """
        with self._lock:
            pending = len(self._queue)

        return {
            "pending": pending,
            "successful": self._successful_retries,
            "failed": len(self._permanently_failed),
        }

    def _worker_loop(self) -> None:
        """Main worker loop for processing retry queue."""
        while not self._stop_event.is_set():
            item = self._get_next_item()

            if item is None:
                # Queue is empty, wait a bit before checking again
                time.sleep(0.5)
                continue

            self._process_item(item)

    def _get_next_item(self) -> FailedDownload | None:
        """Get the next item from the queue.

        Returns:
            Next FailedDownload or None if queue is empty.
        """
        with self._lock:
            if len(self._queue) == 0:
                return None
            return self._queue.popleft()

    def _process_item(self, item: FailedDownload) -> None:
        """Process a single retry item.

        Args:
            item: The FailedDownload to retry.
        """
        safe_log(
            f"Retrying download: {item.out_path.name} "
            f"(attempt {item.retry_count}/{self._config.max_retries})\n",
            level="INFO",
        )

        # Wait before retrying to avoid hammering the server
        time.sleep(self._config.retry_delay_sec)

        # Attempt the download
        try:
            success = self._download_func(item.item, item.creator, item.out_path)
        except Exception as e:
            success = False
            item.last_error = str(e)

        if success:
            self._successful_retries += 1
            safe_log(f"Retry successful: {item.out_path.name}\n", level="INFO")
        else:
            # Failed again
            item.retry_count += 1

            if item.retry_count >= self._config.max_retries:
                # Max retries reached, add to permanently failed
                self._permanently_failed.append(item)
                safe_log(
                    f"Download permanently failed after {item.retry_count} attempts: "
                    f"{item.out_path.name}\n",
                    level="ERROR",
                )
            else:
                # Add back to the end of the queue
                with self._lock:
                    self._queue.append(item)
                safe_log(
                    f"Re-queued for retry: {item.out_path.name} "
                    f"(will be attempt {item.retry_count + 1}/{self._config.max_retries})\n",
                    level="WARNING",
                )
