"""Help content data structures for the CLI help formatter.

Defines all help text, examples, and command descriptions in a structured way.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Style constants for consistent formatting
class HelpStyles:
    """Color and style constants for help output."""

    # Main styles
    TITLE = "bold cadet_blue"
    SUBTITLE = "pale_turquoise4"
    BORDER = "cadet_blue"

    # Section headers
    SECTION_HEADER = "bold bright_white"
    SECTION_DIM = "dim"

    # Command styles
    MODE_BULLET = "bold steel_blue"
    MODE_COMMAND = "bold steel_blue"

    MEDIA_BULLET = "bold steel_blue3"
    MEDIA_COMMAND = "bold steel_blue3"

    OPTION_BULLET = "bold sky_blue3"
    OPTION_COMMAND = "bold sky_blue3"

    EXAMPLE_ARROW = "bold light_sky_blue3"
    EXAMPLE_TITLE = "bold light_sky_blue3"
    EXAMPLE_COMMAND = "dark_slate_gray3"

    # Note styles
    NOTE_WARNING = "bold steel_blue3"
    NOTE_INFO = "bold steel_blue3"
    NOTE_BULLET = "bold sky_blue3"

    # Usage line
    USAGE_SEPARATOR = "bold cadet_blue"
    USAGE_HEADER = "bold bright_white"
    USAGE_PROGRAM = "white"
    USAGE_COMMAND = "bold cadet_blue"
    USAGE_OPTIONS = "pale_turquoise4"


@dataclass
class CommandItem:
    """Represents a single command or option."""
    command: str
    description: str


@dataclass
class ExampleItem:
    """Represents a usage example."""
    title: str
    command: str


@dataclass
class HelpSection:
    """Represents a section in the help output."""
    title: str
    subtitle: str = ""
    items: list[CommandItem] = field(default_factory=lambda: [])


class HelpContent:
    """Central repository for all CLI help content."""

    APP_TITLE = "Civitai Media Hoarder"
    APP_DESCRIPTION = "Fetch and manage Civitai creator media with flexible filtering"

    USAGE_PROGRAM = "python main.py"
    USAGE_COMMAND_PLACEHOLDER = "<command>"
    USAGE_OPTIONS_PLACEHOLDER = "[options]"

    # Operation Modes
    OPERATION_MODES = HelpSection(
        title="Operation Modes",
        subtitle="Only one operation mode can be used per command",
        items=[
            CommandItem(
                "--update, -u [CreatorName]",
                "Update the specified creators, or all creators if none are provided"
            ),
            CommandItem(
                "--add, -a [CreatorName]",
                "Add one or more creators to the master list"
            ),
            CommandItem(
                "--remove, -r [CreatorName]",
                "Remove one or more creators from the master list"
            ),
            CommandItem(
                "--verify [CreatorName]",
                "Verify all media (images and videos) for creators"
            ),
            CommandItem(
                "--verify-images [CreatorName]",
                "Verify images for creators (all or specified)"
            ),
            CommandItem(
                "--verify-videos [CreatorName]",
                "Verify videos for creators (all or specified)"
            ),
        ]
    )

    # Media Configuration
    MEDIA_CONFIG = HelpSection(
        title="Media Configuration",
        subtitle="(use with --add)",
        items=[
            CommandItem("--images-on", "Enable image downloads for the creator"),
            CommandItem("--images-off", "Disable image downloads for the creator"),
            CommandItem("--videos-on", "Enable video downloads for the creator"),
            CommandItem("--videos-off", "Disable video downloads for the creator"),
            CommandItem("--other-on", "Enable other media types for the creator"),
            CommandItem("--other-off", "Disable other media types for the creator"),
        ]
    )

    # General Options
    GENERAL_OPTIONS = HelpSection(
        title="General Options",
        items=[
            CommandItem(
                "--save-metadata, -sm",
                "Save creator metadata to a JSON file after processing"
            ),
            CommandItem(
                "--ignore-off, -ix",
                "Disable ignore.txt filtering"
            ),
            CommandItem(
                "--auto-purge, -ap",
                "Automatically purge deleted creators without prompting"
            ),
            CommandItem(
                "--repair",
                "Repair invalid videos by redownloading them"
            ),
            CommandItem(
                "--yes, -y",
                "Automatically confirm all prompts"
            ),
            CommandItem(
                "--debug",
                "Enable debug logging to the logs folder"
            ),
        ]
    )

    # Examples
    EXAMPLES = [
        ExampleItem(
            "Add a new creator:",
            "python main.py --add creator_one --images-on --videos-on"
        ),
        ExampleItem(
            "Update specific creators:",
            "python main.py --update creator_one creator_two creator_three"
        ),
        ExampleItem(
            "Update all creators:",
            "python main.py --update"
        ),
        ExampleItem(
            "Verify and repair videos:",
            "python main.py --verify-videos --repair --yes"
        ),
        ExampleItem(
            "Save the json metadata returned from the api:",
            "python main.py --update creator_one --save-metadata"
        ),
    ]

    # Important Notes
    NOTES = [
        ("!", "Media flags (--images-on, etc.) only work with --add"),
        ("i", "--auto-purge and --ignore-off only apply to --update"),
        ("*", "Operation modes are mutually exclusive (choose only one per command)"),
        ("*", "Use --yes or -y to skip confirmations in automation"),
    ]
