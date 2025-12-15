"""
Unit tests for JolpicaClient.

Run with: pytest tests/test_jolpica.py -v
"""

from unittest.mock import patch

import pytest

from src.data.jolpica_client import Driver, JolpicaClient, Race


class TestDriverModel:
    """Tests for Driver dataclass."""

    @pytest.mark.unit
    def test_driver_creation(self):
        """Driver should be creatable with required fields."""
        driver = Driver(
            driver_id="verstappen",
            code="VER",
            name="Max Verstappen",
            nationality="Dutch",
        )
        assert driver.driver_id == "verstappen"
        assert driver.code == "VER"
        assert driver.name == "Max Verstappen"
        assert driver.nationality == "Dutch"
        assert driver.team is None
        assert driver.number is None

    @pytest.mark.unit
    def test_driver_with_optional_fields(self):
        """Driver should accept optional team and number."""
        driver = Driver(
            driver_id="hamilton",
            code="HAM",
            name="Lewis Hamilton",
            nationality="British",
            team="Ferrari",
            number=44,
        )
        assert driver.team == "Ferrari"
        assert driver.number == 44


class TestRaceModel:
    """Tests for Race dataclass."""

    @pytest.mark.unit
    def test_race_creation(self):
        """Race should be creatable with all fields."""
        race = Race(
            round_num=1,
            name="Bahrain Grand Prix",
            circuit="Bahrain International Circuit",
            country="Bahrain",
            date="2025-03-02",
            season=2025,
        )
        assert race.round_num == 1
        assert race.name == "Bahrain Grand Prix"
        assert race.season == 2025


