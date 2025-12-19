# Civitai Media Hoarder
A command-line tool for downloading and managing media content from Civitai creators. Supports batch downloads, media verification, automatic extension correction, and video repair functionality.

## Features
- **Creator Management**: Add, remove, and update creators in your subscription list
- **Batch Downloads**: Download images and videos from multiple creators at once
- **Media Verification**: Validate downloaded images and videos for corruption
- **Extension Correction**: Automatically detect and fix incorrect file extensions using magic byte detection
- **Video Repair**: Identify and redownload corrupted video files
- **Flexible Filtering**: Configure media types (images, videos, other) per creator or globally
- **Ignore Lists**: Maintain per-creator ignore.txt files to skip specific files
- **Progress Tracking**: Real-time progress display with Rich terminal UI

## Requirements
- Python 3.10 or higher
- ffprobe (for video verification and repair features)
- Civitai API key

### Python Dependencies
```
requests>=2.31.0
rich>=13.0.0
```

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/Mewyk/CivitaiMediaHoarder.git
   cd CivitaiMediaHoarder
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure the application by editing `Configuration.json`:
   ```json
  {
    "api_key": "YOUR_API_KEY",
    "default_output": "Path/To/Output/Directory",
    "nsfw": true,
    "rate_limit": true,
    "request_timeout": 10,
    "download_timeout": 10,
    "max_retries": 2,
    "retry_backoff_sec": 5,
    "image_extensions": [
      ".jpg",
      ".jpeg",
      ".png",
      ".gif",
      ".webp",
      ".bmp",
      ".svg"
    ],
    "video_extensions": [
      ".mp4",
      ".mpg",
      ".mpeg",
      ".webm",
      ".avi",
      ".mov",
      ".mkv"
    ],
    "default_media_types": {
      "images": false,
      "videos": true,
      "other": false
    },
    "memory_threshold_bytes": 2147483648,
    "download_lock_policy": "best_effort"
  }
   ```

## Usage
### Adding Creators
Add one or more creators to your subscription list:
```bash
python main.py --add username1 username2
python main.py --add "username1,username2,username3"
```
With custom media type settings:
```bash
python main.py --add Mewyk --videos-on --images-off
```

### Removing Creators
```bash
python main.py --remove Mewyk
```

### Updating Content
Update specific creators:
```bash
python main.py --update username1 username2
```
Update all creators in your list:
```bash
python main.py --update
```
With options:
```bash
python main.py --update --save-metadata # Save creator metadata to JSON
python main.py --update --auto-purge # Auto remove deleted creators
python main.py --update --ignore-off # Disable ignore.txt filtering
```

### Verifying Media
Verify all media files:
```bash
python main.py --verify
python main.py --verify username1 username2
```
Verify only images:
```bash
python main.py --verify-images
python main.py --verify-images username1
```
Verify only videos:
```bash
python main.py --verify-videos
python main.py --verify-videos username1
```

### Repairing Videos
Repair corrupted videos by redownloading them:
```bash
python main.py --repair
python main.py --repair --yes # Skip confirmation prompts
```

### Debug Mode
Enable debug logging:
```bash
python main.py --update --debug
```
Logs are saved to the `logs/` directory.

## Configuration Options
| Option | Type | Description |
|--------|------|-------------|
| `api_key` | string | Your Civitai API key |
| `default_output` | string | Base directory for downloaded files |
| `nsfw` | boolean | Include NSFW content |
| `rate_limit` | boolean | Enable rate limiting between downloads |
| `request_timeout` | integer | API request timeout in seconds |
| `download_timeout` | integer | File download timeout in seconds |
| `max_retries` | integer | Maximum retry attempts for failed requests |
| `retry_backoff_sec` | integer | Backoff time between retries |
| `image_extensions` | array | List of recognized image file extensions |
| `video_extensions` | array | List of recognized video file extensions |
| `default_media_types` | object | Default media type preferences |
| `creators` | array | List of creators to track |

### Per-Creator Configuration
Creators can be specified as simple strings or objects with custom settings:
```json
{
  "creators": [
    "simple_username",
    {
      "username": "custom_username",
      "media_types": {
        "images": true,
        "videos": false,
        "other": false
      }
    }
  ]
}
```

## Output Structure
Downloaded content is organized by creator:
```
output_folder/
  creator_name/
    Images/
      image1.jpg
      image2.png
    Videos/
      video1.mp4
      video2.webm
    Other/
      file1.zip
    ignore.txt
    creator_name_all_data.json
    creator_name_links.txt
```

## Ignore Lists
Create an `ignore.txt` file in a creator's folder to skip specific files:
```
unwanted_file.mp4
another_file.jpg
```
Files listed here will be skipped during updates.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Troubleshooting
### Video verification fails
Ensure ffprobe is installed and available in your system PATH:
- Windows: `winget install ffmpeg`
- Linux: `sudo apt install ffmpeg`

### API rate limiting
If you encounter rate limiting errors, enable the `rate_limit` option in your configuration to add delays between requests.
### Extension correction
The tool automatically detects file types using magic bytes and corrects extensions when they do not match the actual content. A report of corrections is saved to `ExtensionCorrections.json`.
