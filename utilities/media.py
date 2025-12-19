"""Media file utilities for filename handling and type detection."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from models.types import CIVITAI_CDN_ID, CIVITAI_IMAGE_API_BASE, CIVITAI_VIDEO_PARAMS


def safe_filename_from_url(url: str) -> str:
    """
    Extract a safe filename from a URL.
    
    Args:
        url: The URL to extract filename from
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    path = urlparse(url).path
    filename = os.path.basename(path) or "file.bin"
    
    # Replace unsafe characters
    for ch in ('<', '>', ':', '"', '/', '\\', '|', '?', '*'):
        filename = filename.replace(ch, "_")
    
    return filename


def get_extension_from_url(url: str) -> str:
    """
    Extract file extension from a URL.
    
    Args:
        url: The URL to extract extension from
        
    Returns:
        Lowercase file extension (e.g., '.jpg'), or '.bin' if none found
    """
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    return ext if ext else ".bin"


def media_type_from_extension(
    ext: str,
    image_extensions: list[str],
    video_extensions: list[str],
) -> str:
    """
    Determine media type category from file extension.
    
    Args:
        ext: File extension (e.g., '.jpg')
        image_extensions: List of image extensions
        video_extensions: List of video extensions
        
    Returns:
        'Images', 'Videos', or 'Other'
    """
    if ext in image_extensions:
        return "Images"
    elif ext in video_extensions:
        return "Videos"
    else:
        return "Other"


def update_video_url(url: str, video_extensions: list[str]) -> str:
    """
    Update video URLs to include proper download parameters if needed.
    
    For video files from civitai.com, ensures the URL has the correct format:
    {ImageApiBaseUrl}/{CdnId}/{MediaApiId}/{Parameters}/{MediaApiId}.{Extension}
    
    Only rebuilds the URL if it's missing the required video parameters.
    The media ID and filename remain identical - only the parameters change.
    
    Example:
    https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/80b4f36f-7cbb-4a96-a05a-8d1b060d8a7a/original-video=true,quality=100/80b4f36f-7cbb-4a96-a05a-8d1b060d8a7a.mp4
    
    Args:
        url: Original URL from the API
        video_extensions: List of video extensions to check against
        
    Returns:
        Updated URL for videos with proper parameters, or original URL unchanged
    """
    # Check if this is a video file
    ext = get_extension_from_url(url)
    if ext not in video_extensions:
        return url
    
    # Check if this is a civitai.com URL
    if 'civitai.com' not in url:
        return url
    
    # Check if URL already has the correct video parameters - if so, return unchanged
    # Some API variants use 'original=true' while others use 'original-video=true'.
    # Treat either form as indicating the URL already requests the original-quality
    # video when accompanied by a quality parameter.
    if ('original-video=true' in url or 'original=true' in url) and 'quality=100' in url:
        return url
    
    # Extract filename from URL
    filename = safe_filename_from_url(url)
    
    # Extract media_api_id (filename without extension)
    media_api_id = os.path.splitext(filename)[0]
    
    # Get the file extension (e.g., ".mp4")
    file_extension = ext
    
    # Rebuild URL in the correct format:
    # {ImageApiBaseUrl}/{CdnId}/{MediaApiId}/{Parameters}/{MediaApiId}.{Extension}
    rebuilt_url = (
        f"{CIVITAI_IMAGE_API_BASE}/{CIVITAI_CDN_ID}/{media_api_id}/"
        f"{CIVITAI_VIDEO_PARAMS}/{media_api_id}{file_extension}"
    )
    
    return rebuilt_url