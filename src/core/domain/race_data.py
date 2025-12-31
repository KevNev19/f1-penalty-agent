"""Race data models for FastF1 loaded data."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PenaltyEvent:
    """Represents a penalty or investigation from race control.

    Created from FastF1 race control messages during race sessions.

    Attributes:
        message: The race control message text.
        driver: Driver name or car number, if identified.
        time: Time when the message was issued.
        category: Type of event (Investigation, Penalty, Track Limits, etc.).
        session: Session type (Race, Qualifying, Sprint, etc.).
        race_name: Name of the race event.
        season: F1 season year.
        details: Additional details about the event.
    """

    message: str
    driver: str | None
    time: datetime | None
    category: str  # "Investigation", "Penalty", "Track Limits", "Black/White Flag", etc.
    session: str  # "Race", "Qualifying", "Sprint", etc.
    race_name: str
    season: int
    team: str | None = None
    details: str | None = None


@dataclass
class RaceResult:
    """Simplified race result for context.

    Contains the final classification for a driver in a race.

    Attributes:
        position: Final position (1-20 or DNF position).
        driver: Driver's full name.
        team: Team/constructor name.
        time_or_status: Finishing time gap or DNF status.
        points: Championship points awarded.
        race_name: Name of the race event.
        season: F1 season year.
    """

    position: int
    driver: str
    team: str
    time_or_status: str
    points: float
    race_name: str
    season: int
