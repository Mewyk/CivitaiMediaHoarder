"""Utility modules for the Civitai Media Hoarder."""

from utilities.debug_logger import buffer as debug_buffer
from utilities.debug_logger import finalize as finalize_debug
from utilities.debug_logger import get_logger, init_debug, register_consumer
from utilities.extension_handler import ExtensionHandler
from utilities.file_matcher import FileMatcherUtil
from utilities.logging_utils import log_exception, safe_log, safe_operation
from utilities.media import (
    get_extension_from_url,
    media_type_from_extension,
    safe_filename_from_url,
    update_video_url,
)
from utilities.network import request_with_retries, UserNotFoundError
from utilities.video_validator import VideoValidator

__all__ = [
    "debug_buffer",
    "ExtensionHandler",
    "FileMatcherUtil",
    "finalize_debug",
    "get_extension_from_url",
    "get_logger",
    "init_debug",
    "log_exception",
    "media_type_from_extension",
    "register_consumer",
    "request_with_retries",
    "safe_filename_from_url",
    "safe_log",
    "safe_operation",
    "update_video_url",
    "UserNotFoundError",
    "VideoValidator",
]
