"""Reusable Rich UI components for consistent terminal output.

This module provides factory functions and classes for creating
consistently styled Rich components throughout the application.
"""

from __future__ import annotations

from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner

from terminal.theme import theme


class ProgressBar:
    """Creates a text-based progress bar with consistent styling."""

    def __init__(self, width: int = 30):
        """Initialize the progress bar.

        Args:
            width: Character width of the progress bar.
        """
        self.width = width

    def render(
        self,
        current: int,
        total: int,
        show_counts: bool = True,
        complete_style: str | None = None,
        active_style: str | None = None,
    ) -> Text:
        """Render the progress bar as a Text object.

        Args:
            current: Current progress value.
            total: Total value for 100%.
            show_counts: Whether to show current/total counts.
            complete_style: Override style for completed portion.
            active_style: Override style for active portion.

        Returns:
            Rich Text object representing the progress bar.
        """
        if total <= 0:
            ratio = 0.0
        else:
            ratio = min(1.0, current / total)

        filled = int(self.width * ratio)
        is_complete = current >= total

        fill_style = complete_style or (
            theme.colors.PROGRESS_COMPLETE if is_complete else theme.colors.PROGRESS_ACTIVE
        )
        empty_style = active_style or theme.colors.PROGRESS_INACTIVE

        bar = Text()

        if filled > 0:
            bar.append(theme.symbols.PROGRESS_FILLED * filled, style=fill_style)

        if filled < self.width:
            bar.append(theme.symbols.PROGRESS_HEAD, style=fill_style if filled > 0 else empty_style)
            remaining = self.width - filled - 1
            if remaining > 0:
                bar.append(theme.symbols.PROGRESS_EMPTY * remaining, style=empty_style)

        if show_counts:
            bar.append(" ")
            bar.append(str(current), style=theme.styles.COUNT_CURRENT)
            bar.append("/", style=theme.styles.COUNT_SEPARATOR)
            bar.append(str(total), style=theme.styles.COUNT_TOTAL)

        return bar


class StatusLine:
    """Creates a status line with label and value."""

    @staticmethod
    def render(
        label: str,
        value: str,
        label_style: str | None = None,
        value_style: str | None = None,
    ) -> Text:
        """Render a label: value status line.

        Args:
            label: The label text.
            value: The value text.
            label_style: Optional style for the label.
            value_style: Optional style for the value.

        Returns:
            Rich Text object.
        """
        text = Text()
        text.append(f"{label}: ", style=label_style or "")
        text.append(value, style=value_style or theme.styles.COUNT_CURRENT)
        return text

    @staticmethod
    def render_count(
        label: str,
        current: int,
        total: int,
        label_style: str | None = None,
    ) -> Text:
        """Render a label with current/total count.

        Args:
            label: The label text.
            current: Current count.
            total: Total count.
            label_style: Optional style for the label.

        Returns:
            Rich Text object.
        """
        text = Text()
        text.append(f"{label}: ", style=label_style or "")
        text.append(str(current), style=theme.styles.COUNT_CURRENT)
        text.append("/", style=theme.styles.COUNT_SEPARATOR)
        text.append(str(total), style=theme.styles.COUNT_TOTAL)
        return text


