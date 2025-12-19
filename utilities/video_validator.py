"""Video validation utilities using ffprobe to check video integrity."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, cast

from core.extension_tracker import get_extension_tracker
from utilities.extension_handler import ExtensionHandler
from utilities.logging_utils import log_exception

if TYPE_CHECKING:
    from core.display_manager import DisplayManager

IMAGE_CODECS = {"webp", "png", "jpeg", "mjpeg", "gif", "bmp"}
"""Image codecs that indicate a video file contains an image, not video."""


class VideoValidator:
    """Validates video files using ffprobe to check frame count and duration.

    Uses magic byte detection for format verification and ffprobe for video
    integrity validation. Extension corrections are tracked via ExtensionTracker.

    Attributes:
        ffprobe_path: Path to the ffprobe executable.
        extension_handler: Handler for magic byte format detection.
        extension_tracker: Centralized tracker for extension corrections.
    """

    def __init__(self, ffprobe_path: str = "ffprobe"):
        """Initialize VideoValidator.

        Args:
            ffprobe_path: Path to ffprobe executable (defaults to system PATH).
        """
        self.ffprobe_path = ffprobe_path
        self.extension_handler = ExtensionHandler()
        self.extension_tracker = get_extension_tracker()
    
    def get_video_info(self, video_path: Path) -> tuple[int, float, str] | None:
        """Get video information quickly without counting all frames.

        Retrieves duration, codec, and estimated frame count in a single
        ffprobe call. Does NOT use -count_frames, making it much faster.

        Args:
            video_path: Path to the video file.

        Returns:
            Tuple of (estimated_frames, duration, codec_name) or None if failed.
        """
        try:
            result = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=duration,r_frame_rate,nb_frames,codec_name",
                    "-of",
                    "json",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return None

            raw_data: object = json.loads(result.stdout)
            if not isinstance(raw_data, dict):
                return None

            data = cast(dict[str, object], raw_data)
            streams_raw: object = data.get("streams", [])
            if not isinstance(streams_raw, list) or not streams_raw:
                return None

            streams = cast(list[object], streams_raw)
            stream_raw: object = streams[0]
            if not isinstance(stream_raw, dict):
                return None

            stream = cast(dict[str, object], stream_raw)
            codec_name_raw = stream.get("codec_name", "unknown")
            codec_name: str = str(codec_name_raw).lower()

            duration_raw = stream.get("duration")
            if duration_raw is None:
                if codec_name == "vp9":
                    return (0, 0.0, codec_name)
                return None

            if isinstance(duration_raw, (int, float)):
                duration = float(duration_raw)
            elif isinstance(duration_raw, str):
                try:
                    duration = float(duration_raw)
                except ValueError:
                    if codec_name == "vp9":
                        return (0, 0.0, codec_name)
                    return None
            else:
                if codec_name == "vp9":
                    return (0, 0.0, codec_name)
                return None

            nb_frames_raw = stream.get("nb_frames")
            if nb_frames_raw is not None:
                if isinstance(nb_frames_raw, int):
                    return (nb_frames_raw, duration, codec_name)
                elif isinstance(nb_frames_raw, str):
                    try:
                        frames = int(nb_frames_raw)
                        return (frames, duration, codec_name)
                    except (ValueError, TypeError):
                        pass

            r_frame_rate_raw = stream.get("r_frame_rate", "0/1")
            r_frame_rate_str = (
                r_frame_rate_raw if isinstance(r_frame_rate_raw, str) else "0/1"
            )

            # Parse frame rate fraction (e.g., "30000/1001")
            if "/" in r_frame_rate_str:
                try:
                    parts = r_frame_rate_str.split("/")
                    num = float(parts[0])
                    den = float(parts[1])
                    fps = num / den if den != 0 else 0.0
                except (ValueError, IndexError):
                    fps = 0.0
            else:
                try:
                    fps = float(r_frame_rate_str)
                except ValueError:
                    fps = 0.0

            estimated_frames = int(duration * fps) if fps > 0 else 0

            return (estimated_frames, duration, codec_name)

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return None
    
    def validate_image(self, image_path: Path) -> tuple[bool, int, float]:
        """Validate an image file by checking if it's a valid image format.

        For images, we don't check frame count or duration (they don't have those).
        We only verify:
        1. File exists and is readable
        2. File can be detected as a valid image format using magic bytes

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (is_valid, frames, duration)
            - is_valid: True if image is a valid format, False otherwise
            - frames: Always 1 (images are treated as single-frame)
            - duration: Always 0.0 (images don't have duration)
        """
        if not image_path.exists() or not image_path.is_file():
            return (False, 0, 0.0)

        try:
            detection = self.extension_handler.detect_format(image_path)
            if detection is None:
                return (False, 0, 0.0)

            media_type, _format_name, _detected_ext = detection
            return (media_type == "image", 1, 0.0)

        except (IOError, OSError) as e:
            log_exception(e, f"Failed to validate image {image_path}")
            return (False, 0, 0.0)

    def validate_video(self, video_path: Path) -> tuple[bool, int, float]:
        """Validate a video file by checking frame count and duration.

        This method uses a fast validation approach that:
        1. Gets video info in a single ffprobe call (no frame counting)
        2. Checks for valid duration (missing duration = corrupt/invalid)
        3. Detects image codecs masquerading as videos (e.g., webp in mp4)
        4. Estimates frame count from duration × fps

        Logic:
        - If video info cannot be retrieved, video is invalid
        - If duration is 0 or codec is an image format, video is invalid
        - If estimated frames <= 1, video is invalid
        - Otherwise, video is valid

        Args:
            video_path: Path to the video file

        Returns:
            Tuple of (is_valid, frames, duration)
            - is_valid: True if video is valid, False otherwise
            - frames: Number of frames (0 if check failed)
            - duration: Duration in seconds (0.0 if not checked or failed)
        """
        info = self.get_video_info(video_path)
        if info is None:
            return (False, 0, 0.0)

        frames, duration, codec_name = info

        if codec_name in IMAGE_CODECS:
            return (False, frames, duration)
        if codec_name == "vp9":
            return (True, frames, duration)
        if duration <= 0.0:
            return (False, frames, duration)
        if frames <= 1:
            return (False, frames, duration)

        return (True, frames, duration)
    
    def scan_creator_videos(
        self,
        creator_path: Path,
        video_extensions: list[str],
        display_manager: DisplayManager,
        total_checked_so_far: int = 0,
        total_to_check: int = 0,
        total_invalid_so_far: int = 0,
        total_incorrect_so_far: int = 0,
        image_extensions: list[str] | None = None,
        apply_corrections: bool = False,
        scan_folder: str | None = None,
        media_type: str = "Videos",
    ) -> tuple[dict[str, tuple[bool, int, float]], int, int]:
        """Scan all video files in a creator's folder with optional extension correction.

        Folder-agnostic: works with Videos folder or any other folder. Can scan all files
        regardless of extension if scan_folder is provided.

        When apply_corrections=True, automatically corrects file extensions based on actual
        media format detected using magic bytes. This is useful during repair operations to
        fix files with incorrect extensions.

        Args:
            creator_path: Path to the creator's root folder
            video_extensions: List of video file extensions to check
            display_manager: DisplayManager for integrated progress updates
            total_checked_so_far: Total videos already checked (for header progress)
            total_to_check: Total videos to check across all creators (for header progress)
            total_invalid_so_far: Total invalid videos found so far across all creators
            total_incorrect_so_far: Total incorrect extension videos found so far
            image_extensions: List of valid image extensions (required if apply_corrections)
            apply_corrections: If True, automatically correct file extensions
            scan_folder: Folder name to scan (e.g., 'Videos' or 'Images')
            media_type: Type of media (for display): "Videos" or "Images"

        Returns:
            Tuple of (results_dict, invalid_count, incorrect_count) where:
            - results_dict: Dictionary mapping filename -> (is_valid, frames, duration)
            - invalid_count: Number of invalid videos found in this creator (broken files)
            - incorrect_count: Number of videos with incorrect extensions in this creator
        """
        results: dict[str, tuple[bool, int, float]] = {}
        folder_name = scan_folder or "Videos"
        target_folder = creator_path / folder_name

        if not target_folder.exists() or not target_folder.is_dir():
            return results, 0, 0

        if folder_name.lower() == "videos":
            video_files = [
                f
                for f in target_folder.iterdir()
                if f.is_file() and f.suffix.lower() in video_extensions
            ]
        else:
            video_files = [f for f in target_folder.iterdir() if f.is_file()]

        invalid_count = 0
        incorrect_count = 0

        for idx, video_file in enumerate(video_files, 1):
            if media_type == "Images":
                is_valid, frames, duration = self.validate_image(video_file)
            else:
                is_valid, frames, duration = self.validate_video(video_file)
            results[video_file.name] = (is_valid, frames, duration)

            if not is_valid:
                invalid_count += 1
                display_manager.set_total_invalid(total_invalid_so_far + invalid_count)

            # Check if this file had an extension correction
            if self.extension_tracker.get_correction(str(video_file)) is not None:
                incorrect_count += 1
                display_manager.set_total_incorrect(
                    total_incorrect_so_far + incorrect_count
                )

            if apply_corrections and image_extensions:
                try:
                    corrected_path = self.extension_handler.validate_and_correct_file(
                        video_file,
                        image_extensions,
                        video_extensions,
                        apply_rename=True,
                    )
                    if corrected_path != video_file:
                        self.extension_tracker.record_correction(
                            str(video_file),
                            video_file.suffix.lower(),
                            corrected_path.suffix.lower(),
                        )
                        results[corrected_path.name] = results.pop(video_file.name)
                except OSError as e:
                    log_exception(e, f"Failed to correct extension for {video_file}")

            display_manager.update_verification_progress(
                idx, invalid_count, incorrect_count, media_type
            )

        return results, invalid_count, incorrect_count

    def scan_creator_images(
        self,
        creator_path: Path,
        image_extensions: list[str],
        display_manager: DisplayManager,
        total_checked_so_far: int = 0,
        total_to_check: int = 0,
        total_invalid_so_far: int = 0,
        total_incorrect_so_far: int = 0,
        video_extensions: list[str] | None = None,
        apply_corrections: bool = False,
    ) -> tuple[dict[str, tuple[bool, int, float]], int, int]:
        """Scan all image files in a creator's Images folder with extension correction.

        Convenience wrapper around scan_creator_videos with folder_agnostic=True
        for Images folder. Detects format mismatches and optionally corrects them.

        Args:
            creator_path: Path to the creator's root folder
            image_extensions: List of valid image extensions
            display_manager: DisplayManager for integrated progress updates
            total_checked_so_far: Total images already checked
            total_to_check: Total images to check across all creators
            total_invalid_so_far: Total invalid images found so far
            total_incorrect_so_far: Total incorrect extension images found so far
            video_extensions: List of video extensions (for cross-detection)
            apply_corrections: If True, automatically correct file extensions

        Returns:
            Tuple of (results_dict, invalid_count, incorrect_count)
        """
        return self.scan_creator_videos(
            creator_path=creator_path,
            video_extensions=video_extensions or [],
            display_manager=display_manager,
            total_checked_so_far=total_checked_so_far,
            total_to_check=total_to_check,
            total_invalid_so_far=total_invalid_so_far,
            total_incorrect_so_far=total_incorrect_so_far,
            image_extensions=image_extensions,
            apply_corrections=apply_corrections,
            scan_folder="Images",
            media_type="Images",
        )
