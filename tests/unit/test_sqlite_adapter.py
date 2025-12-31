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
