"""SQLite adapter for storing and querying structured F1 statistics."""

import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Allowed SQL patterns for safe query execution (whitelist approach)
ALLOWED_SQL_PATTERNS = [
    r"^SELECT\s+",  # Must start with SELECT
]

# Dangerous SQL patterns that should be blocked
BLOCKED_SQL_PATTERNS = [
    r";\s*\w",  # Multiple statements (SQL injection attempt)
    r"--",  # SQL comments (often used in injection)
    r"/\*",  # Block comments
    r"\bDROP\b",  # DROP statements
    r"\bDELETE\b",  # DELETE statements
    r"\bINSERT\b",  # INSERT statements
    r"\bUPDATE\b",  # UPDATE statements
    r"\bALTER\b",  # ALTER statements
    r"\bCREATE\b",  # CREATE statements
    r"\bTRUNCATE\b",  # TRUNCATE statements
    r"\bEXEC\b",  # EXEC statements
    r"\bATTACH\b",  # ATTACH database
    r"\bDETACH\b",  # DETACH database
    r"\bPRAGMA\b",  # PRAGMA statements (can modify DB settings)
    r"\bVACUUM\b",  # VACUUM statements
    r"\bREINDEX\b",  # REINDEX statements
    r"\bREPLACE\b",  # REPLACE statements
    r"\bUNION\s+ALL\s+SELECT\b.*\bFROM\s+sqlite_",  # sqlite_master access via UNION
]

# Allowed table names (whitelist)
ALLOWED_TABLES = {"penalties"}

# Allowed column names (whitelist)
ALLOWED_COLUMNS = {
    "id", "season", "race_name", "session", "driver",
    "team", "category", "message", "created_at"
}


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

    def _validate_sql_safety(self, query: str) -> tuple[bool, str]:
        """Validate SQL query for safety against injection attacks.

        Args:
            query: SQL query string to validate.

        Returns:
            Tuple of (is_safe, error_message). If safe, error_message is empty.
        """
        query_upper = query.upper().strip()

        # Check if query starts with SELECT
        if not re.match(r"^SELECT\s+", query_upper):
            return False, "Only SELECT queries are allowed for analysis."

        # Check for blocked patterns (SQL injection attempts)
        for pattern in BLOCKED_SQL_PATTERNS:
            if re.search(pattern, query_upper, re.IGNORECASE):
                logger.warning(f"Blocked potentially dangerous SQL pattern: {pattern}")
                return False, "Query contains blocked pattern for security reasons."

        # Extract table references and validate against whitelist
        # Simple pattern to find FROM and JOIN table references
        table_pattern = r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
        referenced_tables = re.findall(table_pattern, query_upper, re.IGNORECASE)

        for table in referenced_tables:
            if table.lower() not in ALLOWED_TABLES:
                logger.warning(f"Query references non-whitelisted table: {table}")
                return False, f"Query references non-allowed table: {table}"

        return True, ""

    def execute_query(self, query: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        """Execute a READ-ONLY SQL query (for Agent use).

        This method includes security validations to prevent SQL injection
        attacks from LLM-generated queries.

        Args:
            query: SQL query string.
            params: Query parameters.

        Returns:
            List of result rows.

        Raises:
            ValueError: If query fails security validation.
        """
        # Validate SQL safety
        is_safe, error_msg = self._validate_sql_safety(query)
        if not is_safe:
            raise ValueError(error_msg)

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            return []
