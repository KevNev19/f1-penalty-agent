"""SQLite adapter for storing and querying structured F1 statistics."""

import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SQLiteAdapter:
    """Adapter for SQLite database operations."""

    def __init__(self, db_path: str | Path = "data/f1_stats.db") -> None:
        """Initialize the SQLite adapter.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self) -> None:
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _init_db(self) -> None:
        """Initialize the database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create penalties table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS penalties (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        season INTEGER NOT NULL,
                        race_name TEXT NOT NULL,
                        session TEXT,
                        driver TEXT,
                        team TEXT,
                        category TEXT,
                        message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create index for faster searching
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_penalties_season_race
                    ON penalties(season, race_name)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_penalties_driver
                    ON penalties(driver)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_penalties_team
                    ON penalties(team)
                """)

                conn.commit()

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def insert_penalty(
        self,
        season: int,
        race_name: str,
        driver: str,
        category: str,
        message: str,
        session: str = "Race",
        team: str = "Unknown",
    ) -> int:
        """Insert a penalty record.

        Args:
            season: Season year.
            race_name: Name of the race.
            driver: Driver name.
            category: Penalty category.
            message: Penalty message details.
            session: Session type (Race, Qualifying, etc.).
            team: Driver's team/constructor.

        Returns:
            ID of the inserted record.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO penalties (season, race_name, session, driver, team, category, message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (season, race_name, session, driver, team, category, message),
                )
                conn.commit()
                return cursor.lastrowid or 0
        except sqlite3.Error as e:
            logger.error(f"Failed to insert penalty: {e}")
            return 0

    def clear_season(self, season: int) -> None:
        """Clear all records for a specific season.

        Args:
            season: The season to clear.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM penalties WHERE season = ?", (season,))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to clear season {season}: {e}")

    def execute_query(self, query: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        """Execute a READ-ONLY SQL query (for Agent use).

        Args:
            query: SQL query string.
            params: Query parameters.

        Returns:
            List of result rows.
        """
        if not query.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed for analysis.")

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            return []
