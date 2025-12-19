"""Unified verification results tracking for both images and videos."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MediaVerificationResults:
    """Results for verifying one media type (Images or Videos)."""
    media_type: str  # "Images" or "Videos"
    checked: int = 0
    invalid: int = 0  # Broken/corrupt files
    incorrect: int = 0  # Files with wrong extension
    
    def has_issues(self) -> bool:
        """Check if there are any issues found."""
        return self.invalid > 0 or self.incorrect > 0
    
    def get_status_line(self) -> str:
        """Get single-line status for this media type."""
        if self.checked == 0:
            return f"✓ No {self.media_type.lower()} found"
        
        issues: list[str] = []
        if self.invalid > 0:
            issues.append(f"{self.invalid} invalid")
        if self.incorrect > 0:
            issues.append(f"{self.incorrect} incorrect extension")
        
        if issues:
            return f"✓ Found {', '.join(issues)} {self.media_type.lower()[:-1]}(s)"
        else:
            return f"✓ All {self.media_type.lower()} valid"


@dataclass
class VerificationSummary:
    """Complete verification results for all creators."""
    creators_processed: int = 0
    creators_failed: int = 0
    images: MediaVerificationResults = field(default_factory=lambda: MediaVerificationResults("Images"))
    videos: MediaVerificationResults = field(default_factory=lambda: MediaVerificationResults("Videos"))
    
    def get_summary_lines(self) -> list[str]:
        """Get formatted summary lines for display."""
        lines: list[str] = []
        
        # Images section
        lines.append(f"• ── {self.images.checked} Images ──")
        lines.append(f"• Invalid contents: {self.images.invalid}")
        lines.append(f"• Incorrect extensions: {self.images.incorrect}")
        
        # Videos section
        lines.append("")
        lines.append(f"• ── {self.videos.checked} Videos ──")
        lines.append(f"• Invalid contents: {self.videos.invalid}")
        lines.append(f"• Incorrect extensions: {self.videos.incorrect}")
        
        return lines
    
    def get_title_with_creators(self) -> str:
        """Get summary title with creator count."""
        total_creators = self.creators_processed + self.creators_failed
        return f"Verification | Summary ({self.creators_processed}/{total_creators} Creators)"
