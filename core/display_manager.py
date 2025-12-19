"""Unified display manager for console output with Rich library."""

from __future__ import annotations

import re
from collections.abc import Callable
from collections import deque
from datetime import datetime
from re import Match, Pattern

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.text import Text

from models.config import MediaTypeConfig


class DisplayManager:
    """Manages all console output with live updates and progress tracking."""
    
    def __init__(self) -> None:
        """Initialize the display manager."""
        self.console = Console()
        self.live: Live | None = None

        self.creator_name: str = ""

        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_index = 0

        self.api_spinner = Spinner("dots", text="Fetching Api Data", style="orange3")
        self.local_spinner = Spinner("dots", text="Updating Local Data", style="orange3")
        self.repair_removing_spinner = Spinner("dots", style="orange3")
        self.repair_downloading_spinner = Spinner("dots", style="orange3")

        self.api_active: bool = False
        self.api_complete: bool = False
        self.api_pages: int = 0
        self.api_items: int = 0

        self.local_active: bool = False
        self.local_complete: bool = False
        self.local_existing: int = 0
        self.local_total: int = 0
        self.local_downloaded: int = 0
        self.local_to_download: int = 0

        self.verify_images_checked: int = 0
        self.verify_images_total: int = 0
        self.verify_images_invalid: int = 0
        self.verify_images_incorrect: int = 0
        self.verify_images_complete: bool = False

        self.verify_videos_checked: int = 0
        self.verify_videos_total: int = 0
        self.verify_videos_invalid: int = 0
        self.verify_videos_incorrect: int = 0
        self.verify_videos_complete: bool = False

        self.verify_any_active: bool = False

        # Track which media types are enabled for the current creator
        self.images_enabled: bool = True
        self.videos_enabled: bool = True

        self.repair_active: bool = False
        self.repair_complete: bool = False
        self.repair_removing_active: bool = False
        self.repair_removed: int = 0
        self.repair_downloading_active: bool = False
        self.repair_downloaded: int = 0
        self.repair_total: int = 0

        self.header_title: str = ""
        self.header_current: int = 0
        self.header_total: int = 0
        self.show_header_progress: bool = False

        self.use_panel_mode: bool = False
        self.panel_title: str = ""
        self.global_current: int = 0
        self.global_total: int = 0
        self.global_progress = None
        self.global_progress_task = None

        self.debug_enabled: bool = False
        self.debug_lines: deque[tuple[str, str]] = deque()
        self.debug_soft_limit: int = 1000

        # Formatter registry: list of (compiled_pattern, formatter_callable) pairs
        self._formatters: list[tuple[Pattern[str], Callable[[Match[str], str], Text]]] = []
        try:
            self.register_formatter(
                re.compile(r"^Api Request \((?P<user>[^)]+)\):\s*Page\s+(?P<page>\d+)\s*\|\s*Cursor\s+(?P<cursor>\S+)", re.I),
                self._fmt_api_request,
            )
            self.register_formatter(
                re.compile(r"^Api Response \((?P<user>[^)]+)\):\s*Page\s+(?P<page>\d+)\s*\|\s*Items\s+(?P<items>\d+)", re.I),
                self._fmt_api_response,
            )
            self.register_formatter(
                re.compile(r"^Starting processing creator=(?P<creator>[^\s]+)", re.I),
                self._fmt_proc_start,
            )
            self.register_formatter(
                re.compile(r"^Fetched\s+(?P<count>\d+)\s+items\s+for\s+creator=(?P<creator>\S+)", re.I),
                self._fmt_fetched,
            )
            self.register_formatter(
                re.compile(r"^Exported metadata for creator=(?P<creator>\S+)", re.I),
                self._fmt_saved,
            )
            self.register_formatter(
                re.compile(r"^Items matching filter=(?P<match>\d+),\s*needing_download=(?P<need>\d+)\s+for\s+creator=(?P<creator>\S+)", re.I),
                self._fmt_items_filter,
            )
            self.register_formatter(
                re.compile(r"^Downloaded for creator=(?P<creator>[^:]+):\s*files=(?P<files>\d+),\s*images=(?P<images>\d+),\s*videos=(?P<videos>\d+)", re.I),
                self._fmt_downloaded_summary,
            )
            self.register_formatter(
                re.compile(r"^Preparing (?P<media>\w+) for download", re.I),
                self._fmt_preparing_download,
            )
            self.register_formatter(
                re.compile(r"^Downloaded file:\s*(?P<path>\S+)\s+media_type=(?P<media>\w+)", re.I),
                self._fmt_downloaded_file,
            )
            self.register_formatter(
                re.compile(r"^Download failed for url=(?P<url>\S+)", re.I),
                self._fmt_download_failed,
            )
            self.register_formatter(
                re.compile(r"^Creator processed:\s*(?P<username>\S+)\s+api_items=(?P<api_items>\d+)\s+needing_download=(?P<need>\d+)\s+downloaded=(?P<downloaded>\d+)", re.I),
                self._fmt_creator_done,
            )
        except Exception:
            pass

        self.creator_complete: bool = False
        self.creator_media_types: str = ""
        self.global_downloaded: int = 0
        self.global_downloaded_base: int = 0
        self.creator_media_style: str = "bright_cyan"

    def register_formatter(self, pattern: Pattern[str], func: Callable[[Match[str], str], Text]) -> None:
        """Register a pattern + formatter callable.

        The formatter is called with (match, level_style) and must return a Text.
        """
        self._formatters.append((pattern, func))

    def format_message(self, message: str, level_style: str, message_style: str | None = None) -> Text:
        """Format a debug message using the first matching registered formatter.

        The `level_style` is used only for the left-hand level label when
        composing debug lines. `message_style` controls how the message body
        and separators are colored.
        """
        if message_style is None:
            message_style = level_style

        for pattern, func in self._formatters:
            m = pattern.match(message)
            if m:
                try:
                    return func(m, message_style)
                except Exception:
                    break

        msg_text = Text("", overflow="fold")
        url_re = re.compile(r"https?://[^\s)\]>\"]+", re.I)
        last = 0
        for um in url_re.finditer(message):
            start, end = um.span()
            if start > last:
                msg_text.append(message[last:start])
            url = message[start:end]
            url_style = f"link {url} bright_cyan"
            msg_text.append("URL", style=url_style)
            last = end
        if last < len(message):
            msg_text.append(message[last:])
        return msg_text

    def _fmt_api_request(self, m: Match[str], level_style: str) -> Text:
        """Format API request message with linked creator name and timestamp tooltip."""
        user = m.group("user")
        page = m.group("page")
        cursor = m.group("cursor")

        msg_text = Text("", overflow="fold")
        profile = f"https://civitai.com/user/{user}"
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Make "Api Request" text a link that shows timestamp on hover
        msg_text.append("Api Request", style=f"link #{now_ts} deep_sky_blue1")
        msg_text.append(" (", style="deep_sky_blue1")
        msg_text.append(user, style=f"link {profile} bright_cyan underline")
        msg_text.append("): ", style="deep_sky_blue1")
        msg_text.append("Page ", style="bright_blue bold")
        msg_text.append(str(page), style="bright_blue bold")
        msg_text.append(" | ", style=level_style)
        msg_text.append("Cursor ", style="bright_blue bold")
        msg_text.append(str(cursor), style="bright_blue bold")
        return msg_text

    def _fmt_api_response(self, m: Match[str], level_style: str) -> Text:
        """Format API response message with linked timestamp tooltip."""
        user = m.group("user")
        page = m.group("page")
        items = m.group("items")
        
        msg_text = Text("", overflow="fold")
        profile = f"https://civitai.com/user/{user}"
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Make "Api Response" text a link that shows timestamp on hover
        msg_text.append("Api Response", style=f"link #{now_ts} deep_sky_blue1")
        msg_text.append(" (", style="deep_sky_blue1")
        msg_text.append(user, style=f"link {profile} bright_cyan underline")
        msg_text.append("): ", style="deep_sky_blue1")
        msg_text.append("Page ", style="bright_blue bold")
        msg_text.append(str(page), style="bright_blue bold")
        msg_text.append(" | ", style=level_style)
        msg_text.append("Items ", style="bright_blue bold")
        msg_text.append(str(items), style="bright_blue bold")
        return msg_text

    def _fmt_proc_start(self, m: Match[str], level_style: str) -> Text:
        """Format processing start message with linked creator name."""
        creator = m.group("creator")
        msg_text = Text("", overflow="fold")
        profile = f"https://civitai.com/user/{creator}"
        
        # Check if creator is a numeric ID
        is_numeric = creator.isdigit()
        
        msg_text.append("Processing ", style="deep_sky_blue1")
        if is_numeric:
            msg_text.append("creator (", style="deep_sky_blue1")
            msg_text.append(creator, style=f"link {profile} bright_cyan underline")
            msg_text.append(")", style="deep_sky_blue1")
        else:
            msg_text.append(creator, style=f"link {profile} bright_cyan underline")
        return msg_text

    def _fmt_fetched(self, m: Match[str], level_style: str) -> Text:
        count = m.group("count")
        creator = m.group("creator")
        msg_text = Text("", overflow="fold")
        profile = f"https://civitai.com/user/{creator}"
        msg_text.append("Fetched ", style="deep_sky_blue1")
        msg_text.append(str(count), style="bright_blue bold")
        msg_text.append(" items for ", style="deep_sky_blue1")
        msg_text.append(creator, style=f"link {profile} bright_cyan")
        return msg_text

    def _fmt_saved(self, m: Match[str], level_style: str) -> Text:
        """Format metadata export message."""
        creator = m.group("creator")
        msg_text = Text("", overflow="fold")
        profile = f"https://civitai.com/user/{creator}"
        msg_text.append("Exported metadata for ", style="deep_sky_blue1")
        msg_text.append(creator, style=f"link {profile} bright_cyan")
        return msg_text

    def _fmt_items_filter(self, m: Match[str], level_style: str) -> Text:
        match = m.group("match")
        need = m.group("need")
        creator = m.group("creator")
        msg_text = Text("", overflow="fold")
        # Analyzing CreatorName: Found X Missing Y
        profile = f"https://civitai.com/user/{creator}"
        msg_text.append("Analyzing ", style="deep_sky_blue1")
        msg_text.append(creator, style=f"link {profile} bright_cyan")
        msg_text.append(": ", style="deep_sky_blue1")
        msg_text.append("Found ", style="deep_sky_blue1")
        msg_text.append(str(match), style="bright_blue bold")
        msg_text.append(" ", style="deep_sky_blue1")
        msg_text.append("Missing ", style="deep_sky_blue1")
        msg_text.append(str(need), style="bright_blue bold")
        return msg_text

    def _fmt_downloaded_summary(self, m: Match[str], level_style: str) -> Text:
        creator = m.group("creator").strip()
        files = m.group("files")
        images = m.group("images")
        videos = m.group("videos")
        msg_text = Text("", overflow="fold")
        profile = f"https://civitai.com/user/{creator}"
        msg_text.append("Downloaded summary for ", style="deep_sky_blue1")
        msg_text.append(creator, style=f"link {profile} bright_cyan")
        msg_text.append(" | ", style=level_style)
        msg_text.append("files=", style="bright_blue bold")
        msg_text.append(str(files), style="bright_blue bold")
        msg_text.append(" images=", style="bright_blue bold")
        msg_text.append(str(images), style="bright_blue bold")
        msg_text.append(" videos=", style="bright_blue bold")
        msg_text.append(str(videos), style="bright_blue bold")
        return msg_text

    def _fmt_preparing_download(self, m: Match[str], level_style: str) -> Text:
        media = m.group("media").capitalize()
        msg_text = Text("", overflow="fold")
        msg_text.append(f"Preparing {media} for download", style="deep_sky_blue1")
        return msg_text

    def _fmt_downloaded_file(self, m: Match[str], level_style: str) -> Text:
        path = m.group("path")
        media = m.group("media")
        msg_text = Text("", overflow="fold")
        msg_text.append("Downloaded ", style="deep_sky_blue1")
        msg_text.append(path, style="bright_cyan")
        msg_text.append(" | ", style=level_style)
        msg_text.append(media, style="bright_blue bold")
        return msg_text

    def _fmt_download_failed(self, m: Match[str], level_style: str) -> Text:
        url = m.group("url")
        msg_text = Text("", overflow="fold")
        # Keep the failure label neutral so the level label (e.g. [ERROR])
        # carries the red highlighting. The message body remains in the
        # standard message color.
        msg_text.append("Download failed: ", style="deep_sky_blue1")
        url_style = f"link {url} bright_cyan"
        msg_text.append("URL", style=url_style)
        return msg_text

    def _fmt_creator_done(self, m: Match[str], level_style: str) -> Text:
        username = m.group("username")
        api_items = m.group("api_items")
        need = m.group("need")
        downloaded = m.group("downloaded")
        msg_text = Text("", overflow="fold")
        # Processed CreatorName: Media Items (Api) X Missing Y Downloaded Z
        profile = f"https://civitai.com/user/{username}"
        msg_text.append("Processed ", style="deep_sky_blue1")
        msg_text.append(username, style=f"link {profile} bright_cyan")
        msg_text.append(": ", style="deep_sky_blue1")
        msg_text.append("Media Items (Api) ", style="bright_blue bold")
        msg_text.append(str(api_items), style="bright_blue bold")
        msg_text.append(" ", style="deep_sky_blue1")
        msg_text.append("Missing ", style="bright_blue bold")
        msg_text.append(str(need), style="bright_blue bold")
        msg_text.append(" ", style="deep_sky_blue1")
        msg_text.append("Downloaded ", style="bright_blue bold")
        msg_text.append(str(downloaded), style="bright_blue bold")
        return msg_text

    def _create_header_display(self) -> RenderableType:
        """Create header-based display for verification/repair modes."""
        elements: list[RenderableType] = []

        if self.show_header_progress and self.header_total > 0:
            progress_bar_width = 30
            progress_ratio = self.header_current / self.header_total if self.header_total > 0 else 0
            filled_width = int(progress_bar_width * progress_ratio)

            is_complete = self.header_current >= self.header_total
            filled_color = "medium_purple" if is_complete else "magenta"
            empty_color = "dim"

            header_line = Text()
            header_line.append("── ", style="sky_blue1")
            header_line.append(self.header_title, style="bright_cyan")
            header_line.append(" ", style="sky_blue1")

            if filled_width > 0:
                header_line.append("━" * filled_width, style=filled_color)
            if filled_width < progress_bar_width:
                header_line.append("╸", style=filled_color if filled_width > 0 else empty_color)
                if filled_width < progress_bar_width - 1:
                    header_line.append("─" * (progress_bar_width - filled_width - 1), style=empty_color)

            header_line.append(" ", style="sky_blue1")
            header_line.append(f"{self.header_current}", style="bold cyan")
            header_line.append("/", style="dim")
            header_line.append(f"{self.header_total}", style="medium_purple")

            elements.append(header_line)
            elements.append(Text(""))
        
        # Creator name (bigger, bright_cyan, no "Creator:" prefix)
        if self.creator_name and not self.show_header_progress:
            creator_line = Text()
            creator_line.append(self.creator_name, style="bold underline bright_cyan")
            elements.append(creator_line)
        
        # API Fetch Section
        if self.api_active or self.api_complete:
            api_elements: list[RenderableType] = []
            if self.api_active:
                api_elements.append(self.api_spinner)
            else:
                api_elements.append(Text("Fetched Api Data", style="green"))
            api_elements.append(Text(f"Pages: {self.api_pages}"))
            api_elements.append(Text(f"Items: {self.api_items}"))
            if self.api_complete:
                api_elements.append(Text("✓ Successfully saved json data", style="green"))
            elements.append(Group(*api_elements))
            elements.append(Text(""))

        # Local Update Section
        if self.local_active or self.local_complete:
            local_elements: list[RenderableType] = []
            if self.local_active:
                local_elements.append(self.local_spinner)
            else:
                local_elements.append(Text("Updated Local Data", style="green"))

            existing_line = Text.assemble(
                ("Existing: ", ""),
                (str(self.local_existing), "bold cyan"),
                ("/", "dim"),
                (str(self.local_total), "medium_purple")
            )
            local_elements.append(existing_line)

            downloaded_line = Text.assemble(
                ("Downloaded: ", ""),
                (str(self.local_downloaded), "bold cyan"),
                ("/", "dim"),
                (str(self.local_to_download), "medium_purple")
            )
            local_elements.append(downloaded_line)

            if self.local_complete:
                local_elements.append(Text("✓ Successfully processed creator", style="green"))

            elements.append(Group(*local_elements))
            elements.append(Text(""))

        # Images Verification Section
        if self.verify_any_active or self.verify_images_checked > 0 or self.verify_images_total > 0 or self.verify_images_complete:
            images_elements: list[RenderableType] = []
            header_line = Text.assemble(
                ("── Images Verified: ", "sky_blue1"),
                (str(self.verify_images_checked), "bold cyan"),
                ("/", "dim"),
                (str(self.verify_images_total), "medium_purple"),
                (" ── ", "sky_blue1")
            )
            images_elements.append(header_line)
            invalid_line = Text.assemble(
                ("Invalid Contents: ", "orange3"),
                (str(self.verify_images_invalid), "bold orange3")
            )
            images_elements.append(invalid_line)
            incorrect_line = Text.assemble(
                ("Incorrect Extension: ", "orange3"),
                (str(self.verify_images_incorrect), "bold orange3")
            )
            images_elements.append(incorrect_line)

            if self.verify_images_complete:
                if self.verify_images_total == 0:
                    images_elements.append(Text("✓ No images found", style="dim"))
                elif self.verify_images_invalid > 0 or self.verify_images_incorrect > 0:
                    image_issues: list[str] = []
                    if self.verify_images_invalid > 0:
                        image_issues.append(f"{self.verify_images_invalid} invalid")
                    if self.verify_images_incorrect > 0:
                        image_issues.append(f"{self.verify_images_incorrect} incorrect extension")
                    images_elements.append(Text(f"✓ Found {', '.join(image_issues)} image(s)", style="orange3"))
                else:
                    images_elements.append(Text("✓ All images valid", style="green"))

            elements.append(Group(*images_elements))

        # Videos Verification Section
        if self.verify_any_active or self.verify_videos_checked > 0 or self.verify_videos_total > 0 or self.verify_videos_complete:
            videos_elements: list[RenderableType] = []
            header_line = Text.assemble(
                ("── Videos Verified: ", "sky_blue1"),
                (str(self.verify_videos_checked), "bold cyan"),
                ("/", "dim"),
                (str(self.verify_videos_total), "medium_purple"),
                (" ── ", "sky_blue1")
            )
            videos_elements.append(header_line)
            invalid_line = Text.assemble(
                ("Invalid Contents: ", "orange3"),
                (str(self.verify_videos_invalid), "bold orange3")
            )
            videos_elements.append(invalid_line)
            incorrect_line = Text.assemble(
                ("Incorrect Extension: ", "orange3"),
                (str(self.verify_videos_incorrect), "bold orange3")
            )
            videos_elements.append(incorrect_line)

            if self.verify_videos_complete:
                if self.verify_videos_total == 0:
                    videos_elements.append(Text("✓ No videos found", style="dim"))
                elif self.verify_videos_invalid > 0 or self.verify_videos_incorrect > 0:
                    video_issues: list[str] = []
                    if self.verify_videos_invalid > 0:
                        video_issues.append(f"{self.verify_videos_invalid} invalid")
                    if self.verify_videos_incorrect > 0:
                        video_issues.append(f"{self.verify_videos_incorrect} incorrect extension")
                    videos_elements.append(Text(f"✓ Found {', '.join(video_issues)} video(s)", style="orange3"))
                else:
                    videos_elements.append(Text("✓ All videos valid", style="green"))

            elements.append(Group(*videos_elements))

        # Video Repair Section
        if self.repair_active or self.repair_complete:
            repair_elements: list[RenderableType] = []
            if self.repair_removing_active:
                removing_text = f"Removing: {self.repair_removed}/{self.repair_total}"
                self.repair_removing_spinner.text = removing_text
                repair_elements.append(self.repair_removing_spinner)
            elif self.repair_removed > 0:
                removed_line = Text.assemble(
                    ("Removed: ", "green"),
                    (str(self.repair_removed), "bold cyan"),
                    ("/", "dim"),
                    (str(self.repair_total), "medium_purple")
                )
                repair_elements.append(removed_line)

            if self.repair_downloading_active:
                downloading_text = f"Downloading: {self.repair_downloaded}/{self.repair_total}"
                self.repair_downloading_spinner.text = downloading_text
                repair_elements.append(self.repair_downloading_spinner)
            elif self.repair_downloaded > 0:
                downloaded_line = Text.assemble(
                    ("Downloaded: ", "green"),
                    (str(self.repair_downloaded), "bold cyan"),
                    ("/", "dim"),
                    (str(self.repair_total), "medium_purple")
                )
                repair_elements.append(downloaded_line)

            if self.repair_complete:
                repair_elements.append(Text("✓ Successfully processed creator", style="green"))

            if repair_elements:
                elements.append(Group(*repair_elements))
                elements.append(Text(""))

        if self.global_total > 0 and self.global_progress and self.global_progress_task is not None:
            elements.append(Rule(style="dim"))
            elements.append(self.global_progress.get_renderable())

        return Group(*elements)

    def _create_display(self) -> RenderableType:
        """Create the complete display renderable."""
        if self.use_panel_mode:
            return self._create_panel_display()
        else:
            return self._create_header_display()

    def _create_panel_display(self) -> RenderableType:
        """Create panel-based display for update and verify modes."""
        content_elements: list[RenderableType] = []

        # Determine if this is a verify-only mode (no API activity)
        is_verify_only = (
            not self.api_active
            and not self.api_complete
            and not self.local_active
            and not self.local_complete
            and self.verify_any_active
        )

        if self.api_active or self.api_complete:
            if self.api_active:
                content_elements.append(self.api_spinner)
            else:
                content_elements.append(Text("✓ Fetched Api Data", style="green"))
            content_elements.append(Text(f"Pages: {self.api_pages}"))
            content_elements.append(Text(f"Items: {self.api_items}"))
            content_elements.append(Text(""))

        if self.local_complete:
            content_elements.append(Text("✓ Download & Verification", style="green"))
        elif self.local_active:
            self.local_spinner.text = "Download & Verification"
            content_elements.append(self.local_spinner)
        elif not is_verify_only:
            content_elements.append(Text("Download & Verification", style="dim"))

        # Show Images/Videos verification status
        show_verification = (
            self.local_active
            or self.local_complete
            or is_verify_only
            or self.verify_any_active
        )

        if show_verification:
            # Images line
            if self.verify_images_complete:
                if self.verify_images_total == 0:
                    images_line = Text("Images: None")
                elif self.verify_images_invalid > 0 or self.verify_images_incorrect > 0:
                    images_line = Text.assemble(
                        "Images: ",
                        (str(self.verify_images_checked), "bold cyan"),
                        ("/", "dim"),
                        (str(self.verify_images_total), "medium_purple"),
                        (" ⚠ ", "orange3"),
                        (f"{self.verify_images_invalid} invalid", "orange3"),
                    )
                else:
                    images_line = Text.assemble(
                        "Images: ",
                        (str(self.verify_images_checked), "bold cyan"),
                        ("/", "dim"),
                        (str(self.verify_images_total), "medium_purple"),
                        (" ✓", "green"),
                    )
            elif self.verify_images_total > 0:
                images_line = Text.assemble(
                    "Images: ",
                    (str(self.verify_images_checked), "bold cyan"),
                    ("/", "dim"),
                    (str(self.verify_images_total), "medium_purple"),
                )
            elif not self.images_enabled:
                images_line = Text("Images: N/A", style="dim")
            else:
                images_line = Text("Images: (Pending)", style="dim")
            content_elements.append(images_line)

            # Videos line
            if self.verify_videos_complete:
                if self.verify_videos_total == 0:
                    videos_line = Text("Videos: None")
                elif self.verify_videos_invalid > 0 or self.verify_videos_incorrect > 0:
                    videos_line = Text.assemble(
                        "Videos: ",
                        (str(self.verify_videos_checked), "bold cyan"),
                        ("/", "dim"),
                        (str(self.verify_videos_total), "medium_purple"),
                        (" ⚠ ", "orange3"),
                        (f"{self.verify_videos_invalid} invalid", "orange3"),
                    )
                else:
                    videos_line = Text.assemble(
                        "Videos: ",
                        (str(self.verify_videos_checked), "bold cyan"),
                        ("/", "dim"),
                        (str(self.verify_videos_total), "medium_purple"),
                        (" ✓", "green"),
                    )
            elif self.verify_videos_total > 0:
                videos_line = Text.assemble(
                    "Videos: ",
                    (str(self.verify_videos_checked), "bold cyan"),
                    ("/", "dim"),
                    (str(self.verify_videos_total), "medium_purple"),
                )
            elif not self.videos_enabled:
                videos_line = Text("Videos: N/A", style="dim")
            else:
                videos_line = Text("Videos: (Pending)", style="dim")
            content_elements.append(videos_line)
        else:
            # Not active yet — show pending state based on enabled status
            if self.images_enabled:
                content_elements.append(Text("Images: (Pending)", style="dim"))
            else:
                content_elements.append(Text("Images: N/A", style="dim"))
            if self.videos_enabled:
                content_elements.append(Text("Videos: (Pending)", style="dim"))
            else:
                content_elements.append(Text("Videos: N/A", style="dim"))

        panel_content = Group(*content_elements) if content_elements else Text("")

        # Build title based on mode
        title_text = Text()
        if is_verify_only:
            title_text.append("Verification | ", style="bright_blue")
        else:
            title_text.append("Creator Update | ", style="bright_blue")
        title_text.append(
            self.creator_name, style=f"bold underline {self.creator_media_style}"
        )

        if self.creator_media_types:
            title_text.append(" ")
            title_text.append(
                f"({self.creator_media_types})", style=self.creator_media_style
            )
        elif self.global_total > 1:
            title_text.append(" ")
            title_text.append(
                f"({self.global_current + 1}/{self.global_total})", style="medium_purple"
            )

        progress_bar_width = 30
        progress_ratio = self.global_current / self.global_total if self.global_total > 0 else 0
        filled_width = int(progress_bar_width * progress_ratio)

        subtitle_text = Text()
        subtitle_text.append("Progress ", style="deep_sky_blue1")
        if filled_width > 0:
            subtitle_text.append("━" * filled_width, style="bright_blue")
        if filled_width < progress_bar_width:
            subtitle_text.append("━", style="bright_blue" if filled_width > 0 else "dim")
            if filled_width < progress_bar_width - 1:
                subtitle_text.append("━" * (progress_bar_width - filled_width - 1), style="dim")
        subtitle_text.append(f" {self.global_current}/{self.global_total}", style="deep_sky_blue1")

        # Only show Downloaded count for update mode
        if not is_verify_only:
            subtitle_text.append(" | ", style="bright_blue")
            subtitle_text.append("Downloaded: ", style="deep_sky_blue1")
            subtitle_text.append(str(self.global_downloaded), style="deep_sky_blue1")

        main_panel = Panel(
            panel_content,
            title=title_text,
            title_align="left",
            subtitle=subtitle_text,
            subtitle_align="right",
            border_style="bright_blue",
            padding=(1, 2),
            expand=True,
        )

        # If debug panel is enabled, create a secondary panel below the main panel
        if self.debug_enabled:
            # Determine debug panel height based on terminal height and reserve
            # a minimal area for the main panel so the debug panel fills the
            # remaining available space. The panel will expand to full width.

            try:
                term_height = max(8, self.console.size.height)
            except Exception:
                term_height = 24

            # Try to accurately measure how many console lines the main panel
            # will occupy by using Rich's Console.render_lines API with a
            # ConsoleOptions object sized to the current terminal width.
            # This uses the public API documented in Rich and avoids touching
            # internal functions or signatures. If anything fails, fall back
            # to a conservative estimate.
            try:
                try:
                    term_width = max(20, self.console.size.width)
                except Exception:
                    term_width = 80

                # Ask Rich to render the main panel into lines at the current
                # terminal width. Use the ConsoleOptions helper to set width so
                # the signature matches the documented API (options=...).
                options = self.console.options.update_width(term_width)
                rendered = self.console.render_lines(main_panel, options=options, pad=True)
                # render_lines returns a list of lines (each a list of Segments)
                main_lines = max(3, len(rendered))
            except Exception:
                # Conservative estimate: content elements plus overhead for
                # title/subtitle and padding. Using a slightly larger overhead
                # avoids accidentally allocating the whole terminal to debug.
                main_content_lines = len(content_elements)
                main_overhead = 6  # title + subtitle + paddings + buffer
                main_lines = main_content_lines + main_overhead

            # Available lines for debug panel is terminal minus measured main height
            available = term_height - main_lines - 1

            # If little space remains, use a minimal height; otherwise cap at 50
            if available <= 0:
                dbg_height = 1
            else:
                dbg_height = min(50, available)

            # Ensure debug panel never exceeds terminal or is less than 1
            dbg_height = max(1, min(dbg_height, max(1, term_height - 1)))

            # Compute how many stored message lines fit inside the debug panel.
            # Subtract 2 for panel padding/title so messages don't overflow.
            max_stored = max(1, dbg_height - 2)

            # Trim debug_lines so the rendered lines fit in the debug panel.
            # We measure rendered height per message to handle wrapped messages
            # (URLs and long strings) correctly.
            try:
                inner_width = max(20, self.console.size.width - 6)
            except Exception:
                inner_width = 80

            # Available renderable lines inside the debug panel (subtract padding/title)
            avail_lines = max(1, dbg_height - 2)

            # Helper to compute rendered height of a stored message. Use the
            # documented Console.render_lines API with ConsoleOptions sized to
            # the debug inner width. If rendering fails for any entry, fall
            # back to a cheap approximation so the trimming still works.
            def rendered_lines_for(entry: tuple[str, str]) -> int:
                level, message = entry
                level_label = Text(f"[{level}] ", no_wrap=True)
                msg_text = Text(message, overflow="fold")
                combined = Text()
                combined.append(level_label)
                combined.append(msg_text)

                try:
                    opts = self.console.options.update_width(inner_width)
                    lines = self.console.render_lines(combined, options=opts, pad=False)
                    return max(1, len(lines))
                except Exception:
                    # Fallback approximation: explicit newlines + wrap estimate
                    try:
                        newline_count = message.count("\n")
                        approx_chars = len(message.replace("\n", " "))
                        approx = max(1, (approx_chars // max(10, inner_width)) + 1 + newline_count)
                        return approx
                    except Exception:
                        return 1

            # Trim oldest entries until total rendered lines fit
            try:
                total = sum(rendered_lines_for(e) for e in self.debug_lines)
                # Only trim if we're significantly over the limit to avoid flickering
                while total > avail_lines + 2 and len(self.debug_lines) > 1:
                    try:
                        self.debug_lines.popleft()
                    except Exception:
                        break
                    total = sum(rendered_lines_for(e) for e in self.debug_lines)
            except Exception:
                # If sizing fails for any reason, fall back to simple count-based trim
                # Use a more conservative limit to avoid clearing too much
                safe_limit = max(5, max_stored)
                while len(self.debug_lines) > safe_limit:
                    try:
                        self.debug_lines.popleft()
                    except Exception:
                        break

            # Compose debug content; ensure newest lines are at the bottom and add spacing
            dbg_text = Text()
            # Color map for levels
            level_map = {
                "DEBUG": "dim",
                "INFO": "white",
                "WARNING": "yellow",
                "WARN": "yellow",
                "ERROR": "bold red",
                "CRITICAL": "bold white on red",
            }

            for i, (level, message) in enumerate(self.debug_lines):
                level_up = level.upper()
                level_label_style = level_map.get(level_up, "white")

                # Choose a neutral message style so that only the level label
                # is visually highlighted for ERROR/CRITICAL entries. Other
                # levels keep the same style for message text.
                if level_up in ("ERROR", "CRITICAL"):
                    message_style = "deep_sky_blue1"
                else:
                    message_style = level_map.get(level_up, "white")

                # Render level label at left (don't allow it to wrap) and the
                # message with folding so long messages wrap to the panel width.
                level_label = Text(f"[{level}] ", style=level_label_style, no_wrap=True)

                # Build message text using the formatter registry; if no formatter
                # matches the message will fall back to URL replacement inside
                # format_message. Pass message_style so formatters don't color the
                # entire line with the level label color.
                msg_text = self.format_message(message, level_label_style, message_style)

                combined = Text()
                combined.append(level_label)
                combined.append(msg_text)

                dbg_text.append(combined)

                # Single newline between messages
                if i < len(self.debug_lines) - 1:
                    dbg_text.append("\n")

            debug_panel = Panel(
                dbg_text,
                title=Text("Debug Console", style="bold magenta"),
                title_align="left",
                border_style="magenta",
                padding=(1, 2),
                height=dbg_height,
                expand=True,
            )

            # Add an explicit blank line between main and debug panel for visual separation
            return Group(main_panel, Text(""), debug_panel)

        return main_panel

    def _update_display(self) -> None:
        """Update the live display."""
        if self.live:
            self.live.update(self._create_display())

    def enable_debug_panel(self, enabled: bool = True) -> None:
        """Enable or disable the debug console panel.

        When enabled, calls to `debug_log` will append to the live panel.
        """
        self.debug_enabled = enabled
        # Ensure display updates to reflect panel change
        self._update_display()

    def debug_log(self, msg: str) -> None:
        """Append a message to the debug console (newest lines at bottom).

        This will trim oldest messages to fit the available panel size when
        rendering.
        """
        if not self.debug_enabled:
            return

        # Normalize message but keep it as a single stored entry so long
        # messages (URLs, stack traces) are handled as a single logical log
        # item and wrap correctly when rendered.
        try:
            raw = str(msg).rstrip()
            # Detect common level prefixes: [LEVEL] message or LEVEL: message
            m = re.match(r"^\s*\[?(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL)\]?[:\s-]*\s*(.*)$", raw, re.I | re.S)
            if m:
                level = m.group(1).upper()
                message = m.group(2)
            else:
                # No explicit level found; mark as DEBUG by default
                level = "DEBUG"
                message = raw

            # Keep a reasonable cap to avoid unbounded memory use
            if len(self.debug_lines) >= self.debug_soft_limit:
                try:
                    self.debug_lines.popleft()
                except Exception:
                    pass

            self.debug_lines.append((level, message))
        except Exception:
            # Defensive fallback: add the raw message with DEBUG level
            try:
                self.debug_lines.append(("DEBUG", str(msg)))
            except Exception:
                pass

        # Refresh display with updated debug content
        self._update_display()
    
    def start(self) -> None:
        """Start the live display."""
        if not self.live:
            self.live = Live(
                self._create_display(),
                console=self.console,
                refresh_per_second=10,
                transient=False,
                auto_refresh=True,
                screen=True
            )
            self.live.start()
    
    def stop(self, print_final_state: bool = True) -> None:
        """
        Stop the live display.
        
        Args:
            print_final_state: If True, preserve final state to main screen. 
                             If False, clear the display without printing.
        """
        if self.live:
            if print_final_state:
                # Before stopping alternate screen, print the final state to main console
                # This preserves the header and all content when exiting alternate screen
                final_display = self._create_display()
                self.live.stop()
                self.live = None
                # Now print to main screen so it persists
                self.console.print(final_display)
            else:
                # Just stop without printing - caller will display their own content
                self.live.stop()
                self.live = None
        
        # Clean up global progress bar
        if self.global_progress:
            self.global_progress = None
            self.global_progress_task = None
    
    def start_creator(self, creator_name: str, media_config: MediaTypeConfig | None = None) -> None:
        """
        Start processing a new creator.

        Args:
            creator_name: Name of the creator
            media_config: Optional media type configuration for the creator
        """
        # Reset all state
        self.creator_name = creator_name
        # Derive a human-readable media types string from the optional media_config
        if media_config is None:
            self.creator_media_types = ""
            self.creator_media_style = "bright_cyan"
            self.images_enabled = True
            self.videos_enabled = True
        else:
            parts: list[str] = []
            if media_config.images:
                parts.append("Images")
            if media_config.videos:
                parts.append("Videos")
            if media_config.other:
                parts.append("Other")
            self.creator_media_types = " & ".join(parts)
            # Track which media types are enabled
            self.images_enabled = media_config.images
            self.videos_enabled = media_config.videos
            # Choose a style based on selected media types so the creator name
            # can share that color. Prefer distinct colors for clarity.
            has_images = media_config.images
            has_videos = media_config.videos
            if has_images and not has_videos:
                self.creator_media_style = "bright_green"
            elif has_videos and not has_images:
                self.creator_media_style = "medium_purple"
            elif has_images and has_videos:
                self.creator_media_style = "bright_yellow"
            else:
                self.creator_media_style = "bright_cyan"
        self.api_active = False
        self.api_complete = False
        self.api_pages = 0
        self.api_items = 0
        self.local_active = False
        self.local_complete = False
        self.local_existing = 0
        self.local_total = 0
        self.local_downloaded = 0
        self.local_to_download = 0
        self.verify_images_checked = 0
        self.verify_images_total = 0
        self.verify_images_invalid = 0
        self.verify_images_incorrect = 0
        self.verify_images_complete = False
        self.verify_videos_checked = 0
        self.verify_videos_total = 0
        self.verify_videos_invalid = 0
        self.verify_videos_incorrect = 0
        self.verify_videos_complete = False
        self.verify_any_active = False
        self.repair_active = False
        self.repair_complete = False
        self.repair_removing_active = False
        self.repair_removed = 0
        self.repair_downloading_active = False
        self.repair_downloaded = 0
        self.repair_total = 0
        self.creator_complete = False
        
        self._update_display()
    
    def start_api_fetch(self) -> None:
        """Start the API fetch section."""
        self.api_active = True
        self.api_complete = False
        self.api_pages = 0
        self.api_items = 0
        self._update_display()
    
    def update_api_progress(self, pages: int, items: int) -> None:
        """
        Update API fetch progress.
        
        Args:
            pages: Current page count
            items: Current item count
        """
        self.api_pages = pages
        self.api_items = items
        self._update_display()
    
    def complete_api_fetch(self, pages: int, items: int) -> None:
        """
        Complete the API fetch section.
        
        Args:
            pages: Final page count
            items: Final item count
        """
        self.api_pages = pages
        self.api_items = items
        self.api_active = False
        self.api_complete = True
        self._update_display()
    
    def start_local_update(self, existing: int, total: int, to_download: int) -> None:
        """
        Start the local update section.
        
        Args:
            existing: Number of existing files
            total: Total files matching filter
            to_download: Number of files to download
        """
        self.local_active = True
        self.local_complete = False
        self.local_existing = existing
        self.local_total = total
        self.local_downloaded = 0
        self.local_to_download = to_download
        # Also set header progress so the combined total appears in the panel title
        try:
            self.set_header_progress("Files", 0, total)
        except Exception:
            # non-fatal — continue without header progress if it fails
            pass

        self._update_display()
    
    def update_download_progress(self, downloaded: int) -> None:
        """Update download progress for current creator and global total.
        
        Args:
            downloaded: Number of files downloaded so far for current creator
        """
        self.local_downloaded = downloaded
        self.global_downloaded = self.global_downloaded_base + downloaded
        self._update_display()
    
    def complete_local_update(self) -> None:
        """Complete the local update section."""
        self.local_active = False
        self.local_complete = True
        self._update_display()
    
    def activate_download_ui(self, total: int, media_type: str = "Videos") -> None:
        """
        Start verification section for videos or images.
        
        Args:
            total: Total number of files to verify
            media_type: Type of media being verified ("Videos" or "Images")
        """
        self.verify_any_active = True
        
        if media_type == "Images":
            self.verify_images_checked = 0
            self.verify_images_total = total
            self.verify_images_invalid = 0
            self.verify_images_incorrect = 0
            self.verify_images_complete = False
        elif media_type == "Videos":
            self.verify_videos_checked = 0
            self.verify_videos_total = total
            self.verify_videos_invalid = 0
            self.verify_videos_incorrect = 0
            self.verify_videos_complete = False
        
        self._update_display()
    
    def update_verification_progress(self, checked: int, invalid: int, incorrect: int = 0, media_type: str = "Videos") -> None:
        """
        Update verification progress.
        
        Args:
            checked: Number of files checked so far
            invalid: Number of invalid files found so far
            incorrect: Number of files with incorrect extensions
            media_type: Type of media being verified ("Videos" or "Images")
        """
        if media_type == "Images":
            self.verify_images_checked = checked
            self.verify_images_invalid = invalid
            self.verify_images_incorrect = incorrect
        elif media_type == "Videos":
            self.verify_videos_checked = checked
            self.verify_videos_invalid = invalid
            self.verify_videos_incorrect = incorrect
        self._update_display()
    
    def set_total_invalid(self, total_invalid: int) -> None:
        """
        Set the total invalid count across all creators.
        
        Args:
            total_invalid: Total number of invalid files found across all creators
        """
        self.verify_total_invalid = total_invalid
        self._update_display()
    
    def set_total_incorrect(self, total_incorrect: int) -> None:
        """
        Set the total incorrect extension count across all creators.
        
        Args:
            total_incorrect: Total number of files with incorrect extensions across all creators
        """
        self.verify_total_incorrect = total_incorrect
        self._update_display()
    
    def complete_video_verification(self, media_type: str = "Videos") -> None:
        """Mark video or image verification as complete.

        Args:
            media_type: Type of media being verified ("Videos" or "Images")
        """
        if media_type == "Images":
            self.verify_images_complete = True
        elif media_type == "Videos":
            self.verify_videos_complete = True
        self._update_display()

    def set_panel_mode(self, enabled: bool, global_total: int = 0) -> None:
        """
        Enable or disable panel display mode.

        Args:
            enabled: Whether to use panel mode
            global_total: Total number of creators for global progress
        """
        self.use_panel_mode = enabled
        self.global_total = global_total
        self.global_current = 0
        self._update_display()

    def update_global_progress(self, current: int) -> None:
        """
        Update global progress counter.

        Args:
            current: Current creator index
        """
        self.global_current = current
        self._update_display()

    def update_global_downloaded(self, downloaded_total: int) -> None:
        """Update the cumulative downloaded count and set base for next creator.

        This should be called after each creator is processed to update the
        base count for the next creator's incremental downloads.

        Args:
            downloaded_total: Total number of files downloaded across all creators
        """
        self.global_downloaded = downloaded_total
        self.global_downloaded_base = downloaded_total
        self._update_display()
    
    def complete_creator(self) -> None:
        """Mark current creator as complete."""
        self.creator_complete = True
        self._update_display()
    
    def set_header_progress(self, title: str, current: int, total: int) -> None:
        """
        Set the header with progress bar.
        
        Args:
            title: Title to show in header
            current: Current progress count
            total: Total count
        """
        self.header_title = title
        self.header_current = current
        self.header_total = total
        self.show_header_progress = True
        self._update_display()
    
    def start_repair_section(self, total: int) -> None:
        """
        Start the repair section for a creator.
        
        Args:
            total: Total number of videos to repair for this creator
        """
        self.repair_active = True
        self.repair_complete = False
        self.repair_removing_active = False
        self.repair_removed = 0
        self.repair_downloading_active = False
        self.repair_downloaded = 0
        self.repair_total = total
        self._update_display()
    
    def start_removal_phase(self) -> None:
        """Start the removal phase of repair."""
        self.repair_removing_active = True
        self._update_display()
    
    def update_removal_progress(self, removed: int) -> None:
        """
        Update removal progress.
        
        Args:
            removed: Number of files removed so far
        """
        self.repair_removed = removed
        self._update_display()
    
    def complete_removal_phase(self) -> None:
        """Complete the removal phase of repair."""
        self.repair_removing_active = False
        self._update_display()
    
    def start_download_phase(self) -> None:
        """Start the download phase of repair."""
        self.repair_downloading_active = True
        self._update_display()
    
    def update_download_progress_repair(self, downloaded: int) -> None:
        """
        Update download progress during repair.
        
        Args:
            downloaded: Number of files downloaded so far
        """
        self.repair_downloaded = downloaded
        self._update_display()
    
    def complete_download_phase(self) -> None:
        """Complete the download phase of repair."""
        self.repair_downloading_active = False
        self._update_display()
    
    def complete_repair_section(self) -> None:
        """Complete the repair section."""
        self.repair_active = False
        self.repair_complete = True
        self._update_display()
    
    def print_message(self, message: str, style: str = "") -> None:
        """
        Print a standalone message (for errors or final summaries).
        
        Args:
            message: Message to print
            style: Rich style string
        """
        # Temporarily stop live display
        was_live = self.live is not None
        if was_live:
            self.stop()
        
        if style:
            self.console.print(message, style=style)
        else:
            self.console.print(message)
        
        # Restart live display
        if was_live:
            self.start()
    
    def print_separator(self, char: str = "#", width: int = 60) -> None:
        """
        Print a separator line.
        
        Args:
            char: Character to use for separator
            width: Width of separator
        """
        self.print_message(char * width)
    
    def print_final_summary(self, summary_lines: list[str]) -> None:
        """
        Print final aggregate summary after stopping live display.
        
        Args:
            summary_lines: List of summary lines to print
        """
        # Stop live display first
        self.stop()
        
        # Create summary content with markdown bullets
        markdown_content = "\n".join([f"- {line}" for line in summary_lines])
        summary_md = Markdown(markdown_content)
        self.console.print()
        self.console.print(Panel(summary_md, title="[bold cyan]Summary", 
                                 title_align="left", border_style="cyan", padding=(1, 2)))
