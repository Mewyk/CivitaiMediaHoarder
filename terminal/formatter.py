"""Custom help formatter for argparse using Rich library.

Provides colorful, well-organized help output for the CLI.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from io import StringIO

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .help_content import HelpContent, HelpStyles


class HelpRenderer:
    """Renders help content using Rich formatting."""

    def __init__(self, console: Console) -> None:
        """Initialize the help renderer.

        Args:
            console: Rich Console instance for output.
        """
        self.console = console
        self.content = HelpContent()
        self.styles = HelpStyles()

    def render_title_panel(self) -> None:
        """Render the main title panel with app name and description."""
        title = Text(self.content.APP_TITLE, style=self.styles.TITLE)
        subtitle = Text(self.content.APP_DESCRIPTION, style=self.styles.SUBTITLE)

        self.console.print()
        self.console.print(Panel(
            title + "\n" + subtitle,
            border_style=self.styles.BORDER,
            padding=(1, 2)
        ))

    def render_usage(self) -> None:
        """Render the usage line."""
        self.console.print()
        self.console.print(
            f"  [{self.styles.USAGE_HEADER}]Usage:[/{self.styles.USAGE_HEADER}] "
            f"[{self.styles.USAGE_PROGRAM}]{self.content.USAGE_PROGRAM}[/{self.styles.USAGE_PROGRAM}] "
            f"[{self.styles.USAGE_COMMAND}]{self.content.USAGE_COMMAND_PLACEHOLDER}[/{self.styles.USAGE_COMMAND}] "
            f"[{self.styles.USAGE_OPTIONS}]{self.content.USAGE_OPTIONS_PLACEHOLDER}[/{self.styles.USAGE_OPTIONS}]"
        )
        self.console.print()

    def _render_section(
        self,
        title: str,
        subtitle: str,
        items: list[tuple[str, str]],
        command_style: str,
        command_width: int = 35,
    ) -> None:
        """Render a section with commands and descriptions.

        Args:
            title: Section title.
            subtitle: Section subtitle (can be empty).
            items: List of (command, description) tuples.
            command_style: Style for command text.
            command_width: Width for command column formatting.
        """
        subtitle_text = f" [{self.styles.SECTION_DIM}]{subtitle}[/{self.styles.SECTION_DIM}]" if subtitle else ""
        self.console.print(
            f"  [{self.styles.SECTION_HEADER}]{title}[/{self.styles.SECTION_HEADER}]{subtitle_text}"
        )

        for command, description in items:
            self.console.print(
                f"    [{command_style}]{command:<{command_width}}[/{command_style}] "
                f"{description}"
            )

    def render_operation_modes(self) -> None:
        """Render the operation modes section."""
        section = self.content.OPERATION_MODES
        items = [(item.command, item.description) for item in section.items]
        self._render_section(
            section.title,
            section.subtitle,
            items,
            self.styles.MODE_COMMAND,
            command_width=35,
        )

    def render_media_config(self) -> None:
        """Render the media configuration section."""
        self.console.print()
        section = self.content.MEDIA_CONFIG
        items = [(item.command, item.description) for item in section.items]
        self._render_section(
            section.title,
            section.subtitle,
            items,
            self.styles.MEDIA_COMMAND,
            command_width=20,
        )

    def render_general_options(self) -> None:
        """Render the general options section."""
        self.console.print()
        section = self.content.GENERAL_OPTIONS
        items = [(item.command, item.description) for item in section.items]
        self._render_section(
            section.title,
            section.subtitle,
            items,
            self.styles.OPTION_COMMAND,
            command_width=25,
        )

    def render_examples(self) -> None:
        """Render the examples section."""
        self.console.print()
        self.console.print(
            f"  [{self.styles.SECTION_HEADER}]Examples[/{self.styles.SECTION_HEADER}]"
        )

        for example in self.content.EXAMPLES:
            self.console.print(
                f"    [{self.styles.EXAMPLE_TITLE}]{example.title}[/{self.styles.EXAMPLE_TITLE}]"
            )
            self.console.print(
                f"      [{self.styles.EXAMPLE_COMMAND}]$ {example.command}[/{self.styles.EXAMPLE_COMMAND}]"
            )

    def render_notes(self) -> None:
        """Render the important notes section."""
        self.console.print()
        self.console.print(
            f"  [{self.styles.SECTION_HEADER}]Notes[/{self.styles.SECTION_HEADER}]"
        )

        for icon, note in self.content.NOTES:
            self.console.print(
                f"    [{self.styles.NOTE_BULLET}]{icon}[/{self.styles.NOTE_BULLET}] {note}"
            )

        self.console.print()

    def render_all(self) -> str:
        """Render all help sections and return the complete output.

        Returns:
            Complete help text as a string.
        """
        self.render_title_panel()
        self.render_usage()
        self.render_operation_modes()
        self.render_media_config()
        self.render_general_options()
        self.render_examples()
        self.render_notes()

        return ""  # Output already sent to console


class RichHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom argparse formatter that uses Rich for colored, formatted help output."""

    def _format_usage(
        self,
        usage: str | None,
        actions: Iterable[argparse.Action],
        groups: Iterable[object],
        prefix: str | None,
    ) -> str:
        """Override to hide default usage line."""
        return ""

    def format_help(self) -> str:
        """Override to provide custom Rich-formatted help."""
        output = StringIO()
        console = Console(file=output, legacy_windows=True)

        renderer = HelpRenderer(console)
        renderer.render_all()

        return output.getvalue()
