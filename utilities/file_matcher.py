"""File matching utilities for finding files by base name ignoring extension."""

from __future__ import annotations

from pathlib import Path


class FileMatcherUtil:
    """Find files by base name ignoring extension."""
    
    @staticmethod
    def extract_base_name(filename: str) -> str:
        """
        Extract base name from filename (everything before last dot).
        
        Args:
            filename: Filename to parse
            
        Returns:
            Base name in lowercase
        """
        name = Path(filename).stem
        return name.lower()
    
    @staticmethod
    def find_file_by_base_name(
        folder: Path,
        filename: str,
        valid_extensions: list[str],
    ) -> Path | None:
        """
        Find file in folder matching base name, with any valid extension.
        
        Args:
            folder: Folder to search
            filename: Target filename (e.g., 'abc123.mp4')
            valid_extensions: List of extensions to accept (e.g., ['.mp4', '.webm'])
            
        Returns:
            Path to matching file, or None
        """
        folder = Path(folder)
        if not folder.exists() or not folder.is_dir():
            return None
        
        target_base = FileMatcherUtil.extract_base_name(filename)
        
        try:
            for file_path in folder.iterdir():
                if not file_path.is_file():
                    continue
                
                file_base = FileMatcherUtil.extract_base_name(file_path.name)
                
                # Match base name case-insensitively
                if file_base == target_base:
                    # Verify extension is valid
                    if file_path.suffix.lower() in [e.lower() for e in valid_extensions]:
                        return file_path
        except (OSError, PermissionError):
            pass
        
        return None
    
    @staticmethod
    def file_exists_ignoring_extension(
        folder: Path,
        filename: str,
        valid_extensions: list[str],
    ) -> bool:
        """
        Check if file exists in folder by base name, ignoring extension.
        
        Args:
            folder: Folder to search
            filename: Target filename
            valid_extensions: List of valid extensions to accept
            
        Returns:
            True if file with matching base name and valid extension exists
        """
        return FileMatcherUtil.find_file_by_base_name(
            folder, filename, valid_extensions
        ) is not None
