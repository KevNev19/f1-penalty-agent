"""Port definition for analytics data access."""

from abc import abstractmethod
from typing import Any, Protocol


class AnalyticsPort(Protocol):
    """Port for accessing analytics."""

    @abstractmethod
    def track_event(
        self,
        event_type: str,
        user_id: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Track an analytics event."""
        pass

    @abstractmethod
    def get_metrics(self, metric_name: str, period: tuple[Any, Any] | None = None) -> Any:
        """Get metrics for a specific period."""
        pass

    @abstractmethod
    def execute_query(self, sql: str) -> list[tuple[Any, ...]]:
        """Execute a SQL query and return results.

        Args:
            sql: SQL query string to execute.

        Returns:
            List of tuples containing query results.
        """
        pass
