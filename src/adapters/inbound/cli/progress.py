"""Progress tracking utilities for CLI setup command.

This module provides a unified progress tracking system using Rich library
for displaying intuitive, phase-based progress during data ingestion.
"""

from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)


class Phase(Enum):
    """Setup phases for progress tracking."""

    DISCOVERY = "discovery"
    DOWNLOAD = "download"
    EMBED = "embed"
    INDEX = "index"


# Phase icons and colors
PHASE_CONFIG = {
    Phase.DISCOVERY: {"icon": "🔍", "color": "cyan", "verb": "Discovering"},
    Phase.DOWNLOAD: {"icon": "⏬", "color": "blue", "verb": "Downloading"},
    Phase.EMBED: {"icon": "🧠", "color": "magenta", "verb": "Embedding"},
    Phase.INDEX: {"icon": "💾", "color": "green", "verb": "Indexing"},
}


@dataclass
class PhaseStats:
    """Statistics for a single phase."""

    total: int = 0
    processed: int = 0
    new: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass
class DataTypeStats:
    """Statistics for a data type (regulations, stewards, race)."""

    name: str
    icon: str
    phases: dict[Phase, PhaseStats] = field(default_factory=dict)
    total_indexed: int = 0
    total_skipped: int = 0
    total_chunks: int = 0


