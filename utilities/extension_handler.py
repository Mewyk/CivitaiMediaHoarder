"""Extension detection and correction for media files using comprehensive magic byte analysis."""

from __future__ import annotations

from pathlib import Path


class ExtensionHandler:
    """
    Detects actual media types and formats using magic byte analysis.
    
    Supports detection of:
    - Images: JPEG, PNG, GIF, BMP, WebP, TIFF, ICO, HEIC
    - Videos: MP4, MOV, WebM, MKV, AVI, 3GP, QuickTime
    - Audio: MP3, WAV, FLAC, AAC, OGG, M4A
    """
    
    # Magic byte signatures for format detection (more specific signatures first)
    # RIFF requires special handling at offset 8, so it's separate
    SIGNATURES = [
        (b'\xff\xd8\xff', ('image', 'JPEG', '.jpg')),
        (b'\x89PNG\r\n\x1a\n', ('image', 'PNG', '.png')),
        (b'GIF87a', ('image', 'GIF', '.gif')),
        (b'GIF89a', ('image', 'GIF', '.gif')),
        (b'BM', ('image', 'BMP', '.bmp')),
        (b'II*\x00', ('image', 'TIFF', '.tiff')),
        (b'MM\x00*', ('image', 'TIFF', '.tiff')),
        (b'\x00\x00\x01\x00', ('image', 'ICO', '.ico')),
        (b'\xff\xfb', ('audio', 'MP3', '.mp3')),
        (b'ID3', ('audio', 'MP3', '.mp3')),
        (b'\x1a\x45\xdf\xa3', ('video', 'WebM/MKV', '.webm')),
        (b'ftypisom', ('video', 'MP4', '.mp4')),
        (b'ftypmp42', ('video', 'MP4', '.mp4')),
        (b'ftypqt\x00', ('video', 'MOV', '.mov')),
        (b'flac', ('audio', 'FLAC', '.flac')),
        (b'OggS', ('audio', 'OGG', '.ogg')),
        (b'\x00\x00\x00 ftypheic', ('image', 'HEIC', '.heic')),
    ]

    # RIFF container subtypes (checked at offset 8)
    RIFF_SIGNATURES = {
        b'WAVE': ('audio', 'WAV', '.wav'),
        b'AVI ': ('video', 'AVI', '.avi'),
        b'WEBP': ('image', 'WebP', '.webp'),
    }

    
    def detect_format(self, file_path: Path) -> tuple[str, str, str] | None:
        """
        Detect file format using magic byte analysis.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Tuple of (media_type, format_name, extension) or None if cannot determine
            Examples: ('image', 'JPEG', '.jpg'), ('video', 'MP4', '.mp4')
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'rb') as f:
                header = f.read(512)
            
            if not header:
                return None

            if header.startswith(b'RIFF') and len(header) > 12:
                riff_type = header[8:12]
                if riff_type in self.RIFF_SIGNATURES:
                    return self.RIFF_SIGNATURES[riff_type]

            if len(header) > 8 and header[4:8] == b'ftyp':
                ftyp_code = header[8:12]
                if ftyp_code.startswith(b'isom') or ftyp_code.startswith(b'mp4'):
                    return ('video', 'MP4', '.mp4')
                elif ftyp_code.startswith(b'qt'):
                    return ('video', 'MOV', '.mov')
                elif ftyp_code.startswith(b'heic'):
                    return ('image', 'HEIC', '.heic')

            for magic_sig, (media_type, format_name, ext) in self.SIGNATURES:
                if header.startswith(magic_sig):
                    return (media_type, format_name, ext)
            
            return None
        except (IOError, OSError):
            return None
    
    def detect_media_type(self, file_path: Path) -> str | None:
        """
        Detect whether a file is image, video, or audio.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            'image', 'video', 'audio', or None if cannot determine
        """
        result = self.detect_format(file_path)
        if result:
            return result[0]
        return None
    
    def get_correct_extension(
        self,
        file_path: Path,
        image_extensions: list[str],
        video_extensions: list[str],
        audio_extensions: list[str] | None = None,
    ) -> str | None:
        """
        Determine the correct extension based on actual file format.
        
        Uses detected format to find exact extension from configured lists.
        Never falls back or guesses - only returns exact matches from configured extensions.
        Checks all supported extensions (images, videos, audio) to handle edge cases
        like WebP which can be either image or video.
        
        Args:
            file_path: Path to the file to analyze
            image_extensions: List of configured image extensions
            video_extensions: List of configured video extensions
            audio_extensions: List of configured audio extensions (optional)
            
        Returns:
            Correct extension (e.g., '.webp', '.mp4') or None if cannot determine
        """
        detection = self.detect_format(file_path)
        if not detection:
            return None
        
        _media_type, format_name, detected_ext = detection

        all_extensions = list(image_extensions) + list(video_extensions)
        if audio_extensions:
            all_extensions.extend(audio_extensions)

        if detected_ext in all_extensions:
            return detected_ext

        # Handle format variations (e.g., JPEG can be .jpg or .jpeg)
        format_variants = {
            'JPEG': ['.jpg', '.jpeg'],
            'TIFF': ['.tiff', '.tif'],
            'MP3': ['.mp3'],
            'OGG': ['.ogg', '.oga', '.ogv'],
        }

        if format_name in format_variants:
            for variant_ext in format_variants[format_name]:
                if variant_ext in all_extensions:
                    return variant_ext

        return None
    
    
    def validate_and_correct_file(
        self,
        file_path: Path,
        image_extensions: list[str],
        video_extensions: list[str],
        audio_extensions: list[str] | None = None,
        apply_rename: bool = False,
    ) -> Path:
        """
        Validate file format and optionally correct extension mismatch.
        
        Uses magic byte analysis to detect actual format and verify current extension matches.
        Supports format-specific detection with proper fallbacks.
        
        Args:
            file_path: Path to the file to validate
            image_extensions: List of configured image extensions
            video_extensions: List of configured video extensions
            audio_extensions: List of configured audio extensions (optional)
            apply_rename: If True, rename file to correct extension
            
        Returns:
            Path to the file (original or corrected name if renamed)
        """
        file_path = Path(file_path)

        detection = self.detect_format(file_path)
        if not detection:
            return file_path

        _media_type, _format_name, detected_ext = detection
        current_ext = file_path.suffix.lower()

        if current_ext == detected_ext:
            return file_path

        correct_ext = self.get_correct_extension(
            file_path,
            image_extensions,
            video_extensions,
            audio_extensions
        )
        
        if not correct_ext or current_ext == correct_ext:
            return file_path

        if not apply_rename:
            return file_path

        new_path = file_path.with_suffix(correct_ext)

        try:
            if new_path.exists() and new_path != file_path:
                return file_path

            file_path.rename(new_path)
            return new_path
        except (IOError, OSError):
            return file_path

