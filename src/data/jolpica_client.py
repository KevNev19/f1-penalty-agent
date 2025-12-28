"""Jolpica API client for F1 driver and race data (Ergast successor)."""

import logging
from dataclasses import dataclass

import requests
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)

# Constants
REQUEST_TIMEOUT = 30


@dataclass
class Driver:
    """F1 driver information."""

    driver_id: str
    code: str
    name: str
    nationality: str
    team: str | None = None
    number: int | None = None


@dataclass
class Race:
    """F1 race information."""

    round_num: int
    name: str
    circuit: str
    country: str
    date: str
    season: int


class JolpicaClient:
    """Client for the Jolpica API (Ergast successor)."""

    BASE_URL = "https://api.jolpi.ca/ergast/f1"

    def __init__(self) -> None:
        """Initialize the client."""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "F1-Penalty-Agent/1.0"})

    def __enter__(self) -> "JolpicaClient":
        """Enter context manager."""
        return self

    def __exit__(self, *args) -> None:
        """Exit context manager and close session."""
        self.close()

    def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            self.session.close()

    def _get(self, endpoint: str) -> dict | None:
        """Make a GET request to the API.

        Args:
            endpoint: API endpoint path.

        Returns:
            JSON response as dict, or None if request failed.
        """
        url = f"{self.BASE_URL}/{endpoint}.json"
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[red]API error: {e}[/]")
            return None

    def get_drivers(self, season: int = 2025) -> list[Driver]:
        """Get all drivers for a season.

        Args:
            season: The F1 season year.

        Returns:
            List of Driver objects.
        """
        data = self._get(f"{season}/drivers")
        if not data:
            return []

        drivers = []
        try:
            driver_list = data["MRData"]["DriverTable"]["Drivers"]
            for d in driver_list:
                drivers.append(
                    Driver(
                        driver_id=d.get("driverId", ""),
                        code=d.get("code", ""),
                        name=f"{d.get('givenName', '')} {d.get('familyName', '')}".strip(),
                        nationality=d.get("nationality", ""),
                        number=int(d.get("permanentNumber")) if d.get("permanentNumber") else None,
                    )
                )
        except (KeyError, TypeError) as e:
            console.print(f"[yellow]Parse warning: {e}[/]")

        return drivers

    def get_races(self, season: int = 2025) -> list[Race]:
        """Get all races for a season.

        Args:
            season: The F1 season year.

        Returns:
            List of Race objects.
        """
        data = self._get(f"{season}")
        if not data:
            return []

        races = []
        try:
            race_list = data["MRData"]["RaceTable"]["Races"]
            for r in race_list:
                circuit = r.get("Circuit", {})
                location = circuit.get("Location", {})
                races.append(
                    Race(
                        round_num=int(r.get("round", 0)),
                        name=r.get("raceName", ""),
                        circuit=circuit.get("circuitName", ""),
                        country=location.get("country", ""),
                        date=r.get("date", ""),
                        season=season,
                    )
                )
        except (KeyError, TypeError) as e:
            console.print(f"[yellow]Parse warning: {e}[/]")

        return races

    def get_driver_standings(self, season: int = 2025) -> list[dict]:
        """Get driver standings for a season.

        Args:
            season: The F1 season year.

        Returns:
            List of standing entries.
        """
        data = self._get(f"{season}/driverStandings")
        if not data:
            return []

        try:
            standings_list = data["MRData"]["StandingsTable"]["StandingsLists"]
            if standings_list:
                return standings_list[0].get("DriverStandings", [])
        except (KeyError, TypeError, IndexError) as e:
            logger.debug(f"Driver standings parse error: {e}")

        return []

    def get_race_results(self, season: int, round_num: int) -> list[dict]:
        """Get results for a specific race.

        Args:
            season: The F1 season year.
            round_num: Round number of the race.

        Returns:
            List of result entries.
        """
        data = self._get(f"{season}/{round_num}/results")
        if not data:
            return []

        try:
            races = data["MRData"]["RaceTable"]["Races"]
            if races:
                return races[0].get("Results", [])
        except (KeyError, TypeError, IndexError) as e:
            logger.debug(f"Race results parse error: {e}")

        return []

    def search_driver(self, query: str, season: int = 2025) -> Driver | None:
        """Search for a driver by name, code, or number.

        Args:
            query: Search term (name, 3-letter code, or number).
            season: The F1 season year for context.

        Returns:
            Matching Driver or None.
        """
        drivers = self.get_drivers(season)
        query_lower = query.lower().strip()

        for driver in drivers:
            # Match by code (e.g., "VER", "HAM")
            if driver.code.lower() == query_lower:
                return driver
            # Match by full name
            if query_lower in driver.name.lower():
                return driver
            # Match by number
            if driver.number and query_lower == str(driver.number):
                return driver

        return None

    def get_driver_context(self, driver_name: str, season: int = 2025) -> str:
        """Get contextual information about a driver.

        Args:
            driver_name: Driver name or code to look up.
            season: The F1 season year.

        Returns:
            Formatted string with driver context.
        """
        driver = self.search_driver(driver_name, season)
        if not driver:
            return f"Could not find driver: {driver_name}"

        # Get standings for additional context
        standings = self.get_driver_standings(season)
        position = "Unknown"
        points = 0

        for entry in standings:
            entry_driver = entry.get("Driver", {})
            if entry_driver.get("code") == driver.code:
                position = entry.get("position", "Unknown")
                points = entry.get("points", 0)
                break

        return (
            f"Driver: {driver.name} ({driver.code})\n"
            f"Number: {driver.number}\n"
            f"Nationality: {driver.nationality}\n"
            f"Championship Position: P{position} ({points} points)"
        )
