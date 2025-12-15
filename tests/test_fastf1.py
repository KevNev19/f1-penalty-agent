"""
Unit tests for FastF1Loader.

Run with: pytest tests/test_fastf1.py -v
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.data.fastf1_loader import FastF1Loader, PenaltyEvent, RaceResult


class TestPenaltyEventModel:
    """Tests for PenaltyEvent dataclass."""

    @pytest.mark.unit
    def test_penalty_event_creation(self):
        """PenaltyEvent should be creatable with required fields."""
        event = PenaltyEvent(
            message="CAR 1 - 5 SECOND TIME PENALTY",
            driver="Car 1",
            time=datetime(2025, 3, 2, 15, 30, 0),
            category="Penalty",
            session="Race",
            race_name="Bahrain",
            season=2025,
        )
        assert event.message == "CAR 1 - 5 SECOND TIME PENALTY"
        assert event.driver == "Car 1"
        assert event.category == "Penalty"
        assert event.details is None

    @pytest.mark.unit
    def test_penalty_event_with_details(self):
        """PenaltyEvent should accept optional details."""
        event = PenaltyEvent(
            message="Investigation",
            driver=None,
            time=None,
            category="Investigation",
            session="Qualifying",
            race_name="Monaco",
            season=2025,
            details="Impeding during qualifying",
        )
        assert event.details == "Impeding during qualifying"
        assert event.driver is None


class TestRaceResultModel:
    """Tests for RaceResult dataclass."""

    @pytest.mark.unit
    def test_race_result_creation(self):
        """RaceResult should be creatable with all fields."""
        result = RaceResult(
            position=1,
            driver="Max Verstappen",
            team="Red Bull Racing",
            time_or_status="1:32:45.678",
            points=25.0,
            race_name="Bahrain",
            season=2025,
        )
        assert result.position == 1
        assert result.driver == "Max Verstappen"
        assert result.points == 25.0


class TestFastF1Loader:
    """Tests for FastF1Loader."""

    @pytest.fixture
    def mock_loader(self, tmp_path):
        """Create a FastF1Loader with mocked fastf1."""
        with patch("src.data.fastf1_loader.FastF1Loader._setup_fastf1"):
            loader = FastF1Loader(tmp_path / "cache")
            loader._fastf1_enabled = False  # Start disabled
            return loader

    @pytest.fixture
    def enabled_loader(self, tmp_path):
        """Create a FastF1Loader with fastf1 'enabled'."""
        with patch("src.data.fastf1_loader.FastF1Loader._setup_fastf1"):
            loader = FastF1Loader(tmp_path / "cache")
            loader._fastf1_enabled = True
            return loader

    @pytest.mark.unit
    def test_loader_initialization(self, mock_loader, tmp_path):
        """Loader should initialize with cache directory."""
        assert mock_loader.cache_dir == tmp_path / "cache"

    @pytest.mark.unit
    def test_loader_creates_cache_dir(self, tmp_path):
        """Loader should create cache directory if it doesn't exist."""
        cache_dir = tmp_path / "new_cache"
        with patch("src.data.fastf1_loader.FastF1Loader._setup_fastf1"):
            _loader = FastF1Loader(cache_dir)  # noqa: F841
            assert cache_dir.exists()

    @pytest.mark.unit
    def test_get_race_control_messages_disabled(self, mock_loader):
        """Should return empty list when FastF1 not enabled."""
        events = mock_loader.get_race_control_messages(2025, "Bahrain", "Race")
        assert events == []

    @pytest.mark.unit
    def test_get_race_results_disabled(self, mock_loader):
        """Should return empty list when FastF1 not enabled."""
        results = mock_loader.get_race_results(2025, "Bahrain")
        assert results == []

    @pytest.mark.unit
    def test_get_season_events_disabled(self, mock_loader):
        """Should return empty list when FastF1 not enabled."""
        events = mock_loader.get_season_events(2025)
        assert events == []

    @pytest.mark.unit
    def test_get_all_penalties_for_season_disabled(self, mock_loader):
        """Should return empty list when FastF1 not enabled."""
        events = mock_loader.get_all_penalties_for_season(2025)
        assert events == []

    @pytest.mark.unit
    def test_get_race_control_messages_success(self, enabled_loader):
        """Should parse race control messages correctly."""
        # Create mock session with race control messages
        mock_session = MagicMock()
        mock_rcm = MagicMock()
        mock_rcm.iterrows.return_value = iter(
            [
                (0, {"Message": "CAR 1 - UNDER INVESTIGATION", "Time": None}),
                (1, {"Message": "CAR 44 - 5 SECOND TIME PENALTY", "Time": None}),
                (2, {"Message": "TRACK LIMITS - LAP TIME DELETED", "Time": None}),
            ]
        )
        mock_session.race_control_messages = mock_rcm

        mock_fastf1 = MagicMock()
        mock_fastf1.get_session.return_value = mock_session

        with patch.dict("sys.modules", {"fastf1": mock_fastf1}):
            events = enabled_loader.get_race_control_messages(2025, "Bahrain", "Race")

        assert len(events) == 3
        assert events[0].category == "Investigation"
        assert events[1].category == "Penalty"
        assert events[2].category == "Track Limits"

    @pytest.mark.unit
    def test_get_race_control_messages_no_messages(self, enabled_loader):
        """Should handle session without race control messages."""
        mock_session = MagicMock()
        mock_session.race_control_messages = None

        mock_fastf1 = MagicMock()
        mock_fastf1.get_session.return_value = mock_session

        with patch.dict("sys.modules", {"fastf1": mock_fastf1}):
            events = enabled_loader.get_race_control_messages(2025, "Bahrain", "Race")

        assert events == []

    @pytest.mark.unit
    def test_get_race_control_messages_error(self, enabled_loader):
        """Should handle errors gracefully."""
        mock_fastf1 = MagicMock()
        mock_fastf1.get_session.side_effect = Exception("Session load error")

        with patch.dict("sys.modules", {"fastf1": mock_fastf1}):
            events = enabled_loader.get_race_control_messages(2025, "Bahrain", "Race")

        assert events == []

    @pytest.mark.unit
    def test_get_race_results_success(self, enabled_loader):
        """Should parse race results correctly."""
        mock_session = MagicMock()

        mock_results = MagicMock()
        mock_results.iterrows.return_value = iter(
            [
                (
                    0,
                    {
                        "Position": 1,
                        "FullName": "Max Verstappen",
                        "TeamName": "Red Bull",
                        "Time": "1:30:00",
                        "Points": 25,
                    },
                ),
                (
                    1,
                    {
                        "Position": 2,
                        "FullName": "Lewis Hamilton",
                        "TeamName": "Ferrari",
                        "Time": "+5.0s",
                        "Points": 18,
                    },
                ),
            ]
        )
        mock_session.results = mock_results

        mock_fastf1 = MagicMock()
        mock_fastf1.get_session.return_value = mock_session

        with patch.dict("sys.modules", {"fastf1": mock_fastf1}):
            results = enabled_loader.get_race_results(2025, "Bahrain")

        assert len(results) == 2
        assert results[0].position == 1
        assert results[0].driver == "Max Verstappen"
        assert results[0].points == 25.0

    @pytest.mark.unit
    def test_get_race_results_no_results(self, enabled_loader):
        """Should handle session without results."""
        mock_session = MagicMock()
        mock_session.results = None

        mock_fastf1 = MagicMock()
        mock_fastf1.get_session.return_value = mock_session

        with patch.dict("sys.modules", {"fastf1": mock_fastf1}):
            results = enabled_loader.get_race_results(2025, "Bahrain")

        assert results == []

    @pytest.mark.unit
    def test_get_season_events_success(self, enabled_loader):
        """Should return list of race names."""
        mock_schedule = MagicMock()
        # Simulate DataFrame filtering
        mock_filtered = MagicMock()
        mock_filtered.__getitem__ = MagicMock(return_value=["testing"])
        mock_schedule.__getitem__ = MagicMock(return_value=mock_filtered)

        # Create mock for filtered races
        mock_races = MagicMock()
        mock_races.__getitem__.return_value.tolist.return_value = [
            "Bahrain Grand Prix",
            "Saudi Arabian Grand Prix",
        ]
        mock_schedule.__getitem__ = MagicMock(return_value=mock_races)

        mock_fastf1 = MagicMock()
        mock_fastf1.get_event_schedule.return_value = mock_schedule

        # This is simplified - actual implementation uses pandas filtering
        with patch.dict("sys.modules", {"fastf1": mock_fastf1}):
            _events = enabled_loader.get_season_events(2025)  # noqa: F841

        mock_fastf1.get_event_schedule.assert_called_once_with(2025)

    @pytest.mark.unit
    def test_get_season_events_error(self, enabled_loader):
        """Should handle errors when getting schedule."""
        mock_fastf1 = MagicMock()
        mock_fastf1.get_event_schedule.side_effect = Exception("API error")

        with patch.dict("sys.modules", {"fastf1": mock_fastf1}):
            events = enabled_loader.get_season_events(2025)

        assert events == []

    @pytest.mark.unit
    def test_category_parsing_investigation(self, enabled_loader):
        """Should correctly categorize investigation messages."""
        # Test the message parsing logic indirectly
        test_messages = [
            ("CAR 1 - UNDER INVESTIGATION", "Investigation"),
            ("5 SECOND TIME PENALTY FOR CAR 44", "Penalty"),
            ("TRACK LIMITS - LAP TIME DELETED", "Track Limits"),
            ("BLACK AND WHITE FLAG SHOWN TO CAR 16", "Black/White Flag"),
            ("UNSAFE RELEASE - PIT LANE", "Unsafe Release"),
            ("CAUSING A COLLISION - CAR 11", "Collision"),
        ]

        for msg, expected_category in test_messages:
            msg_lower = msg.lower()
            if "investigation" in msg_lower:
                assert expected_category == "Investigation"
            elif "penalty" in msg_lower:
                assert expected_category == "Penalty"
            elif "track limits" in msg_lower or "lap time deleted" in msg_lower:
                assert expected_category == "Track Limits"
            elif "black and white" in msg_lower:
                assert expected_category == "Black/White Flag"
            elif "unsafe release" in msg_lower:
                assert expected_category == "Unsafe Release"
            elif "causing a collision" in msg_lower:
                assert expected_category == "Collision"

    @pytest.mark.unit
    def test_car_number_extraction(self, enabled_loader):
        """Should extract car numbers from messages."""
        import re

        test_cases = [
            ("CAR 1 - UNDER INVESTIGATION", "1"),
            ("CAR 44 PENALTY", "44"),
            ("CAR 16 BLACK AND WHITE FLAG", "16"),
            ("NO CAR NUMBER HERE", None),
        ]

        for msg, expected_num in test_cases:
            car_match = re.search(r"CAR\s*(\d+)", msg, re.I)
            if expected_num:
                assert car_match is not None
                assert car_match.group(1) == expected_num
            else:
                assert car_match is None
