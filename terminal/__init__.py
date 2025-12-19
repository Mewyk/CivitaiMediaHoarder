"""Terminal presentation layer for Civitai Media Hoarder.

Provides CLI parsing, theming, and reusable UI components.
"""

from .cli import CLIParser, OperationMode, ParsedArgs, VerifyMode, parse_arguments
from .components import (
    ErrorList,
    Panels,
    ProgressBar,
    Spinners,
    StatusIndicators,
    StatusLine,
    create_console,
)
from .formatter import RichHelpFormatter
from .theme import Theme, theme

__all__ = [
    # CLI
    "CLIParser",
    "OperationMode",
    "ParsedArgs",
    "VerifyMode",
    "parse_arguments",
    # Theme
    "Theme",
    "theme",
    # Components
    "create_console",
    "ErrorList",
    "Panels",
    "ProgressBar",
    "RichHelpFormatter",
    "Spinners",
    "StatusIndicators",
    "StatusLine",
]
