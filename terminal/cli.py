"""Command-line interface configuration and argument parsing.

This module provides a clean, professional CLI structure following
best practices for argument organization and validation.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from enum import Enum, auto

from rich.console import Console

from terminal.formatter import RichHelpFormatter


class OperationMode(Enum):
    """Available operation modes for the CLI."""

    UPDATE = auto()
    ADD = auto()
    REMOVE = auto()
    VERIFY = auto()
    VERIFY_IMAGES = auto()
    VERIFY_VIDEOS = auto()
    REPAIR = auto()


class VerifyMode(Enum):
    """Verification mode for --verify commands."""

    NONE = auto()
    ALL = auto()
    IMAGES = auto()
    VIDEOS = auto()


@dataclass
class MediaTypeFlags:
    """Media type configuration from CLI flags."""

    images: bool | None = None
    videos: bool | None = None
    other: bool | None = None

    def has_any(self) -> bool:
        """Check if any media type flag was set."""
        return any(v is not None for v in [self.images, self.videos, self.other])

    def to_dict(self) -> dict[str, bool]:
        """Convert to dictionary, excluding None values."""
        result: dict[str, bool] = {}
        if self.images is not None:
            result["images"] = self.images
        if self.videos is not None:
            result["videos"] = self.videos
        if self.other is not None:
            result["other"] = self.other
        return result


@dataclass
class ParsedArgs:
    """Structured representation of parsed CLI arguments.

    Provides a clean interface to access CLI arguments with proper typing
    and validation already applied.
    """

    mode: OperationMode | None = None
    verify_mode: VerifyMode = VerifyMode.NONE
    creators: list[str] = field(default_factory=lambda: [])
    media_types: MediaTypeFlags = field(default_factory=MediaTypeFlags)

    # Flags
    auto_purge: bool = False
    ignore_off: bool = False
    repair: bool = False
    yes: bool = False
    debug: bool = False
    save_metadata: bool = False


class CLIParser:
    """Professional CLI argument parser with validation."""

    def __init__(self) -> None:
        """Initialize the CLI parser."""
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with all arguments defined."""
        parser = argparse.ArgumentParser(
            description="Civitai Media Hoarder - Fetch and manage creator media",
            formatter_class=RichHelpFormatter,
            add_help=False,
        )

        self._add_operation_modes(parser)
        self._add_media_flags(parser)
        self._add_options(parser)

        return parser

    def _add_operation_modes(self, parser: argparse.ArgumentParser) -> None:
        """Add mutually exclusive operation mode arguments."""
        modes = parser.add_mutually_exclusive_group()

        modes.add_argument(
            "--update",
            "-u",
            metavar="CREATORS",
            nargs="*",
            help="Update specified creators, or all creators if none specified",
        )

        modes.add_argument(
            "--add",
            "-a",
            metavar="CREATORS",
            nargs="+",
            help="Add creators to master list",
        )

        modes.add_argument(
            "--remove",
            "-r",
            metavar="USERNAME",
            help="Remove a creator from master list",
        )

        modes.add_argument(
            "--verify",
            metavar="CREATORS",
            nargs="*",
            help="Verify all media for creators (or all if none specified)",
        )

        modes.add_argument(
            "--verify-images",
            metavar="CREATORS",
            nargs="*",
            help="Verify images for creators (or all if none specified)",
        )

        modes.add_argument(
            "--verify-videos",
            metavar="CREATORS",
            nargs="*",
            help="Verify videos for creators (or all if none specified)",
        )

    def _add_media_flags(self, parser: argparse.ArgumentParser) -> None:
        """Add media type configuration flags."""
        media = parser.add_argument_group("media types", "Configure media types (use with --add-creator)")

        media.add_argument("--images-on", action="store_true", help="Enable images")
        media.add_argument("--images-off", action="store_true", help="Disable images")
        media.add_argument("--videos-on", action="store_true", help="Enable videos")
        media.add_argument("--videos-off", action="store_true", help="Disable videos")
        media.add_argument("--other-on", action="store_true", help="Enable other media")
        media.add_argument("--other-off", action="store_true", help="Disable other media")

    def _add_options(self, parser: argparse.ArgumentParser) -> None:
        """Add general option flags."""
        options = parser.add_argument_group("options")

        options.add_argument(
            "--auto-purge",
            "-ap",
            action="store_true",
            help="Automatically purge deleted creators",
        )

        options.add_argument(
            "--ignore-off",
            "-ix",
            action="store_true",
            help="Disable ignore.txt filtering",
        )

        options.add_argument(
            "--repair",
            action="store_true",
            help="Repair invalid media files",
        )

        options.add_argument(
            "--save-metadata",
            "-sm",
            action="store_true",
            help="Save creator metadata to JSON file",
        )

        options.add_argument(
            "--yes",
            "-y",
            action="store_true",
            help="Automatically confirm prompts",
        )

        options.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging",
        )

        options.add_argument(
            "-h",
            "--help",
            action="store_true",
            help="Show help message",
        )

    def parse(self, args: list[str] | None = None) -> ParsedArgs:
        """Parse command-line arguments.

        Args:
            args: Optional list of arguments. Uses sys.argv if None.

        Returns:
            ParsedArgs with validated arguments.

        Raises:
            SystemExit: If arguments are invalid or help is requested.
        """
        namespace = self.parser.parse_args(args)

        if namespace.help:
            from rich.console import Console
            console = Console()
            help_text = self.parser.format_help()
            console.print(help_text, end="")
            sys.exit(0)

        self._validate(namespace)

        return self._convert(namespace)

    def _validate(self, args: argparse.Namespace) -> None:
        """Validate argument combinations.

        Args:
            args: Parsed namespace to validate.

        Raises:
            SystemExit: If validation fails.
        """
        # Check for conflicting media flags
        if args.images_on and args.images_off:
            self.parser.error("Cannot use both --images-on and --images-off")
        if args.videos_on and args.videos_off:
            self.parser.error("Cannot use both --videos-on and --videos-off")
        if args.other_on and args.other_off:
            self.parser.error("Cannot use both --other-on and --other-off")

        # Media flags only valid with --add
        has_media_flags = any([
            args.images_on, args.images_off,
            args.videos_on, args.videos_off,
            args.other_on, args.other_off,
        ])
        if has_media_flags and not args.add:
            self.parser.error("Media type flags require --add")

        # --auto-purge and --ignore-off require update mode
        update_mode = args.update is not None
        if args.auto_purge and not update_mode:
            self.parser.error("--auto-purge requires --update")
        if args.ignore_off and not update_mode:
            self.parser.error("--ignore-off requires --update")

        # --yes requires verify or repair
        verify_mode = (
            args.verify is not None
            or args.verify_images is not None
            or args.verify_videos is not None
        )
        if args.yes and not (verify_mode or args.repair):
            self.parser.error("--yes requires --verify, --verify-images, --verify-videos, or --repair")

        # Require at least one operation mode
        has_mode = any([
            args.update is not None,
            args.add,
            args.remove,
            args.verify is not None,
            args.verify_images is not None,
            args.verify_videos is not None,
            args.repair,
        ])
        if not has_mode:
            self.parser.error(
                "Please specify an operation: --update, --add, "
                "--remove, --verify, --verify-images, --verify-videos, or --repair"
            )

    def _convert(self, args: argparse.Namespace) -> ParsedArgs:
        """Convert namespace to ParsedArgs.

        Args:
            args: Validated namespace.

        Returns:
            ParsedArgs instance.
        """
        result = ParsedArgs()

        # Determine operation mode and verify mode
        if args.update is not None:
            result.mode = OperationMode.UPDATE
            result.creators = self._parse_creators(args.update) if args.update else []
        elif args.add:
            result.mode = OperationMode.ADD
            result.creators = self._parse_creators(args.add)
        elif args.remove:
            result.mode = OperationMode.REMOVE
            result.creators = [args.remove]
        elif args.verify is not None:
            result.mode = OperationMode.VERIFY
            result.verify_mode = VerifyMode.ALL
            result.creators = self._parse_creators(args.verify) if args.verify else []
        elif args.verify_images is not None:
            result.mode = OperationMode.VERIFY_IMAGES
            result.verify_mode = VerifyMode.IMAGES
            result.creators = self._parse_creators(args.verify_images) if args.verify_images else []
        elif args.verify_videos is not None:
            result.mode = OperationMode.VERIFY_VIDEOS
            result.verify_mode = VerifyMode.VIDEOS
            result.creators = self._parse_creators(args.verify_videos) if args.verify_videos else []
        elif args.repair:
            result.mode = OperationMode.REPAIR

        # Parse media type flags
        if args.images_on:
            result.media_types.images = True
        elif args.images_off:
            result.media_types.images = False

        if args.videos_on:
            result.media_types.videos = True
        elif args.videos_off:
            result.media_types.videos = False

        if args.other_on:
            result.media_types.other = True
        elif args.other_off:
            result.media_types.other = False

        # Copy flags
        result.auto_purge = args.auto_purge
        result.ignore_off = args.ignore_off
        result.repair = args.repair
        result.yes = args.yes
        result.debug = args.debug
        result.save_metadata = args.save_metadata

        return result

    def _parse_creators(self, items: list[str]) -> list[str]:
        """Parse creator names from argument list.

        Handles both comma-separated and space-separated names.

        Args:
            items: List of argument values.

        Returns:
            List of individual creator names.
        """
        creators: list[str] = []
        for item in items:
            for name in item.split(","):
                name = name.strip()
                if name:
                    creators.append(name)
        return creators


def parse_arguments() -> ParsedArgs:
    """Parse command-line arguments.

    This is the main entry point for CLI parsing.

    Returns:
        ParsedArgs with validated arguments.
    """
    parser = CLIParser()
    return parser.parse()
