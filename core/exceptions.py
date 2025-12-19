"""Custom exceptions for the Civitai Media Hoarder.

This module defines application-specific exceptions that provide clear,
actionable error messages and enable proper error handling throughout
the application.

Exception Hierarchy:
    CivitaiError (base)
    ├── ConfigurationError
    │   ├── ConfigFileNotFoundError
    │   ├── ConfigValidationError
    │   └── InvalidCreatorError
    ├── NetworkError
    │   ├── ApiError
    │   ├── DownloadError
    │   └── UserNotFoundError
    ├── FileOperationError
    │   ├── FileReadError
    │   ├── FileWriteError
    │   └── FileValidationError
    └── MediaError
        ├── InvalidMediaError
        └── ExtensionMismatchError
"""

from __future__ import annotations


class CivitaiError(Exception):
    """Base exception for all Civitai Media Hoarder errors.

    All application-specific exceptions should inherit from this class
    to enable unified exception handling.

    Attributes:
        message: Human-readable error description.
        details: Optional additional context about the error.
    """

    def __init__(self, message: str, details: str | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error description.
            details: Optional additional context about the error.
        """
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


# Configuration Errors


class ConfigurationError(CivitaiError):
    """Base exception for configuration-related errors."""

    pass


class ConfigFileNotFoundError(ConfigurationError):
    """Raised when a required configuration file is missing."""

    def __init__(self, filename: str) -> None:
        """Initialize the exception.

        Args:
            filename: Name of the missing configuration file.
        """
        super().__init__(
            f"Configuration file not found: {filename}",
            "Please create the configuration file. See README.md for details.",
        )
        self.filename = filename


class ConfigValidationError(ConfigurationError):
    """Raised when configuration validation fails."""

    def __init__(self, errors: list[str]) -> None:
        """Initialize the exception.

        Args:
            errors: List of validation error messages.
        """
        error_list = "\n  - ".join(errors)
        super().__init__(
            "Configuration validation failed",
            f"\n  - {error_list}",
        )
        self.errors = errors


class InvalidCreatorError(ConfigurationError):
    """Raised when a creator entry is invalid."""

    def __init__(self, creator: str, reason: str) -> None:
        """Initialize the exception.

        Args:
            creator: The invalid creator identifier.
            reason: Why the creator entry is invalid.
        """
        super().__init__(f"Invalid creator: {creator}", reason)
        self.creator = creator
        self.reason = reason


# Network Errors


class NetworkError(CivitaiError):
    """Base exception for network-related errors."""

    pass


class ApiError(NetworkError):
    """Raised when an API request fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        url: str | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            status_code: HTTP status code if available.
            url: The URL that failed.
        """
        details: list[str] = []
        if status_code is not None:
            details.append(f"Status: {status_code}")
        if url is not None:
            details.append(f"URL: {url}")

        super().__init__(message, " | ".join(details) if details else None)
        self.status_code = status_code
        self.url = url


class DownloadError(NetworkError):
    """Raised when a file download fails."""

    def __init__(
        self,
        filename: str,
        reason: str,
        url: str | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            filename: Name of the file that failed to download.
            reason: Why the download failed.
            url: The download URL if available.
        """
        super().__init__(f"Failed to download: {filename}", reason)
        self.filename = filename
        self.reason = reason
        self.url = url


class UserNotFoundError(NetworkError):
    """Raised when a Civitai user cannot be found."""

    def __init__(self, username: str) -> None:
        """Initialize the exception.

        Args:
            username: The username that was not found.
        """
        super().__init__(
            f"User not found: {username}",
            "The user may have been deleted or the username may be incorrect.",
        )
        self.username = username


# File Operation Errors


class FileOperationError(CivitaiError):
    """Base exception for file operation errors."""

    pass


class FileReadError(FileOperationError):
    """Raised when reading a file fails."""

    def __init__(self, filepath: str, reason: str) -> None:
        """Initialize the exception.

        Args:
            filepath: Path to the file that couldn't be read.
            reason: Why the read operation failed.
        """
        super().__init__(f"Failed to read file: {filepath}", reason)
        self.filepath = filepath


class FileWriteError(FileOperationError):
    """Raised when writing a file fails."""

    def __init__(self, filepath: str, reason: str) -> None:
        """Initialize the exception.

        Args:
            filepath: Path to the file that couldn't be written.
            reason: Why the write operation failed.
        """
        super().__init__(f"Failed to write file: {filepath}", reason)
        self.filepath = filepath


class FileValidationError(FileOperationError):
    """Raised when file validation fails."""

    def __init__(self, filepath: str, reason: str) -> None:
        """Initialize the exception.

        Args:
            filepath: Path to the invalid file.
            reason: Why the validation failed.
        """
        super().__init__(f"File validation failed: {filepath}", reason)
        self.filepath = filepath


# Media Errors


class MediaError(CivitaiError):
    """Base exception for media-related errors."""

    pass


class InvalidMediaError(MediaError):
    """Raised when media content is invalid or corrupted."""

    def __init__(
        self,
        filepath: str,
        media_type: str,
        reason: str,
    ) -> None:
        """Initialize the exception.

        Args:
            filepath: Path to the invalid media file.
            media_type: Type of media (image, video, etc.).
            reason: Why the media is invalid.
        """
        super().__init__(f"Invalid {media_type}: {filepath}", reason)
        self.filepath = filepath
        self.media_type = media_type


class ExtensionMismatchError(MediaError):
    """Raised when a file's extension doesn't match its content."""

    def __init__(
        self,
        filepath: str,
        expected_ext: str,
        actual_ext: str,
    ) -> None:
        """Initialize the exception.

        Args:
            filepath: Path to the file with mismatched extension.
            expected_ext: The extension based on file content.
            actual_ext: The current file extension.
        """
        super().__init__(
            f"Extension mismatch: {filepath}",
            f"Expected {expected_ext}, got {actual_ext}",
        )
        self.filepath = filepath
        self.expected_ext = expected_ext
        self.actual_ext = actual_ext
