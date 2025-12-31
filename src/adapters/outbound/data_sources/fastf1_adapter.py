"""FastF1 data loader for race control messages and session data."""

import logging
from datetime import datetime
from pathlib import Path

from rich.console import Console

from ....core.domain import PenaltyEvent, RaceResult
from ....core.ports.data_source_port import RaceDataSourcePort

console = Console()
logger = logging.getLogger(__name__)

# Constants
DEFAULT_SEASON = 2025


class FastF1Adapter(RaceDataSourcePort):
    """Loads F1 race data using the FastF1 library."""

    def __init__(self, cache_dir: Path) -> None:
        """Initialize the loader with cache directory.

        Args:
            cache_dir: Directory for FastF1 cache.
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._fastf1_enabled = False
        self._setup_fastf1()

    def _setup_fastf1(self) -> None:
        """Set up FastF1 with caching."""
        try:
            import fastf1

            fastf1.Cache.enable_cache(str(self.cache_dir))
            self._fastf1_enabled = True
            console.print("[green]FastF1 cache enabled[/]")
        except ImportError:
            console.print("[yellow]FastF1 not installed, race data features disabled[/]")
        except Exception as exc:
            console.print(f"[yellow]FastF1 setup warning: {exc}[/]")

    def get_race_control_messages(
        self,
        season: int,
        race_name: str,
        session_type: str = "Race",
    ) -> list[PenaltyEvent]:
        """Get race control messages (penalties, investigations) for a session.

        Args:
            season: The F1 season year.
            race_name: Name of the race (e.g., "Monaco", "Silverstone").
            session_type: Type of session ("Race", "Qualifying", "Sprint", etc.).

        Returns:
            List of PenaltyEvent objects from race control.
        """
        if not self._fastf1_enabled:
            console.print("[yellow]FastF1 not available[/]")
            return []

        import fastf1

        events = []

        try:
            console.print(f"[blue]Loading {race_name} {session_type} {season}...[/]")

            # Get the session
            session = fastf1.get_session(season, race_name, session_type)
            session.load(messages=True)

            # Get race control messages
            if (
                hasattr(session, "race_control_messages")
                and session.race_control_messages is not None
            ):
                rcm = session.race_control_messages

                for _, row in rcm.iterrows():
                    message = row.get("Message", "")
                    time = row.get("Time")
                    driver = None
                    category = "General"

                    # Parse message to extract driver and category
                    message_lower = message.lower()

                    if "investigation" in message_lower:
                        category = "Investigation"
                    elif "penalty" in message_lower:
                        category = "Penalty"
                    elif "track limits" in message_lower or "lap time deleted" in message_lower:
                        category = "Track Limits"
                    elif "black and white" in message_lower:
                        category = "Black/White Flag"
                    elif "unsafe release" in message_lower:
                        category = "Unsafe Release"
                    elif "causing a collision" in message_lower:
                        category = "Collision"

                    # Try to extract driver number/name
                    # Messages often contain car numbers like "CAR 1" or driver codes
                    import re

                    car_match = re.search(r"CAR\s*(\d+)", message, re.I)
                    team = None
                    if car_match:
                        car_number = car_match.group(1)
                        try:
                            # Map car number to driver name
                            drv_info = session.get_driver(car_number)
                            if not drv_info.empty:  # Check if driver found
                                name = drv_info.get(
                                    "BroadcastName", drv_info.get("FullName", "Unknown")
                                )
                                driver = f"{name} ({car_number})"
                                team = drv_info.get("TeamName")
                            else:
                                driver = f"Car {car_number}"
                        except Exception:
                            # Fallback if mapping fails
                            driver = f"Car {car_number}"

                    # Only include penalty-related messages
                    if category != "General":
                        events.append(
                            PenaltyEvent(
                                message=message,
                                driver=driver,
                                team=team,
                                time=time if isinstance(time, datetime) else None,
                                category=category,
                                session=session_type,
                                race_name=race_name,
                                season=season,
                            )
                        )

            console.print(f"  Found {len(events)} penalty-related messages")

        except Exception as exc:
            console.print(f"[red]Error loading session: {exc}[/]")

        return events

    def get_race_results(self, season: int, race_name: str) -> list[RaceResult]:
        """Get race results including post-penalty positions.

        Args:
            season: The F1 season year.
            race_name: Name of the race.

        Returns:
            List of RaceResult objects.
        """
        if not self._fastf1_enabled:
            return []

        import fastf1

        results = []

        try:
            session = fastf1.get_session(season, race_name, "Race")
            session.load()

            if hasattr(session, "results") and session.results is not None:
                for _, row in session.results.iterrows():
                    results.append(
                        RaceResult(
                            position=int(row.get("Position", 0)),
                            driver=row.get("FullName", row.get("Abbreviation", "Unknown")),
                            team=row.get("TeamName", "Unknown"),
                            time_or_status=str(row.get("Time", row.get("Status", ""))),
                            points=float(row.get("Points", 0)),
                            race_name=race_name,
                            season=season,
                        )
                    )

        except Exception as exc:
            console.print(f"[red]Error loading results: {exc}[/]")

        return results

    def get_season_events(self, season: int = DEFAULT_SEASON) -> list[str]:
        """Get list of events/races for a season.

        Args:
            season: The F1 season year.

        Returns:
            List of race names.
        """
        if not self._fastf1_enabled:
            return []

        import fastf1

        try:
            schedule = fastf1.get_event_schedule(season)
            # Filter for actual races (not testing)
            races = schedule[schedule["EventFormat"] != "testing"]
            return races["EventName"].tolist()
        except Exception as exc:
            console.print(f"[yellow]Could not get schedule: {exc}[/]")
            return []

    def get_all_penalties_for_season(self, season: int = DEFAULT_SEASON) -> list[PenaltyEvent]:
        """Get all penalty events for an entire season.

        Args:
            season: The F1 season year.

        Returns:
            List of all PenaltyEvent objects from the season.
        """
        all_events = []
        races = self.get_season_events(season)

        for race in races:
            console.print(f"[blue]Processing {race}...[/]")
            # Get race session penalties
            race_events = self.get_race_control_messages(season, race, "Race")
            all_events.extend(race_events)

            # Also get qualifying penalties
            quali_events = self.get_race_control_messages(season, race, "Qualifying")
            all_events.extend(quali_events)

        console.print(f"[green]Found {len(all_events)} total penalty events for {season}[/]")
        return all_events
