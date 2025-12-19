"""Handlers module for Civitai Media Hoarder.

This module contains all operation handlers: update, verify, and repair.
Each handler is responsible for processing an operation and returning
a result object that describes what happened.

Handlers do NOT print results - they return result objects.
Result printing is handled by ResultPrinter after the handler completes.
"""

from handlers.repair_handler import handle_repair_videos
from handlers.update_handler import handle_update
from handlers.verify_handler import handle_verify_unified

__all__ = [
    "handle_repair_videos",
    "handle_update",
    "handle_verify_unified",
]
