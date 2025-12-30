"""Data Source Port Interfaces."""

from abc import ABC, abstractmethod

from ..domain import FIADocument, PenaltyEvent, RaceResult


class RegulationsSourcePort(ABC):
    """Abstract interface for regulations/FIA data sources."""

    @abstractmethod
    def scrape_regulations(self, season: int) -> list[FIADocument]:
        """Scrape regulations for a season."""
        ...

    @abstractmethod
    def scrape_stewards_decisions(
        self, season: int, race_name: str | None = None
    ) -> list[FIADocument]:
        """Scrape stewards decisions."""
        ...

    @abstractmethod
    def download_document(self, doc: FIADocument) -> bool:
        """Download document content."""
        ...

    @abstractmethod
    def extract_text(self, doc: FIADocument) -> None:
        """Extract text from the document."""
        ...


class RaceDataSourcePort(ABC):
    """Abstract interface for race data sources (FastF1, etc.)."""

    @abstractmethod
    def get_season_events(self, season: int) -> list[str]:
        """Get list of events for a season."""
        ...

    @abstractmethod
    def get_race_control_messages(
        self, season: int, race_name: str, session_type: str = "Race"
    ) -> list[PenaltyEvent]:
        """Get race control messages."""
        ...

    @abstractmethod
    def get_race_results(self, season: int, race_name: str) -> list[RaceResult]:
        """Get race results."""
        ...

    @abstractmethod
    def get_all_penalties_for_season(self, season: int) -> list[PenaltyEvent]:
        """Get all penalties for a season."""
        ...
