"""Simple debug logger utilities used when --debug mode is enabled.

Provides an in-memory buffer and a file handler that will be flushed on
finalization (including on exceptions / KeyboardInterrupt).
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path


_logger: logging.Logger | None = None
_buffer: list[str] = []
_log_file: Path | None = None
_subscriber: Callable[[str], None] | None = None


def init_debug(log_dir: Path | None = None) -> logging.Logger:
    """Initialize the debug logger.

    Creates a logger that writes debug messages to a timestamped file inside
    the given log_dir (defaults to cwd). Also keeps a small in-memory buffer
    of messages to ensure they can be flushed on abrupt termination.
    """
    global _logger, _buffer, _log_file

    if _logger is not None:
        return _logger

    log_dir = Path(log_dir) if log_dir is not None else Path.cwd()
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logfile = log_dir / f"civitai_update_debug_{ts}.log"
    _log_file = logfile

    logger = logging.getLogger("civitai_debug")
    logger.setLevel(logging.DEBUG)

    # File handler only (silent on console)
    fh = logging.FileHandler(str(logfile), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Keep reference
    _logger = logger

    # Seed buffer with header
    _buffer.append(f"Debug log initialized: {logfile}\n")

    return logger


def get_logger() -> logging.Logger | None:
    return _logger


def buffer(msg: str, level: str = "DEBUG") -> None:
    """Store a message in the in-memory buffer and send it to logger.

    The in-memory buffer stores lines prefixed with the level (e.g. "INFO: ...").
    The logger is called with the appropriate level so the file output also
    contains a level on the left.
    """
    global _buffer
    try:
        formatted = f"{level}: {msg}"
    except Exception:
        formatted = f"{level}: {str(msg)}"

    _buffer.append(formatted)

    # Emit to file logger at appropriate level
    if _logger is not None:
        try:
            lvl = level.upper()
            if lvl == "DEBUG":
                _logger.debug(msg)
            elif lvl == "INFO":
                _logger.info(msg)
            elif lvl == "WARNING" or lvl == "WARN":
                _logger.warning(msg)
            elif lvl == "ERROR":
                _logger.error(msg)
            elif lvl == "CRITICAL":
                _logger.critical(msg)
            else:
                _logger.debug(msg)
        except Exception:
            pass

    # Notify any subscriber (e.g., display manager) so live UI can show logs
    try:
        if _subscriber is not None:
            try:
                _subscriber(formatted)
            except Exception:
                pass
    except Exception:
        pass


def register_consumer(fn: Callable[[str], None] | None) -> None:
    """Register a function to receive buffered messages as they are added.

    The function should accept a single string argument. Pass None to unregister.
    """
    global _subscriber
    _subscriber = fn


def finalize() -> None:
    """Finalize debug logging by ensuring buffer is written to the log file.

    Safe to call multiple times.
    """
    global _buffer, _log_file

    if _log_file is None:
        return

    try:
        # Append any buffered messages (in case some messages couldn't be logged
        # via the logger). We append them at the end of the file to ensure
        # ordering.
        if _buffer:
            with open(_log_file, "a", encoding="utf-8") as f:
                f.write("\n# In-memory buffer:\n")
                for line in _buffer:
                    f.write(line.rstrip("\n") + "\n")
    except Exception:
        # Best-effort only
        pass