class Panels:
    """Factory for creating consistently styled panels."""

    @staticmethod
    def summary(
        content: RenderableType,
        title: str,
        subtitle: str | None = None,
    ) -> Panel:
        """Create a summary panel with primary styling.

        Args:
            content: Panel content.
            title: Panel title.
            subtitle: Optional subtitle.

        Returns:
            Configured Panel object.
        """
        return Panel(
            content,
            title=f"[{theme.styles.PANEL_TITLE_PRIMARY}]{title}",
            title_align=theme.panel.TITLE_ALIGN,
            subtitle=f"[{theme.colors.TEXT_DIM}]{subtitle}" if subtitle else None,
            subtitle_align="right",
            border_style=theme.colors.BORDER_SUCCESS,
            padding=theme.panel.PADDING,
        )

    @staticmethod
    def error(
        content: RenderableType,
        title: str = "Errors",
    ) -> Panel:
        """Create an error panel with error styling.

        Args:
            content: Panel content.
            title: Panel title.

        Returns:
            Configured Panel object.
        """
        return Panel(
            content,
            title=f"[{theme.styles.PANEL_TITLE_ERROR}]{title}",
            title_align=theme.panel.TITLE_ALIGN,
            border_style=theme.colors.BORDER_ERROR,
            padding=theme.panel.PADDING,
        )

    @staticmethod
    def warning(
        content: RenderableType,
        title: str = "Warning",
    ) -> Panel:
        """Create a warning panel with warning styling.

        Args:
            content: Panel content.
            title: Panel title.

        Returns:
            Configured Panel object.
        """
        return Panel(
            content,
            title=f"[{theme.styles.PANEL_TITLE_WARNING}]{title}",
            title_align=theme.panel.TITLE_ALIGN,
            border_style=theme.colors.BORDER_WARNING,
            padding=theme.panel.PADDING,
        )

    @staticmethod
    def confirmation(
        content: RenderableType,
        title: str = "Confirmation",
    ) -> Panel:
        """Create a confirmation panel.

        Args:
            content: Panel content.
            title: Panel title.

        Returns:
            Configured Panel object.
        """
        return Panel(
            content,
            title=f"[{theme.styles.PANEL_TITLE_WARNING}]{title}",
            title_align=theme.panel.TITLE_ALIGN,
            border_style=theme.colors.BORDER_WARNING,
            padding=theme.panel.PADDING,
        )

    @staticmethod
    def info(
        content: RenderableType,
        title: str,
    ) -> Panel:
        """Create an info panel with primary styling.

        Args:
            content: Panel content.
            title: Panel title.

        Returns:
            Configured Panel object.
        """
        return Panel(
            content,
            title=f"[{theme.styles.PANEL_TITLE_PRIMARY}]{title}",
            title_align=theme.panel.TITLE_ALIGN,
            border_style=theme.colors.BORDER_PRIMARY,
            padding=theme.panel.PADDING,
        )


class Spinners:
    """Factory for creating consistently styled spinners."""

    @staticmethod
    def default(text: str = "") -> Spinner:
        """Create a default spinner.

        Args:
            text: Text to display next to the spinner.

        Returns:
            Configured Spinner object.
        """
        return Spinner("dots", text=text, style=theme.colors.WARNING)

    @staticmethod
    def primary(text: str = "") -> Spinner:
        """Create a primary-styled spinner.

        Args:
            text: Text to display next to the spinner.

        Returns:
            Configured Spinner object.
        """
        return Spinner("dots", text=text, style=theme.colors.PRIMARY)


class StatusIndicators:
    """Factory for creating status indicator text."""

    @staticmethod
    def success(message: str) -> Text:
        """Create a success indicator.

        Args:
            message: Success message.

        Returns:
            Rich Text object.
        """
        return Text(f"{theme.symbols.CHECK} {message}", style=theme.colors.SUCCESS)

    @staticmethod
    def error(message: str) -> Text:
        """Create an error indicator.

        Args:
            message: Error message.

        Returns:
            Rich Text object.
        """
        return Text(f"{theme.symbols.CROSS} {message}", style=theme.colors.ERROR)

    @staticmethod
    def warning(message: str) -> Text:
        """Create a warning indicator.

        Args:
            message: Warning message.

        Returns:
            Rich Text object.
        """
        return Text(f"{theme.symbols.WARNING} {message}", style=theme.colors.WARNING)

    @staticmethod
    def info(message: str) -> Text:
        """Create an info indicator.

        Args:
            message: Info message.

        Returns:
            Rich Text object.
        """
        return Text(f"{theme.symbols.INFO} {message}", style=theme.colors.INFO)

    @staticmethod
    def bullet(message: str) -> Text:
        """Create a bullet point.

        Args:
            message: Message text.

        Returns:
            Rich Text object.
        """
        return Text(f"{theme.symbols.BULLET} {message}")


class ErrorList:
    """Formats error lists for display."""

    @staticmethod
    def render(errors: list[tuple[str, str]]) -> str:
        """Render a list of errors as formatted text.

        Args:
            errors: List of (name, error_message) tuples.

        Returns:
            Formatted error string.
        """
        lines = [f"{theme.symbols.CROSS} {name}: {msg}" for name, msg in errors]
        return "\n".join(lines)


def create_console() -> Console:
    """Create a configured Console instance.

    Returns:
        Console with standard configuration.
    """
    return Console()
