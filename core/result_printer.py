"""Unified printer for all operation results.

This module provides a centralized way to print operation results to the console.
All console output for summaries, errors, and confirmations flows through here,
ensuring consistent visual style and formatting across all operations.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from core.operation_results import (
    OperationSummary,
    UpdateOperationSummary,
    VerifyOperationSummary,
    RepairOperationSummary,
)
from core.result_formatter import ResultFormatter


class ResultPrinter:
    """
    Unified printer for all operation results.
    
    Handles printing of summaries, errors, confirmations, and warnings
    with consistent visual styling. Separation of concerns: this printer
    only handles OUTPUT, not state management or formatting logic.
    
    DisplayManager handles LIVE display during operations.
    ResultPrinter handles FINAL results after operations complete.
    """
    
    def __init__(self, console: Console | None = None):
        """
        Initialize the result printer.
        
        Args:
            console: Optional Console instance. If not provided, creates one.
        """
        self.console = console or Console()
    
    def print_summary_panel(
        self,
        summary_lines: list[str],
        title: str,
        border_style: str = "cyan",
    ) -> None:
        """
        Print a summary panel.
        
        Common format for all operation summaries. Provides clean, consistent
        visual presentation of operation results.
        
        Args:
            summary_lines: Lines of summary content to display
            title: Panel title
            border_style: Border color (default: cyan)
        """
        content = "\n".join(summary_lines)
        self.console.print(Panel(
            content,
            title=f"[bold {border_style}]{title}",
            title_align="left",
            border_style=border_style,
            padding=(1, 2)
        ))
    
    def print_error_panel(
        self,
        errors: list[tuple[str, str]],
        title: str | None = None,
    ) -> None:
        """
        Print error panel with consistent formatting.
        
        Args:
            errors: List of (name, error_msg) tuples
            title: Panel title (auto-generated if not provided)
        """
        if not errors:
            return
        
        error_lines = ResultFormatter.format_error_items(errors)
        content = "\n".join(error_lines)
        
        if title is None:
            title = ResultFormatter.format_failed_creators_title(len(errors))
        
        self.console.print(Panel(
            content,
            title=f"[bold red]{title}",
            title_align="left",
            border_style="red",
            padding=(1, 2)
        ))
    
    def print_confirmation_panel(
        self,
        message: str,
        title: str = "⚠ Confirmation"
    ) -> None:
        """
        Print confirmation panel.
        
        Used for operations that need user confirmation before proceeding.
        
        Args:
            message: Message to display
            title: Panel title
        """
        self.console.print(Panel(
            message,
            title=f"[bold orange3]{title}",
            title_align="left",
            border_style="orange3",
            padding=(1, 2)
        ))
    
    def print_extension_corrections(
        self,
        corrections: dict[str, tuple[str, str]],
    ) -> None:
        """
        Print extension corrections summary.
        
        Lists files that had their extensions corrected during the operation.
        
        Args:
            corrections: Dict mapping file_path -> (old_ext, new_ext)
        """
        if not corrections:
            return
        # Print aggregated counts per extension-change (e.g. '.jpeg → .png: 100')
        # to avoid flooding the terminal with one line per file.
        self.console.print()

        # Header with total corrections
        header = ResultFormatter.format_extension_corrections_header(len(corrections))
        self.console.print(f"[cyan]{header}[/cyan]")

        # Aggregate by (old_ext, new_ext)
        agg: dict[tuple[str, str], int] = {}
        for _path, (old_ext, new_ext) in corrections.items():
            key = (old_ext, new_ext)
            agg[key] = agg.get(key, 0) + 1

        # Print aggregated summary sorted by descending count then extension
        for (old_ext, new_ext), count in sorted(agg.items(), key=lambda kv: (-kv[1], kv[0])):
            # Keep same arrow styling as formatter
            self.console.print(f"  {old_ext} → {new_ext}: {count} file(s)")
    
    def print_warnings_panel(
        self,
        warnings: list[str],
    ) -> None:
        """
        Print warnings panel.
        
        Args:
            warnings: List of warning messages
        """
        if not warnings:
            return
        
        warning_lines = ResultFormatter.format_warnings(warnings)
        content = "\n".join(warning_lines)
        title = ResultFormatter.format_warnings_title(len(warnings))
        
        self.console.print(Panel(
            content,
            title=f"[bold yellow]{title}",
            title_align="left",
            border_style="yellow",
            padding=(1, 2)
        ))
    
    def print_update_summary(
        self,
        summary: UpdateOperationSummary
    ) -> None:
        """
        Print update operation summary with proper formatting.
        
        Args:
            summary: UpdateOperationSummary object with results
        """
        # Main summary panel
        summary_lines = ResultFormatter.format_update_summary(summary)
        self.print_summary_panel(
            summary_lines,
            "Creator Update | Summary",
            border_style="cyan"
        )
        
        # Extension corrections if any
        if summary.extension_corrections:
            self.print_extension_corrections(summary.extension_corrections)
        
        # Errors if any
        if summary.failed_creators:
            self.print_error_panel(summary.failed_creators)
        
        # Warnings if any
        if summary.warnings:
            self.print_warnings_panel(summary.warnings)
    
    def print_verify_summary(
        self,
        summary: VerifyOperationSummary
    ) -> None:
        """
        Print verify operation summary with proper formatting.
        
        Args:
            summary: VerifyOperationSummary object with results
        """
        # Main summary panel
        summary_lines = ResultFormatter.format_verify_summary(summary)
        title = ResultFormatter.format_verify_summary_title(summary)
        self.print_summary_panel(
            summary_lines,
            title,
            border_style="cyan"
        )
        
        # Extension corrections if any
        if summary.extension_corrections:
            self.print_extension_corrections(summary.extension_corrections)
        
        # Warnings if any
        if summary.warnings:
            self.print_warnings_panel(summary.warnings)
    
    def print_repair_summary(
        self,
        summary: RepairOperationSummary
    ) -> None:
        """
        Print repair operation summary with proper formatting.
        
        Args:
            summary: RepairOperationSummary object with results
        """
        # Main summary panel
        summary_lines = ResultFormatter.format_repair_summary(summary)
        title = ResultFormatter.format_repair_summary_title(summary)
        self.print_summary_panel(
            summary_lines,
            title,
            border_style="cyan"
        )
        
        # Warnings if any
        if summary.warnings:
            self.print_warnings_panel(summary.warnings)
    
    def print_generic_summary(
        self,
        summary: OperationSummary,
        title: str = "Operation Summary"
    ) -> None:
        """
        Print a generic operation summary.
        
        Handles any OperationSummary type by delegating to specific
        printers based on the summary type.
        
        Args:
            summary: OperationSummary object (or subclass)
            title: Title to use if type-specific title not available
        """
        if isinstance(summary, UpdateOperationSummary):
            self.print_update_summary(summary)
        elif isinstance(summary, VerifyOperationSummary):
            self.print_verify_summary(summary)
        elif isinstance(summary, RepairOperationSummary):
            self.print_repair_summary(summary)
        else:
            # Fallback for unknown types
            self.print_summary_panel([str(summary)], title)
