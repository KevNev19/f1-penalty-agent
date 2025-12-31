"""Port definition for analytics data access."""

from typing import Protocol


class AnalyticsPort(Protocol):
    """Port for accessing analytics data (SQL)."""

    def execute_query(self, query: str, params: tuple = ()) -> list[tuple]:
        """Execute a read-only query.

        Args:
            query: SQL query string.
            params: Query parameters.

        Returns:
            List of result rows.
        """
        ...