class TestJolpicaClient:
    """Tests for JolpicaClient."""

    @pytest.fixture
    def client(self):
        """Create a JolpicaClient instance."""
        return JolpicaClient()

    @pytest.mark.unit
    def test_client_initialization(self, client):
        """Client should initialize with session."""
        assert client.session is not None
        assert "User-Agent" in client.session.headers

    @pytest.mark.unit
    def test_client_base_url(self, client):
        """Client should have correct base URL."""
        assert client.BASE_URL == "https://api.jolpi.ca/ergast/f1"

    @pytest.mark.unit
    @patch.object(JolpicaClient, "_get")
    def test_get_drivers_success(self, mock_get, client):
        """get_drivers should parse API response correctly."""
        mock_get.return_value = {
            "MRData": {
                "DriverTable": {
                    "Drivers": [
                        {
                            "driverId": "verstappen",
                            "code": "VER",
                            "givenName": "Max",
                            "familyName": "Verstappen",
                            "nationality": "Dutch",
                            "permanentNumber": "1",
                        },
                        {
                            "driverId": "hamilton",
                            "code": "HAM",
                            "givenName": "Lewis",
                            "familyName": "Hamilton",
                            "nationality": "British",
                            "permanentNumber": "44",
                        },
                    ]
                }
            }
        }

        drivers = client.get_drivers(2025)

        assert len(drivers) == 2
        assert drivers[0].code == "VER"
        assert drivers[0].name == "Max Verstappen"
        assert drivers[0].number == 1
        assert drivers[1].code == "HAM"
        assert drivers[1].number == 44

    @pytest.mark.unit
    @patch.object(JolpicaClient, "_get")
    def test_get_drivers_empty_response(self, mock_get, client):
        """get_drivers should return empty list on API failure."""
        mock_get.return_value = None

        drivers = client.get_drivers(2025)

        assert drivers == []

    @pytest.mark.unit
    @patch.object(JolpicaClient, "_get")
    def test_get_drivers_malformed_response(self, mock_get, client):
        """get_drivers should handle malformed API response."""
        mock_get.return_value = {"MRData": {}}  # Missing DriverTable

        drivers = client.get_drivers(2025)

        assert drivers == []

    @pytest.mark.unit
    @patch.object(JolpicaClient, "_get")
    def test_get_races_success(self, mock_get, client):
        """get_races should parse API response correctly."""
        mock_get.return_value = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "round": "1",
                            "raceName": "Bahrain Grand Prix",
                            "Circuit": {
                                "circuitName": "Bahrain International Circuit",
                                "Location": {"country": "Bahrain"},
                            },
                            "date": "2025-03-02",
                        }
                    ]
                }
            }
        }

        races = client.get_races(2025)

        assert len(races) == 1
        assert races[0].name == "Bahrain Grand Prix"
        assert races[0].country == "Bahrain"
        assert races[0].round_num == 1

    @pytest.mark.unit
    @patch.object(JolpicaClient, "_get")
    def test_get_races_empty_response(self, mock_get, client):
        """get_races should return empty list on API failure."""
        mock_get.return_value = None

        races = client.get_races(2025)

        assert races == []

    @pytest.mark.unit
    @patch.object(JolpicaClient, "_get")
    def test_get_driver_standings_success(self, mock_get, client):
        """get_driver_standings should parse standings correctly."""
        mock_get.return_value = {
            "MRData": {
                "StandingsTable": {
                    "StandingsLists": [
                        {"DriverStandings": [{"position": "1", "points": "400", "wins": "15"}]}
                    ]
                }
            }
        }

        standings = client.get_driver_standings(2025)

        assert len(standings) == 1
        assert standings[0]["position"] == "1"

    @pytest.mark.unit
    @patch.object(JolpicaClient, "_get")
    def test_get_driver_standings_empty(self, mock_get, client):
        """get_driver_standings should handle empty standings."""
        mock_get.return_value = {"MRData": {"StandingsTable": {"StandingsLists": []}}}

        standings = client.get_driver_standings(2025)

        assert standings == []

    @pytest.mark.unit
    @patch.object(JolpicaClient, "_get")
    def test_get_race_results_success(self, mock_get, client):
        """get_race_results should parse results correctly."""
        mock_get.return_value = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "Results": [
                                {"position": "1", "Driver": {"code": "VER"}},
                                {"position": "2", "Driver": {"code": "HAM"}},
                            ]
                        }
                    ]
                }
            }
        }

        results = client.get_race_results(2025, 1)

        assert len(results) == 2
        assert results[0]["position"] == "1"

    @pytest.mark.unit
    @patch.object(JolpicaClient, "_get")
    def test_get_race_results_no_races(self, mock_get, client):
        """get_race_results should handle missing race data."""
        mock_get.return_value = {"MRData": {"RaceTable": {"Races": []}}}

        results = client.get_race_results(2025, 1)

        assert results == []

    @pytest.mark.unit
    @patch.object(JolpicaClient, "get_drivers")
    def test_search_driver_by_code(self, mock_get_drivers, client):
        """search_driver should find driver by code."""
        mock_get_drivers.return_value = [
            Driver("verstappen", "VER", "Max Verstappen", "Dutch", number=1),
            Driver("hamilton", "HAM", "Lewis Hamilton", "British", number=44),
        ]

        result = client.search_driver("VER", 2025)

        assert result is not None
        assert result.code == "VER"

    @pytest.mark.unit
    @patch.object(JolpicaClient, "get_drivers")
    def test_search_driver_by_name(self, mock_get_drivers, client):
        """search_driver should find driver by name substring."""
        mock_get_drivers.return_value = [
            Driver("verstappen", "VER", "Max Verstappen", "Dutch", number=1),
        ]

        result = client.search_driver("verstappen", 2025)

        assert result is not None
        assert result.name == "Max Verstappen"

    @pytest.mark.unit
    @patch.object(JolpicaClient, "get_drivers")
    def test_search_driver_by_number(self, mock_get_drivers, client):
        """search_driver should find driver by number."""
        mock_get_drivers.return_value = [
            Driver("hamilton", "HAM", "Lewis Hamilton", "British", number=44),
        ]

        result = client.search_driver("44", 2025)

        assert result is not None
        assert result.number == 44

    @pytest.mark.unit
    @patch.object(JolpicaClient, "get_drivers")
    def test_search_driver_not_found(self, mock_get_drivers, client):
        """search_driver should return None when driver not found."""
        mock_get_drivers.return_value = []

        result = client.search_driver("UNKNOWN", 2025)

        assert result is None

    @pytest.mark.unit
    @patch.object(JolpicaClient, "search_driver")
    @patch.object(JolpicaClient, "get_driver_standings")
    def test_get_driver_context_found(self, mock_standings, mock_search, client):
        """get_driver_context should return formatted context."""
        mock_search.return_value = Driver("verstappen", "VER", "Max Verstappen", "Dutch", number=1)
        mock_standings.return_value = [
            {"Driver": {"code": "VER"}, "position": "1", "points": "400"}
        ]

        context = client.get_driver_context("VER", 2025)

        assert "Max Verstappen" in context
        assert "VER" in context
        assert "P1" in context

    @pytest.mark.unit
    @patch.object(JolpicaClient, "search_driver")
    def test_get_driver_context_not_found(self, mock_search, client):
        """get_driver_context should return error message when driver not found."""
        mock_search.return_value = None

        context = client.get_driver_context("UNKNOWN", 2025)

        assert "Could not find driver" in context

    @pytest.mark.unit
    def test_get_request_error_handling(self, client):
        """_get should handle request errors gracefully."""
        with patch.object(client.session, "get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = client._get("test/endpoint")

            assert result is None
