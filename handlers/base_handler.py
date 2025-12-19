"""Base handler functionality and common patterns.

This module provides base classes and utilities used by all handlers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.operation_results import OperationSummary


class BaseHandler(ABC):
    """Abstract base class for operation handlers.

    All operation handlers inherit from this class to ensure consistent
    interface and behavior patterns.
    """

    @abstractmethod
    def execute(self) -> OperationSummary:
        """Execute the operation and return results.

        Returns:
            OperationSummary: Object describing the operation results
        """
        pass

    def validate_inputs(self) -> bool:
        """Validate that all required inputs are available.

        This method should be called before execute() to ensure
        the handler is properly configured.

        Returns:
            bool: True if all inputs are valid, False otherwise
        """
        return True
