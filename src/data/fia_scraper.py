"""FIA document scraper for regulations and stewards decisions."""

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from rich.console import Console
from rich.progress import Progress

console = Console()


@dataclass
class FIADocument:
    """Represents a scraped FIA document."""

    title: str
    url: str
    doc_type: str  # "regulation", "stewards_decision", "guidelines"
    event_name: str | None = None  # For stewards decisions
    season: int = 2025
    local_path: Path | None = None
    text_content: str | None = None


class FIAScraper:
    """Scrapes FIA website for F1 regulations and stewards decisions."""

    # Base URLs for FIA documents
    FIA_BASE_URL = "https://www.fia.com"
    REGULATIONS_URL = "https://www.fia.com/regulation/category/110"  # F1 regulations page
    DECISIONS_BASE_URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14"

    def __init__(self, data_dir: Path) -> None:
        """Initialize the scraper with data directory.

        Args:
            data_dir: Base directory for storing downloaded documents.
        """
        self.data_dir = data_dir
        self.regulations_dir = data_dir / "regulations"
        self.stewards_dir = data_dir / "stewards"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        # Ensure directories exist
        self.regulations_dir.mkdir(parents=True, exist_ok=True)
        self.stewards_dir.mkdir(parents=True, exist_ok=True)

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
            response = self.session.get(self.REGULATIONS_URL, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # Find document links - looking for F1 Sporting Regulations
            doc_links = soup.find_all("a", href=re.compile(r"\.pdf$", re.I))

            for link in doc_links:
                href = link.get("href", "")
                title = link.get_text(strip=True) or href.split("/")[-1]

                # Filter for F1 sporting regulations
                if str(season) in href or str(season) in title:
                    if any(kw in title.lower() or kw in href.lower() 
                           for kw in ["sporting", "regulation", "f1", "formula"]):
                        full_url = urljoin(self.FIA_BASE_URL, href)
                        doc = FIADocument(
                            title=title,
                            url=full_url,
                            doc_type="regulation",
                            season=season,
                        )
                        documents.append(doc)
                        console.print(f"  Found: {title}")

        except requests.RequestException as e:
            console.print(f"[red]Error fetching regulations: {e}[/]")

        return documents

    def scrape_stewards_decisions(
        self, season: int = 2025, race_name: str | None = None
    ) -> list[FIADocument]:
        """Scrape stewards decisions for a season or specific race.

        Args:
            season: The F1 season year.
            race_name: Optional specific race to filter by.

        Returns:
            List of FIADocument objects with stewards decisions.
        """
        console.print(f"[bold blue]Scraping stewards decisions for {season}...[/]")
        documents = []

        # Use the main F1 documents page which lists all recent decisions
        # The season-specific URL often returns 500 errors
        try:
            url = self.DECISIONS_BASE_URL
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # Find all PDF links - FIA uses system/files/decision-document/ path
            all_links = soup.find_all("a", href=re.compile(r"\.pdf$", re.I))

            for link in all_links:
                href = link.get("href", "")
                title = link.get_text(strip=True) or href.split("/")[-1]
                
                # Only include decision documents for the target season
                if str(season) not in href.lower() and str(season) not in title.lower():
                    continue
                
                # Filter for relevant document types
                relevant_keywords = [
                    "infringement", "decision", "offence", "penalty", 
                    "collision", "unsafe", "track", "speeding"
                ]
                href_lower = href.lower()
                title_lower = title.lower()
                
                if not any(kw in href_lower or kw in title_lower for kw in relevant_keywords):
                    continue

                full_url = urljoin(self.FIA_BASE_URL, href)

                # Extract event name from URL or title
                event_name = None
                races = [
                    "bahrain", "saudi", "australia", "japan", "china",
                    "miami", "monaco", "spain", "canada", "austria",
                    "britain", "hungary", "belgium", "netherlands", "italy",
                    "azerbaijan", "singapore", "usa", "mexico", "brazil",
                    "vegas", "qatar", "abu_dhabi", "abu dhabi"
                ]
                for race in races:
                    if race in href_lower or race.replace("_", " ") in title_lower:
                        event_name = race.replace("_", " ").title()
                        break

                # Filter by race if specified
                if race_name and event_name:
                    if race_name.lower() not in event_name.lower():
                        continue

                doc = FIADocument(
                    title=title,
                    url=full_url,
                    doc_type="stewards_decision",
                    event_name=event_name,
                    season=season,
                )
                documents.append(doc)
                console.print(f"  Found: {title[:60]}... ({event_name or 'Unknown race'})")

        except requests.RequestException as e:
            console.print(f"[red]Error fetching stewards decisions: {e}[/]")

        return documents

    def download_document(self, doc: FIADocument) -> FIADocument:
        """Download a document and extract its text content.

        Args:
            doc: FIADocument to download.

        Returns:
            Updated FIADocument with local_path and text_content set.
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

        # Download if not already present
        if not local_path.exists():
            try:
                console.print(f"  Downloading: {doc.title[:60]}...")
                response = self.session.get(doc.url, timeout=60)
                response.raise_for_status()
                local_path.write_bytes(response.content)
            except requests.RequestException as e:
                console.print(f"[red]  Failed to download {doc.title}: {e}[/]")
                return doc

        doc.local_path = local_path

        # Extract text from PDF
        try:
            reader = PdfReader(local_path)
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            doc.text_content = "\n\n".join(text_parts)
        except Exception as e:
            console.print(f"[yellow]  Failed to extract text from {doc.title}: {e}[/]")

        return doc

    def download_all(self, documents: list[FIADocument]) -> list[FIADocument]:
        """Download all documents with progress indicator.

        Args:
            documents: List of documents to download.

        Returns:
            Updated list with downloaded documents.
        """
        with Progress() as progress:
            task = progress.add_task("[cyan]Downloading documents...", total=len(documents))
            for i, doc in enumerate(documents):
                documents[i] = self.download_document(doc)
                progress.update(task, advance=1)

        return documents

    def get_all_documents(self, season: int = 2025) -> list[FIADocument]:
        """Scrape and download all available documents for a season.

        Args:
            season: The F1 season year.

        Returns:
            List of downloaded FIADocument objects with text content.
        """
        all_docs = []

        # Get regulations
        regulations = self.scrape_regulations(season)
        all_docs.extend(regulations)

        # Get stewards decisions
        decisions = self.scrape_stewards_decisions(season)
        all_docs.extend(decisions)

        # Download all
        all_docs = self.download_all(all_docs)

        console.print(f"[green]Downloaded {len(all_docs)} documents[/]")
        return all_docs
