"""Factory for creating and configuring core components.

This module provides centralized component creation to eliminate duplicate
initialization code across handlers and main.py.
"""

from __future__ import annotations

import signal
from dataclasses import dataclass
from types import FrameType

from api.client import CivitaiClient
from core.display_manager import DisplayManager
from core.downloader import MediaDownloader
from core.file_manager import FileManager
from core.processor import CreatorProcessor
from models.config import AppConfig
from utilities.debug_logger import get_logger, register_consumer


@dataclass
class CoreComponents:
    """Container for core application components.

    Attributes:
        api_client: Client for Civitai API interactions.
        file_manager: Manager for file I/O operations.
        downloader: Handler for media downloads.
        display_manager: Manager for console output.
        processor: Orchestrator for creator processing.
    """

    api_client: CivitaiClient
    file_manager: FileManager
    downloader: MediaDownloader
    display_manager: DisplayManager
    processor: CreatorProcessor


class ComponentFactory:
    """Factory for creating configured application components."""

    @staticmethod
    def create_api_client(config: AppConfig) -> CivitaiClient:
        """Create a configured CivitaiClient.

        Args:
            config: Application configuration.

        Returns:
            Configured CivitaiClient instance.
        """
        return CivitaiClient(
            api_key=config.api_key,
            request_timeout=config.request_timeout,
            max_retries=config.max_retries,
            retry_backoff_sec=config.retry_backoff_sec,
        )

    @staticmethod
    def create_file_manager(config: AppConfig) -> FileManager:
        """Create a configured FileManager.

        Args:
            config: Application configuration.

        Returns:
            Configured FileManager instance.
        """
        return FileManager(
            output_folder=config.default_output,
            image_extensions=config.image_extensions,
            video_extensions=config.video_extensions,
        )

    @staticmethod
    def create_downloader(
        config: AppConfig,
        file_manager: FileManager,
    ) -> MediaDownloader:
        """Create a configured MediaDownloader.

        Args:
            config: Application configuration.
            file_manager: FileManager instance.

        Returns:
            Configured MediaDownloader instance.
        """
        return MediaDownloader(
            file_manager=file_manager,
            video_extensions=config.video_extensions,
            image_extensions=config.image_extensions,
            download_timeout=config.download_timeout,
            max_retries=config.max_retries,
            retry_backoff_sec=config.retry_backoff_sec,
            rate_limit=config.rate_limit,
            memory_threshold_bytes=config.memory_threshold_bytes,
            lock_policy=config.download_lock_policy,
        )

    @staticmethod
    def create_display_manager(enable_debug: bool = False) -> DisplayManager:
        """Create a configured DisplayManager.

        Args:
            enable_debug: Whether to enable the debug panel.

        Returns:
            Configured DisplayManager instance.
        """
        display_manager = DisplayManager()
        if enable_debug and get_logger() is not None:
            display_manager.enable_debug_panel(True)
            register_consumer(display_manager.debug_log)
        return display_manager

    @staticmethod
    def create_processor(
        api_client: CivitaiClient,
        file_manager: FileManager,
        downloader: MediaDownloader,
        display_manager: DisplayManager,
    ) -> CreatorProcessor:
        """Create a configured CreatorProcessor.

        Args:
            api_client: CivitaiClient instance.
            file_manager: FileManager instance.
            downloader: MediaDownloader instance.
            display_manager: DisplayManager instance.

        Returns:
            Configured CreatorProcessor instance.
        """
        return CreatorProcessor(
            api_client=api_client,
            file_manager=file_manager,
            downloader=downloader,
            display_manager=display_manager,
        )

    @classmethod
    def create_all(
        cls,
        config: AppConfig,
        enable_debug: bool = False,
    ) -> CoreComponents:
        """Create all core components with proper configuration.

        This is the main entry point for creating a complete set of
        configured components for processing creators.

        Args:
            config: Application configuration.
            enable_debug: Whether to enable debug logging in display.

        Returns:
            CoreComponents containing all configured instances.
        """
        api_client = cls.create_api_client(config)
        file_manager = cls.create_file_manager(config)
        downloader = cls.create_downloader(config, file_manager)
        display_manager = cls.create_display_manager(enable_debug)
        processor = cls.create_processor(
            api_client, file_manager, downloader, display_manager
        )

        components = CoreComponents(
            api_client=api_client,
            file_manager=file_manager,
            downloader=downloader,
            display_manager=display_manager,
            processor=processor,
        )
        return components


def install_sigint_handler(display_manager: DisplayManager) -> None:
    """Install a SIGINT handler that stops the display manager gracefully.

    Args:
        display_manager: The DisplayManager to stop on interrupt.
    """

    def _sigint_handler(sig: int, frame: FrameType | None) -> None:
        try:
            display_manager.stop()
        except Exception:
            pass
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _sigint_handler)