class SetupProgress:
    """Unified progress tracker for setup operations.

    Provides visual feedback for multi-phase data ingestion with:
    - Phase-based progress (discovery → download → embed → index)
    - Progress bars with N/M counts
    - Skipped vs new item tracking
    - Final summary statistics
    """

    def __init__(self, console: Console | None = None):
        """Initialize the progress tracker.

        Args:
            console: Rich console instance. Creates new one if not provided.
        """
        self.console = console or Console()
        self._current_data_type: DataTypeStats | None = None
        self._current_phase: Phase | None = None
        self._progress: Progress | None = None
        self._task_id: TaskID | None = None
        self._live: Live | None = None
        self._all_stats: list[DataTypeStats] = []

    def start_data_type(self, name: str, icon: str) -> None:
        """Start processing a new data type (e.g., regulations, stewards).

        Args:
            name: Display name for the data type
            icon: Emoji icon for the data type
        """
        # Finish previous if any
        if self._current_data_type:
            self._finish_current_data_type()

        self._current_data_type = DataTypeStats(name=name, icon=icon)
        self.console.print(f"\n{icon} [bold]{name}[/]")

    def start_phase(
        self,
        phase: Phase,
        total: int,
        description: str = "",
    ) -> None:
        """Start a new phase within the current data type.

        Args:
            phase: The phase to start
            total: Total items to process in this phase
            description: Optional description to show
        """
        if not self._current_data_type:
            raise RuntimeError("Must call start_data_type before start_phase")

        # End previous phase if any
        if self._progress and self._live:
            self._live.stop()
            self._progress = None
            self._live = None

        config = PHASE_CONFIG[phase]
        self._current_phase = phase
        self._current_data_type.phases[phase] = PhaseStats(total=total)

        # Show phase header
        phase_text = f"├─ {config['icon']} {config['verb']}"
        if description:
            phase_text += f": {description}"
        elif total > 0:
            phase_text += f": {total} items"
        self.console.print(f"[{config['color']}]{phase_text}[/]")

        # Create progress bar for phases with multiple items
        if total > 1:
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=30),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                console=self.console,
                transient=True,
            )
            self._task_id = self._progress.add_task(
                description=f"{config['verb']}...",
                total=total,
            )
            self._live = Live(self._progress, console=self.console, refresh_per_second=4)
            self._live.start()

    def update(
        self,
        current: int | None = None,
        item_name: str = "",
        advance: int = 1,
    ) -> None:
        """Update progress within current phase.

        Args:
            current: Absolute progress value (if None, advances by `advance`)
            item_name: Name of current item being processed
            advance: Amount to advance if current not specified
        """
        if self._progress and self._task_id is not None:
            config = PHASE_CONFIG.get(self._current_phase, {})
            verb = config.get("verb", "Processing")

            # Truncate long item names
            display_name = item_name[:40] + "..." if len(item_name) > 40 else item_name
            description = f"{verb}: {display_name}" if display_name else f"{verb}..."

            if current is not None:
                self._progress.update(self._task_id, completed=current, description=description)
            else:
                self._progress.update(self._task_id, advance=advance, description=description)

        # Update stats
        if self._current_data_type and self._current_phase:
            stats = self._current_data_type.phases.get(self._current_phase)
            if stats:
                stats.processed += advance

    def mark_skipped(self, item_name: str = "") -> None:
        """Mark current item as skipped (already indexed).

        Args:
            item_name: Name of skipped item (for logging)
        """
        if self._current_data_type and self._current_phase:
            stats = self._current_data_type.phases.get(self._current_phase)
            if stats:
                stats.skipped += 1
        self.update(item_name=item_name)

    def mark_new(self, item_name: str = "") -> None:
        """Mark current item as new (will be indexed).

        Args:
            item_name: Name of new item (for logging)
        """
        if self._current_data_type and self._current_phase:
            stats = self._current_data_type.phases.get(self._current_phase)
            if stats:
                stats.new += 1
        self.update(item_name=item_name)

    def mark_failed(self, item_name: str = "", error: str = "") -> None:
        """Mark current item as failed.

        Args:
            item_name: Name of failed item
            error: Error message
        """
        if self._current_data_type and self._current_phase:
            stats = self._current_data_type.phases.get(self._current_phase)
            if stats:
                stats.failed += 1

        if error:
            self.console.print(f"│  [red]✗ {item_name[:30]}: {error[:50]}[/]")
        self.update(item_name=item_name)

    def end_phase(self, message: str = "") -> PhaseStats:
        """End the current phase and return stats.

        Args:
            message: Optional completion message

        Returns:
            Statistics for the completed phase
        """
        stats = PhaseStats()

        if self._progress and self._live:
            self._live.stop()
            self._progress = None
            self._live = None
            self._task_id = None

        if self._current_data_type and self._current_phase:
            stats = self._current_data_type.phases.get(self._current_phase, PhaseStats())

            # Show phase summary
            summary_parts = []
            if stats.new > 0:
                summary_parts.append(f"[green]✓ {stats.new} new[/]")
            if stats.skipped > 0:
                summary_parts.append(f"[dim]⊖ {stats.skipped} skipped[/]")
            if stats.failed > 0:
                summary_parts.append(f"[red]✗ {stats.failed} failed[/]")

            if summary_parts:
                self.console.print(f"│  {' · '.join(summary_parts)}")

            if message:
                self.console.print(f"│  [green]{message}[/]")

        self._current_phase = None
        return stats

    def set_indexed_count(self, count: int, chunks: int = 0) -> None:
        """Set the final indexed count for current data type.

        Args:
            count: Number of documents indexed
            chunks: Number of chunks created
        """
        if self._current_data_type:
            self._current_data_type.total_indexed = count
            self._current_data_type.total_chunks = chunks

    def set_skipped_count(self, count: int) -> None:
        """Set the total skipped count for current data type.

        Args:
            count: Number of items skipped
        """
        if self._current_data_type:
            self._current_data_type.total_skipped = count

    def _finish_current_data_type(self) -> None:
        """Finish processing current data type and store stats."""
        if self._current_data_type:
            # Show completion message
            dt = self._current_data_type
            if dt.total_indexed > 0:
                chunks_msg = f" ({dt.total_chunks} chunks)" if dt.total_chunks else ""
                self.console.print(f"└─ [green]Done! +{dt.total_indexed} documents{chunks_msg}[/]")
            elif dt.total_skipped > 0:
                self.console.print(f"└─ [dim]All {dt.total_skipped} items already indexed[/]")
            else:
                self.console.print("└─ [dim]No items to process[/]")

            self._all_stats.append(self._current_data_type)
            self._current_data_type = None

    def finish(self) -> dict[str, int]:
        """Finish all progress tracking and show final summary.

        Returns:
            Dictionary with total counts by data type
        """
        # Finish current data type if any
        self._finish_current_data_type()

        # Stop any running progress
        if self._live:
            self._live.stop()

        # Calculate totals
        totals = {
            "total_indexed": 0,
            "total_skipped": 0,
            "total_chunks": 0,
        }

        for dt in self._all_stats:
            totals["total_indexed"] += dt.total_indexed
            totals["total_skipped"] += dt.total_skipped
            totals["total_chunks"] += dt.total_chunks
            totals[dt.name.lower().replace(" ", "_")] = dt.total_indexed

        # Show final summary
        self.console.print("\n" + "━" * 50)
        self.console.print("[bold green]✅ Setup Complete![/]")

        for dt in self._all_stats:
            if dt.total_indexed > 0:
                self.console.print(f"   {dt.icon} {dt.total_indexed:,} {dt.name.lower()}")

        if totals["total_skipped"] > 0:
            self.console.print(
                f"   [dim]⊖ {totals['total_skipped']:,} items skipped (unchanged)[/]"
            )

        self.console.print("━" * 50)

        return totals


class SimpleProgress:
    """Simplified progress for embedding operations.

    Shows a spinner with current position during batch embedding.
    """

    def __init__(self, console: Console, description: str, total: int):
        self.console = console
        self.total = total
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=20),
            MofNCompleteColumn(),
            console=console,
            transient=True,
        )
        self._task_id = self._progress.add_task(description=description, total=total)
        self._live = Live(self._progress, console=console, refresh_per_second=4)

    def __enter__(self):
        self._live.start()
        return self

    def __exit__(self, *args):
        self._live.stop()

    def update(self, advance: int = 1, description: str = "") -> None:
        """Update progress."""
        if description:
            self._progress.update(self._task_id, advance=advance, description=description)
        else:
            self._progress.update(self._task_id, advance=advance)
