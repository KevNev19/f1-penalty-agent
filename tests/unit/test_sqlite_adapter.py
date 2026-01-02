"""Unit tests for SQLiteAdapter."""

import sqlite3

import pytest

from src.adapters.outbound.sqlite_adapter import SQLiteAdapter


def test_init_db(tmp_path):
    """Test database initialization and schema creation."""
    db_file = tmp_path / "test.db"
    _adapter = SQLiteAdapter(db_file)  # noqa: F841 - needed to create DB

    # Verify table exists
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='penalties'")
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "penalties"


def test_insert_and_query_penalty(tmp_path):
    """Test inserting a penalty and querying it."""
    db_file = tmp_path / "test_insert.db"
    adapter = SQLiteAdapter(db_file)

    # Insert
    pk = adapter.insert_penalty(
        season=2025,
        race_name="Las Vegas Grand Prix",
        driver="Lando Norris",
        team="McLaren",
        category="Penalty",
        message="5 second time penalty for track limits",
        session="Race",
    )

    assert pk > 0

    # Query specific
    results = adapter.execute_query("SELECT driver, team FROM penalties WHERE season=2025")
    assert len(results) == 1
    assert results[0] == ("Lando Norris", "McLaren")

    # Query with filter
    results = adapter.execute_query("SELECT count(*) FROM penalties WHERE team='Red Bull'")
    assert results[0][0] == 0


def test_clear_season(tmp_path):
    """Test clearing season data."""
    db_file = tmp_path / "test_clear.db"
    adapter = SQLiteAdapter(db_file)

    adapter.insert_penalty(2025, "Race 1", "D1", "C1", "M1")
    adapter.insert_penalty(2025, "Race 2", "D1", "C1", "M1")

    count = adapter.execute_query("SELECT count(*) FROM penalties")[0][0]
    assert count == 2

    adapter.clear_season(2025)

    count = adapter.execute_query("SELECT count(*) FROM penalties")[0][0]
    assert count == 0


def test_invalid_query_prevention(tmp_path):
    """Test that non-SELECT queries raise error."""
    db_file = tmp_path / "test_safety.db"
    adapter = SQLiteAdapter(db_file)

    with pytest.raises(ValueError, match="Only SELECT"):
        adapter.execute_query("DELETE FROM penalties")


class TestSQLSecurityValidation:
    """Test SQL injection prevention in execute_query."""

    def test_blocks_sql_injection_with_semicolon(self, tmp_path):
        """Test that queries with multiple statements are blocked."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        # SQL injection attempt with semicolon
        with pytest.raises(ValueError, match="blocked pattern"):
            adapter.execute_query("SELECT * FROM penalties; DROP TABLE penalties")

    def test_blocks_sql_comments(self, tmp_path):
        """Test that queries with SQL comments are blocked."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        with pytest.raises(ValueError, match="blocked pattern"):
            adapter.execute_query("SELECT * FROM penalties -- comment")

    def test_blocks_drop_statements(self, tmp_path):
        """Test that DROP statements are blocked even in SELECT."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        with pytest.raises(ValueError, match="blocked pattern"):
            adapter.execute_query("SELECT * FROM penalties WHERE 1=1; DROP TABLE penalties")

    def test_blocks_non_whitelisted_tables(self, tmp_path):
        """Test that queries to non-whitelisted tables are blocked."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        with pytest.raises(ValueError, match="non-allowed table"):
            adapter.execute_query("SELECT * FROM sqlite_master")

    def test_blocks_union_sqlite_master_access(self, tmp_path):
        """Test that UNION attacks on sqlite_master are blocked."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        with pytest.raises(ValueError, match="blocked pattern|non-allowed table"):
            adapter.execute_query("SELECT * FROM penalties UNION ALL SELECT * FROM sqlite_master")

    def test_blocks_pragma_statements(self, tmp_path):
        """Test that PRAGMA statements are blocked."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        with pytest.raises(ValueError, match="blocked pattern"):
            adapter.execute_query("SELECT * FROM penalties; PRAGMA table_info(penalties)")

    def test_allows_valid_select_queries(self, tmp_path):
        """Test that valid SELECT queries are allowed."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        # Insert test data
        adapter.insert_penalty(2025, "Monaco GP", "Max Verstappen", "Time", "5s penalty")

        # Valid queries should work
        results = adapter.execute_query("SELECT count(*) FROM penalties")
        assert results[0][0] == 1

        results = adapter.execute_query("SELECT driver FROM penalties WHERE season = 2025")
        assert len(results) == 1

    def test_allows_like_queries(self, tmp_path):
        """Test that LIKE queries are allowed for partial matching."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        adapter.insert_penalty(2025, "Monaco GP", "Lando Norris", "Time", "5s penalty")

        results = adapter.execute_query("SELECT driver FROM penalties WHERE driver LIKE '%Lando%'")
        assert len(results) == 1
        assert results[0][0] == "Lando Norris"

    def test_allows_aggregate_functions(self, tmp_path):
        """Test that aggregate functions are allowed."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        adapter.insert_penalty(2025, "Race 1", "Driver1", "Cat", "Msg")
        adapter.insert_penalty(2025, "Race 2", "Driver2", "Cat", "Msg")

        results = adapter.execute_query("SELECT COUNT(*), team FROM penalties GROUP BY team")
        assert len(results) >= 1

    def test_blocks_double_quoted_table_bypass(self, tmp_path):
        """Test that double-quoted non-whitelisted tables are blocked."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        with pytest.raises(ValueError, match="non-allowed table"):
            adapter.execute_query('SELECT * FROM "sqlite_master"')

    def test_blocks_single_quoted_table_bypass(self, tmp_path):
        """Test that single-quoted non-whitelisted tables are blocked."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        with pytest.raises(ValueError, match="non-allowed table"):
            adapter.execute_query("SELECT * FROM 'sqlite_master'")

    def test_blocks_bracket_quoted_table_bypass(self, tmp_path):
        """Test that bracket-quoted non-whitelisted tables are blocked."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        with pytest.raises(ValueError, match="non-allowed table"):
            adapter.execute_query("SELECT * FROM [sqlite_master]")

    def test_blocks_backtick_quoted_table_bypass(self, tmp_path):
        """Test that backtick-quoted non-whitelisted tables are blocked."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        with pytest.raises(ValueError, match="non-allowed table"):
            adapter.execute_query("SELECT * FROM `sqlite_master`")

    def test_allows_quoted_whitelisted_table(self, tmp_path):
        """Test that quoted whitelisted tables are allowed."""
        db_file = tmp_path / "test_security.db"
        adapter = SQLiteAdapter(db_file)

        adapter.insert_penalty(2025, "Monaco GP", "Max Verstappen", "Time", "5s penalty")

        # Double-quoted whitelisted table should work
        results = adapter.execute_query('SELECT count(*) FROM "penalties"')
        assert results[0][0] == 1
