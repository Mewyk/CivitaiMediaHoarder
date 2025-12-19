"""Unified formatter for all operation results.

This module provides formatting logic to convert operation results into
human-readable formats suitable for console display. Formatters are
independent of display concerns - they return data structures or strings
that describe how results should be displayed.
"""

from __future__ import annotations

from core.operation_results import (
    UpdateOperationSummary,
    VerifyOperationSummary,
    RepairOperationSummary,
)


class ResultFormatter:
    """
    Formats operation results for display.
    
    This class converts operation summary objects into formatted strings
    and structured data suitable for display. All formatting logic is
    centralized here for consistency.
    """
    
    @staticmethod
    def format_update_summary(summary: UpdateOperationSummary) -> list[str]:
        """
        Format update operation summary for display with three sections:
        Api Stats, Download Stats, and Maintenance Report.
        
        Args:
            summary: UpdateOperationSummary object with operation results
            
        Returns:
            List[str]: Formatted summary lines for display
        """
        lines: list[str] = []
        
        # API Stats Section
        lines.append("── Api Stats ──")
        lines.append(f"• Creators Processed: {summary.successful}/{summary.total}")
        lines.append(f"• Total Items Found: {summary.api_items_total}")
        lines.append(f"• Total Errors: {summary.failed}")
        
        # Download Stats Section
        lines.append("")
        lines.append("── Download Stats ──")
        # When needed counts are unknown (0) but downloads occurred, show the
        # downloaded count as the denominator to avoid displaying '/0'.
        images_needed = summary.images_needed if summary.images_needed > 0 else (summary.images_downloaded if summary.images_downloaded > 0 else 0)
        videos_needed = summary.videos_needed if summary.videos_needed > 0 else (summary.videos_downloaded if summary.videos_downloaded > 0 else 0)

        lines.append(f"• Images: {summary.images_downloaded}/{images_needed}")
        lines.append(f"• Videos: {summary.videos_downloaded}/{videos_needed}")
        total_dl = summary.images_downloaded + summary.videos_downloaded
        total_needed = images_needed + videos_needed
        lines.append(f"• Total: {total_dl}/{total_needed}")
        
        # Get media types - placeholder for now
        media_types = summary.get_media_types_downloaded()
        if media_types:
            media_types_str = ", ".join(media_types)
        else:
            media_types_str = "None"
        lines.append(f"• Media Types: {media_types_str}")
        
        # Maintenance Report Section
        lines.append("")
        lines.append("── Maintenance Report ──")
        correction_count = summary.correction_count()
        # If there were no corrections, show 'None'. Otherwise show a simple count.
        if correction_count == 0:
            lines.append("• Media Types Corrected: None")
        else:
            lines.append(f"• Media Types Corrected: {correction_count}")
        
        # Correction types with sub-list
        correction_types = summary.get_correction_types()
        if correction_types:
            lines.append("• Correction Types:")
            for correction_type in sorted(correction_types.keys()):
                lines.append(f"    • {correction_type}")
        else:
            lines.append("• Correction Types: None")
        
        return lines
    
    @staticmethod
    def format_verify_summary(summary: VerifyOperationSummary) -> list[str]:
        """
        Format verify operation summary for display.
        
        Args:
            summary: VerifyOperationSummary object with verification results
            
        Returns:
            List[str]: Formatted summary lines for display
        """
        lines: list[str] = []
        
        # Images section
        lines.append(f"• ── {summary.images_total} Images ──")
        lines.append(f"• Invalid contents: {summary.images_invalid}")
        lines.append(f"• Incorrect extensions: {summary.images_incorrect}")
        
        # Videos section
        lines.append("")
        lines.append(f"• ── {summary.videos_total} Videos ──")
        lines.append(f"• Invalid contents: {summary.videos_invalid}")
        lines.append(f"• Incorrect extensions: {summary.videos_incorrect}")
        
        return lines
    
    @staticmethod
    def format_verify_summary_title(summary: VerifyOperationSummary) -> str:
        """
        Format verify operation summary title with creator count.
        
        Args:
            summary: VerifyOperationSummary object
            
        Returns:
            str: Formatted title string
        """
        total_creators = summary.creators_processed + summary.creators_failed
        return (
            f"Verification | Summary ({summary.creators_processed}/{total_creators} Creators)"
        )
    
    @staticmethod
    def format_repair_summary(summary: RepairOperationSummary) -> list[str]:
        """
        Format repair operation summary for display.
        
        Args:
            summary: RepairOperationSummary object with repair results
            
        Returns:
            List[str]: Formatted summary lines for display
        """
        lines: list[str] = []
        
        # Overview
        lines.append(f"Creators repaired: {summary.total_creators_repaired()}")
        lines.append(f"Total files removed: {summary.files_removed}")
        lines.append(f"Total files redownloaded: {summary.files_redownloaded}")
        
        # Success indicator
        if summary.all_repairs_successful():
            lines.append("Status: All repairs successful ✓")
        else:
            failed_count = sum(
                1 for removed, redownloaded in summary.per_creator_stats.values()
                if removed != redownloaded
            )
            lines.append(f"Status: {failed_count} repair(s) incomplete")
        
        # InvalidVideos.json status
        if summary.invalid_videos_json_kept:
            lines.append("InvalidVideos.json: Kept (some repairs incomplete)")
        else:
            lines.append("InvalidVideos.json: Removed (cleanup completed)")
        
        return lines
    
    @staticmethod
    def format_repair_summary_title(summary: RepairOperationSummary) -> str:
        """
        Format repair operation summary title.
        
        Args:
            summary: RepairOperationSummary object
            
        Returns:
            str: Formatted title string
        """
        return "Video Repair | Summary"
    
    @staticmethod
    def format_error_items(
        errors: list[tuple[str, str]],
    ) -> list[str]:
        """
        Format error list for display.
        
        Args:
            errors: List of (name, error_message) tuples
            
        Returns:
            List[str]: Formatted error lines
        """
        return [f"✗ {name}: {msg}" for name, msg in errors]
    
    @staticmethod
    def format_failed_creators_title(error_count: int) -> str:
        """
        Format failed creators panel title.
        
        Args:
            error_count: Number of failed creators
            
        Returns:
            str: Formatted title
        """
        return f"Failed Creators ({error_count})"
    
    @staticmethod
    def format_extension_corrections_header(count: int) -> str:
        """
        Format extension corrections header.
        
        Args:
            count: Number of corrections applied
            
        Returns:
            str: Formatted header
        """
        return f"Extension Corrections Applied: {count} file(s)"
    
    @staticmethod
    def format_extension_correction_item(
        path: str, old_ext: str, new_ext: str
    ) -> str:
        """
        Format a single extension correction line.
        
        Args:
            path: File path
            old_ext: Original extension
            new_ext: New extension
            
        Returns:
            str: Formatted correction line
        """
        from pathlib import Path
        filename = Path(path).name
        return f"  [dim]{filename}[/dim]: {old_ext} → {new_ext}"
    
    @staticmethod
    def format_warnings(warnings: list[str]) -> list[str]:
        """
        Format warning list for display.
        
        Args:
            warnings: List of warning messages
            
        Returns:
            List[str]: Formatted warning lines
        """
        return [f"⚠ {warning}" for warning in warnings]
    
    @staticmethod
    def format_warnings_title(warning_count: int) -> str:
        """
        Format warnings panel title.
        
        Args:
            warning_count: Number of warnings
            
        Returns:
            str: Formatted title
        """
        return f"Warnings ({warning_count})"
