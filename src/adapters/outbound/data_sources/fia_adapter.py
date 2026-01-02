"""FIA document scraper for regulations and stewards decisions."""

import logging
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from typing import Any, cast
from bs4 import BeautifulSoup, Tag
from pypdf import PdfReader
from rich.console import Console

from ....core.domain import FIADocument
from ....core.domain.utils import normalize_text
from ....core.ports.data_source_port import RegulationsSourcePort

console = Console()
logger = logging.getLogger(__name__)

# Constants
REQUEST_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 60


class FIAAdapter(RegulationsSourcePort):
    """Scrapes FIA website for F1 regulations and stewards decisions."""

    # Base URLs for FIA documents
    FIA_BASE_URL = "https://www.fia.com"
    REGULATIONS_URL = "https://www.fia.com/regulation/category/110"  # F1 regulations page
    DECISIONS_BASE_URL = (
        "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14"
    )

    def __init__(self, data_dir: Path | str) -> None:
        """Initialize the scraper with data directory.

        Args:
            data_dir: Base directory for storing downloaded documents.
        """
        self.data_dir = Path(data_dir) if isinstance(data_dir, str) else data_dir
        self.regulations_dir = self.data_dir / "regulations"
        self.stewards_dir = self.data_dir / "stewards"
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

        # Ensure directories exist
        self.regulations_dir.mkdir(parents=True, exist_ok=True)
        self.stewards_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "FIAAdapter":
        """Enter context manager."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context manager and close session."""
        self.close()

    def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            self.session.close()

    def scrape_regulations(self, season: int = 2025) -> list[FIADocument]:
        """Scrape F1 sporting regulations for a given season.

        Args:
            season: The F1 season year.

        Returns:
            List of FIADocument objects with regulation documents.
        """
        console.print(f"[bold blue]Scraping FIA regulations for {season}...[/]")
        documents = []

        try:
            response = self.session.get(self.REGULATIONS_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # Find document links - looking for F1 Sporting Regulations
            doc_links = soup.find_all("a", href=re.compile(r"\.pdf$", re.I))

            for link in doc_links:
                href = str(link.get("href", ""))
                title = link.get_text(strip=True) or href.split("/")[-1]

                # Filter for F1 sporting regulations
                if str(season) in href or str(season) in title:
                    if any(
                        kw in title.lower() or kw in href.lower()
                        for kw in ["sporting", "regulation", "f1", "formula"]
                    ):
                        full_url = urljoin(self.FIA_BASE_URL, href)
                        doc = FIADocument(
                            title=title,
                            url=full_url,
                            doc_type="regulation",
                            season=season,
                        )
                        documents.append(doc)
                        console.print(f"  Found: {title}")

        except requests.RequestException as exc:
            console.print(f"[red]Error fetching regulations: {exc}[/]")

        return documents

    def _parse_event_name(self, href: str, title: str) -> str | None:
        """Parse event name from link or title."""
        href_lower = href.lower()
        title_lower = title.lower()

        races = [
            "bahrain",
            "saudi",
            "australia",
            "japan",
            "china",
            "miami",
            "monaco",
            "spain",
            "canada",
            "austria",
            "britain",
            "hungary",
            "belgium",
            "netherlands",
            "italy",
            "azerbaijan",
            "singapore",
            "usa",
            "mexico",
            "brazil",
            "vegas",
            "qatar",
            "abu_dhabi",
        ]

        for race in races:
            if race in href_lower or race.replace("_", " ") in title_lower:
                return race.replace("_", " ").title()
        return None

    def _is_relevant_decision(
        self,
        href: str,
        title: str,
        season: int,
        event_name: str | None = None,
        race_filter: str | None = None,
    ) -> bool:
        """Check if a document is relevant based on filters."""
        href_lower = href.lower()
        title_lower = title.lower()

        # Season check
        if str(season) not in href_lower and str(season) not in title_lower:
            return False

        # Keyword check
        relevant_keywords = [
            "infringement",
            "decision",
            "offence",
            "penalty",
            "collision",
            "unsafe",
            "track",
            "speeding",
        ]
        if not any(kw in href_lower or kw in title_lower for kw in relevant_keywords):
            return False

        # Race filter check
        if race_filter and event_name:
            r_lower = race_filter.lower()
            e_lower = event_name.lower()
            if r_lower not in e_lower and e_lower not in r_lower:
                return False

        return True

    def _get_season_events(self, season: int) -> list[tuple[str, str]]:
        """Get all events for a season from the FIA website dropdown.

        Args:
            season: The F1 season year.

        Returns:
            List of (event_name, event_url) tuples.
        """
        events = []

        try:
            # Use the season-specific URL to get the event dropdown
            season_url = f"{self.DECISIONS_BASE_URL}/season/season-{season}-2071"
            response = self.session.get(season_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # Find the event dropdown (facetapi_select_facet_form_2)
            event_select = soup.find("select", id="facetapi_select_facet_form_2")
            if event_select:
                options = event_select.find_all("option")
                for option in options:
                    value = option.get("value", "")
                    text = option.get_text(strip=True)
                    # Skip "Select" placeholder
                    if value and text and text != "Select" and "Select" not in text:
                        # Value is the relative URL path
                        full_url = urljoin(self.FIA_BASE_URL, value)
                        events.append((text, full_url))

            console.print(f"  Found {len(events)} events for {season}")

        except requests.RequestException as exc:
            console.print(f"[yellow]Warning: Could not get event list: {exc}[/]")

        return events

    def _scrape_event_decisions(
        self, event_name: str, event_url: str, season: int
    ) -> list[FIADocument]:
        """Scrape stewards decisions for a specific event.

        Args:
            event_name: The event/race name.
            event_url: The URL to the event's documents page.
            season: The F1 season year.

        Returns:
            List of FIADocument objects.
        """
        documents = []

        try:
            response = self.session.get(event_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # Find all PDF links
            all_links = soup.find_all("a", href=re.compile(r"\.pdf$", re.I))

            for link in all_links:
                href = str(link.get("href", ""))
                title = link.get_text(strip=True) or href.split("/")[-1]

                # Check for relevant keywords
                relevant_keywords = [
                    "infringement",
                    "decision",
                    "offence",
                    "penalty",
                    "collision",
                    "unsafe",
                    "track",
                    "speeding",
                    "exclusion",
                    "disqualif",
                    "classification",
                    "scrutineering",
                ]
                title_lower = title.lower()
                href_lower = href.lower()

                if any(kw in title_lower or kw in href_lower for kw in relevant_keywords):
                    full_url = urljoin(self.FIA_BASE_URL, href)

                    doc = FIADocument(
                        title=title,
                        url=full_url,
                        doc_type="stewards_decision",
                        event_name=event_name,
                        season=season,
                    )
                    documents.append(doc)

        except requests.RequestException as exc:
            console.print(f"[yellow]  Warning: Error fetching {event_name}: {exc}[/]")

        return documents

    def scrape_stewards_decisions(
        self, season: int = 2025, race_name: str | None = None
    ) -> list[FIADocument]:
        """Scrape stewards decisions for all events in a season.

        Args:
            season: The F1 season year.
            race_name: Optional specific race to filter by.

        Returns:
            List of FIADocument objects with stewards decisions.
        """
        console.print(f"[bold blue]Scraping stewards decisions for {season}...[/]")
        documents = []

        # Get all events for the season
        events = self._get_season_events(season)

        if not events:
            # Fallback to original method if we can't get event list
            console.print("[yellow]  Falling back to main page scraping...[/]")
            return self._scrape_main_page_decisions(season, race_name)

        # Filter to specific race if requested
        if race_name:
            race_lower = race_name.lower()
            events = [(name, url) for name, url in events if race_lower in name.lower()]

        # Iterate through each event
        for event_name, event_url in events:
            console.print(f"  [dim]Scraping {event_name}...[/]")
            event_docs = self._scrape_event_decisions(event_name, event_url, season)
            documents.extend(event_docs)
            if event_docs:
                console.print(f"    Found {len(event_docs)} documents")

        console.print(f"[green]  Total: {len(documents)} stewards decisions[/]")
        return documents

    def _scrape_main_page_decisions(
        self, season: int, race_name: str | None = None
    ) -> list[FIADocument]:
        """Fallback: Scrape decisions from main page (latest event only).

        This is the original implementation, kept as fallback.
        """
        documents = []

        try:
            url = self.DECISIONS_BASE_URL
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            all_links = soup.find_all("a", href=re.compile(r"\.pdf$", re.I))

            for link in all_links:
                href = str(link.get("href", ""))
                title = link.get_text(strip=True) or href.split("/")[-1]

                event_name = self._parse_event_name(href, title)

                if self._is_relevant_decision(href, title, season, event_name, race_name):
                    full_url = urljoin(self.FIA_BASE_URL, href)

                    doc = FIADocument(
                        title=title,
                        url=full_url,
                        doc_type="stewards_decision",
                        event_name=event_name,
                        season=season,
                    )
                    documents.append(doc)
                    console.print(f"  Found: {title[:60]}... ({event_name or 'Unknown race'})")

        except requests.RequestException as exc:
            console.print(f"[red]Error fetching stewards decisions: {exc}[/]")

        return documents

    def download_document(self, doc: FIADocument) -> bool:
        """Download a document if it doesn't exist locally.

        Args:
            doc: FIADocument to download.

        Returns:
            True if downloaded, False if skipped (already exists).
        """
        # Determine save location
        if doc.doc_type == "regulation":
            save_dir = self.regulations_dir
        else:
            save_dir = self.stewards_dir

        # Create filename from URL
        filename = doc.url.split("/")[-1]
        if not filename.endswith(".pdf"):
            filename = f"{doc.title[:50].replace(' ', '_')}.pdf"

        local_path = save_dir / filename
        doc.local_path = local_path

        # Download if not already present
        if not local_path.exists():
            try:
                # console.print(f"  Downloading: {doc.title[:60]}...")
                response = self.session.get(doc.url, timeout=DOWNLOAD_TIMEOUT)
                response.raise_for_status()
                local_path.write_bytes(response.content)
                return True
            except requests.RequestException as exc:
                console.print(f"[red]  Failed to download {doc.title}: {exc}[/]")
                return False
        return False

    def extract_text(self, doc: FIADocument) -> None:
        """Extract text content from the local PDF file.

        Args:
            doc: FIADocument with local_path set.
        """
        if not doc.local_path or not doc.local_path.exists():
            return

        try:
            reader = PdfReader(doc.local_path)
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    normalized = normalize_text(text)
                    if normalized:
                        text_parts.append(normalized)
            doc.text_content = "\n\n".join(text_parts)
        except Exception as exc:
            console.print(f"[yellow]  Failed to extract text from {doc.title}: {exc}[/]")

    def get_available_documents(self, season: int = 2025, limit: int = 0) -> list[FIADocument]:
        """Scrape metadata for all available documents (without downloading).

        Args:
            season: The F1 season year.
            limit: Maximum resolution documents to return (0 for all).

        Returns:
            List of FIADocument objects (without text content).
        """
        all_docs = []

        # Get regulations (prioritize these)
        regulations = self.scrape_regulations(season)
        all_docs.extend(regulations)

        # Get stewards decisions
        decisions = self.scrape_stewards_decisions(season)
        all_docs.extend(decisions)

        if limit > 0:
            # If limited, try to get a mix of both types
            # Prioritize regulations but ensure we get some decisions too
            target_regs = min(len(regulations), limit // 2 + (limit % 2))
            target_decs = limit - target_regs

            # If we don't have enough decisions, fill with more regulations
            if target_decs > len(decisions):
                extra_slots = target_decs - len(decisions)
                target_regs = min(len(regulations), target_regs + extra_slots)

            # If we don't have enough regulations, fill with more decisions
            if target_regs > len(regulations):
                extra_slots = target_regs - len(regulations)
                target_decs = min(len(decisions), target_decs + extra_slots)

            return regulations[:target_regs] + decisions[:target_decs]

        return all_docs

    def cleanup_orphaned_files(self, active_documents: list[FIADocument]) -> int:
        """Remove local files that are no longer present in the active documents list.

        Args:
            active_documents: List of currently valid documents from the scrape.

        Returns:
            Number of files removed.
        """
        console.print("[bold blue]Cleaning up orphaned files...[/]")

        # Get set of valid filenames - need to replicate filename logic
        valid_filenames = set()
        for doc in active_documents:
            # Replicate filename logic to know what we expect
            filename = doc.url.split("/")[-1]
            if not filename.endswith(".pdf"):
                filename = f"{doc.title[:50].replace(' ', '_')}.pdf"
            valid_filenames.add(filename)

        removed_count = 0

        # Check regulations directory
        if self.regulations_dir.exists():
            for file_path in self.regulations_dir.glob("*.pdf"):
                if file_path.name not in valid_filenames:
                    try:
                        file_path.unlink()
                        # console.print(f"  [dim]Removed orphaned regulation: {file_path.name}[/]")
                        removed_count += 1
                    except Exception as exc:
                        console.print(f"  [yellow]Failed to remove {file_path.name}: {exc}[/]")

        # Check stewards directory
        if self.stewards_dir.exists():
            for file_path in self.stewards_dir.glob("*.pdf"):
                if file_path.name not in valid_filenames:
                    try:
                        file_path.unlink()
                        # console.print(f"  [dim]Removed orphaned decision: {file_path.name}[/]")
                        removed_count += 1
                    except Exception as exc:
                        console.print(f"  [yellow]Failed to remove {file_path.name}: {exc}[/]")

        if removed_count > 0:
            console.print(f"[green]Removed {removed_count} orphaned files[/]")
        else:
            console.print("[dim]No orphaned files found[/]")

        return removed_count
