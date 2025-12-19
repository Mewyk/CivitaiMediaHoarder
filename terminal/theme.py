"""Centralized theme configuration for Rich UI components.

This module defines all colors, styles, and visual constants used throughout
the application's terminal output. Centralizing these values ensures
consistent appearance and makes theming easy to modify.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AlignMethod = Literal["left", "center", "right"]


@dataclass(frozen=True)
class ThemeColors:
    """Core color palette for the application."""

    # Primary colors
    PRIMARY: str = "bright_blue"
    SECONDARY: str = "cyan"
    ACCENT: str = "medium_purple"

    # Status colors
    SUCCESS: str = "green"
    WARNING: str = "orange3"
    ERROR: str = "red"
    INFO: str = "bright_cyan"

    # Text colors
    TEXT: str = "white"
    TEXT_DIM: str = "dim"
    TEXT_MUTED: str = "grey70"

    # Panel borders
    BORDER_PRIMARY: str = "bright_blue"
    BORDER_SUCCESS: str = "cyan"
    BORDER_WARNING: str = "orange3"
    BORDER_ERROR: str = "red"

    # Progress bar colors
    PROGRESS_COMPLETE: str = "medium_purple"
    PROGRESS_ACTIVE: str = "magenta"
    PROGRESS_INACTIVE: str = "dim"

    # Media type colors
    IMAGES_ONLY: str = "bright_green"
    VIDEOS_ONLY: str = "medium_purple"
    MIXED_MEDIA: str = "bright_yellow"
    DEFAULT_MEDIA: str = "bright_cyan"

    # Debug console colors
    DEBUG_BORDER: str = "magenta"
    DEBUG_TITLE: str = "bold magenta"


@dataclass(frozen=True)
class ThemeStyles:
    """Composite styles combining colors with formatting."""

    # Titles and headers
    TITLE: str = "bold bright_blue"
    SUBTITLE: str = "deep_sky_blue1"
    SECTION_HEADER: str = "bold bright_white"

    # Panel titles
    PANEL_TITLE_PRIMARY: str = "bold cyan"
    PANEL_TITLE_SUCCESS: str = "bold green"
    PANEL_TITLE_WARNING: str = "bold orange3"
    PANEL_TITLE_ERROR: str = "bold red"

    # Text emphasis
    BOLD: str = "bold"
    DIM: str = "dim"
    UNDERLINE: str = "underline"
    BOLD_UNDERLINE: str = "bold underline"

    # Interactive elements
    LINK: str = "bright_cyan underline"
    BULLET: str = "bold steel_blue"

    # Status indicators
    SUCCESS_INDICATOR: str = "green"
    WARNING_INDICATOR: str = "orange3"
    ERROR_INDICATOR: str = "bold red"

    # Counter styles
    COUNT_CURRENT: str = "bold cyan"
    COUNT_TOTAL: str = "medium_purple"
    COUNT_SEPARATOR: str = "dim"


@dataclass(frozen=True)
class ThemeSymbols:
    """Unicode symbols used in the UI."""

    CHECK: str = "✓"
    CROSS: str = "✗"
    BULLET: str = "•"
    DIAMOND: str = "◆"
    ARROW: str = "→"
    WARNING: str = "!"
    INFO: str = "i"

    # Progress bar segments
    PROGRESS_FILLED: str = "━"
    PROGRESS_EMPTY: str = "─"
    PROGRESS_HEAD: str = "╸"

    # Section separators
    SECTION_LINE: str = "──"
    SECTION_DOUBLE: str = "══"


@dataclass(frozen=True)
class PanelConfig:
    """Configuration for Rich Panel components."""

    PADDING: tuple[int, int] = (1, 2)
    TITLE_ALIGN: AlignMethod = "left"


class Theme:
    """Main theme class providing access to all theme components.

    Usage:
        from terminal.theme import theme

        console.print(f"[{theme.colors.SUCCESS}]Done![/{theme.colors.SUCCESS}]")
        console.print(Panel(..., border_style=theme.colors.BORDER_PRIMARY))
    """

    colors = ThemeColors()
    styles = ThemeStyles()
    symbols = ThemeSymbols()
    panel = PanelConfig()

    @classmethod
    def get_media_style(cls, images: bool, videos: bool, other: bool = False) -> str:
        """Get appropriate style based on enabled media types.

        Args:
            images: Whether images are enabled.
            videos: Whether videos are enabled.
            other: Whether other media is enabled.

        Returns:
            Style string for the media type combination.
        """
        if images and not videos:
            return cls.colors.IMAGES_ONLY
        elif videos and not images:
            return cls.colors.VIDEOS_ONLY
        elif images and videos:
            return cls.colors.MIXED_MEDIA
        else:
            return cls.colors.DEFAULT_MEDIA

    @classmethod
    def get_log_level_style(cls, level: str) -> str:
        """Get style for a log level.

        Args:
            level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).

        Returns:
            Style string for the log level.
        """
        level_styles: dict[str, str] = {
            "DEBUG": cls.colors.TEXT_DIM,
            "INFO": cls.colors.TEXT,
            "WARNING": cls.colors.WARNING,
            "WARN": cls.colors.WARNING,
            "ERROR": cls.styles.ERROR_INDICATOR,
            "CRITICAL": "bold white on red",
        }
        return level_styles.get(level.upper(), cls.colors.TEXT)


# Global theme instance for easy import
theme = Theme()
