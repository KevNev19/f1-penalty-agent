# PitWallAI - Live Data & Data Freshness Implementation Plan

## Overview

This document outlines the implementation plan for two critical features:

1. **Live Data Integration** - Real-time race control messages during live sessions
2. **Seasonal Data Freshness** - Keeping the knowledge base current throughout the F1 season

Both features ensure fans always get accurate, up-to-date information whether asking about an incident happening *right now* or a penalty from last weekend's race.

---

## Current Architecture (Post-Refactor)

Your codebase follows a **Hexagonal Architecture** (Ports & Adapters):

```
src/
├── core/                          # Domain logic (no external dependencies)
│   ├── domain/                    # Entities, value objects, exceptions
│   │   ├── agent.py               # QueryType, RetrievalContext, AgentResponse
│   │   ├── document.py            # Document, SearchResult
│   │   ├── race_data.py           # PenaltyEvent, RaceResult
│   │   └── exceptions/            # Custom exception hierarchy
│   ├── ports/                     # Interfaces (abstract contracts)
│   │   ├── data_source_port.py    # RaceDataSourcePort, RegulationsSourcePort
│   │   ├── vector_store_port.py   # VectorStorePort
│   │   ├── llm_port.py            # LLMPort
│   │   └── analytics_port.py      # AnalyticsPort
│   └── services/                  # Use cases / business logic
│       ├── agent_service.py       # AgentService (main orchestrator)
│       ├── retrieval_service.py   # RetrievalService
│       └── prompts.py             # System prompts
│
├── adapters/                      # Implementations of ports
│   ├── inbound/                   # Entry points (API, CLI)
│   │   ├── api/                   # FastAPI routes
│   │   │   ├── main.py
│   │   │   ├── deps.py            # Dependency injection
│   │   │   └── routers/
│   │   └── cli/                   # Typer CLI
│   └── outbound/                  # External services
│       ├── data_sources/
│       │   ├── fastf1_adapter.py  # FastF1Adapter (RaceDataSourcePort)
│       │   ├── fia_adapter.py     # FIAAdapter (RegulationsSourcePort)
│       │   └── jolpica_adapter.py # JolpicaAdapter (driver/race metadata)
│       ├── vector_store/
│       │   └── qdrant_adapter.py  # QdrantAdapter (VectorStorePort)
│       ├── llm/
│       │   └── gemini_adapter.py  # GeminiAdapter (LLMPort)
│       └── sqlite_adapter.py      # SQLiteAdapter (AnalyticsPort)
│
├── config/
│   └── settings.py                # Pydantic settings
│
└── infra/terraform/               # GCP + Qdrant Cloud infrastructure
```

### Key Observations

1. **Clean separation** - Core has no knowledge of adapters
2. **Port-based contracts** - `RaceDataSourcePort`, `VectorStorePort` define interfaces
3. **Dependency injection** - `deps.py` wires everything together
4. **Dual storage** - Qdrant (vectors) + SQLite (structured stats)
5. **Data ingestion** - `setup.py` router and `commands.py` CLI handle indexing

---

## Part 1: Live Data Integration

### Goal

During a live F1 session, fans can ask about **current incidents** and get contextual explanations combining:
- Live race control messages (what's happening NOW)
- FIA regulations (why it's a violation)  
- Historical precedent (typical penalty outcomes)

### Architecture Addition

```
                                    ┌─────────────────────────┐
                                    │     RetrievalService    │
                                    └───────────┬─────────────┘
                                                │
               ┌────────────────────────────────┼────────────────────────────────┐
               │                                │                                │
               ▼                                ▼                                ▼
    ┌──────────────────┐            ┌──────────────────┐            ┌──────────────────┐
    │   VectorStorePort│            │   VectorStorePort│            │LiveDataSourcePort│ ◄── NEW
    │   (Qdrant regs)  │            │   (Qdrant race)  │            │  (OpenF1 API)    │
    └──────────────────┘            └──────────────────┘            └──────────────────┘
```

### Phase 1: OpenF1 Adapter (~2-3 hours)

#### 1.1 Create the Port Interface

**File:** `src/core/ports/live_data_port.py`

```python
"""Port definition for live F1 timing data."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LiveSession:
    """A live F1 session."""
    
    session_key: int
    session_name: str  # "Race", "Qualifying", "Sprint"
    location: str      # "Monaco", "Silverstone"
    country: str
    circuit: str
    date_start: datetime | None
    year: int
    
    @property
    def display_name(self) -> str:
        """Human-readable session name."""
        return f"{self.session_name} at {self.location}"


@dataclass  
class LiveRaceControlMessage:
    """A race control message from live timing."""
    
    date: datetime
    message: str
    category: str  # "Flag", "SafetyCar", "Other"
    driver_number: int | None = None
    lap_number: int | None = None
    
    @property
    def is_investigation(self) -> bool:
        """Check if this message indicates an investigation."""
        keywords = ["NOTED", "UNDER INVESTIGATION", "INVESTIGATED", "SUMMON"]
        return any(kw in self.message.upper() for kw in keywords)
    
    @property
    def is_penalty(self) -> bool:
        """Check if this message announces a penalty."""
        keywords = [
            "PENALTY", "TIME PENALTY", "GRID PENALTY", "DRIVE THROUGH",
            "STOP AND GO", "WARNING", "REPRIMAND", "BLACK AND WHITE",
            "DISQUALIFIED",
        ]
        return any(kw in self.message.upper() for kw in keywords)
    
    @property
    def is_track_limits(self) -> bool:
        """Check if this is a track limits message."""
        return "TRACK LIMITS" in self.message.upper() or "LAP TIME DELETED" in self.message.upper()
    
    @property
    def is_penalty_relevant(self) -> bool:
        """Check if relevant for penalty explanation."""
        return self.is_investigation or self.is_penalty or self.is_track_limits


@dataclass
class LiveDriver:
    """Driver info from live session."""
    
    driver_number: int
    full_name: str
    name_acronym: str  # "VER", "HAM"
    team_name: str


class LiveDataSourcePort(ABC):
    """Abstract interface for live F1 timing data."""
    
    @abstractmethod
    def get_current_session(self) -> LiveSession | None:
        """Get the current or most recent session."""
        ...
    
    @abstractmethod
    def get_race_control_messages(
        self,
        session_key: int | str = "latest",
        driver_number: int | None = None,
    ) -> list[LiveRaceControlMessage]:
        """Get race control messages for a session."""
        ...
    
    @abstractmethod
    def get_penalty_messages(
        self,
        session_key: int | str = "latest",
    ) -> list[LiveRaceControlMessage]:
        """Get only penalty-relevant messages."""
        ...
    
    @abstractmethod
    def get_drivers(
        self,
        session_key: int | str = "latest",
    ) -> list[LiveDriver]:
        """Get drivers for a session."""
        ...
    
    @abstractmethod
    def get_driver_name(
        self,
        driver_number: int,
        session_key: int,
    ) -> str | None:
        """Resolve driver number to name."""
        ...
```

#### 1.2 Implement the OpenF1 Adapter

**File:** `src/adapters/outbound/data_sources/openf1_adapter.py`

```python
"""OpenF1 API adapter for live F1 timing data.

OpenF1 (https://openf1.org) provides a free REST API that wraps the official
F1 live timing SignalR stream with ~3 second delay. No authentication required.
"""

import logging
from datetime import datetime

import requests

from ....core.ports.live_data_port import (
    LiveDataSourcePort,
    LiveDriver,
    LiveRaceControlMessage,
    LiveSession,
)

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


class OpenF1Adapter(LiveDataSourcePort):
    """Adapter for OpenF1 real-time F1 data API.
    
    API Documentation: https://openf1.org
    
    Usage:
        adapter = OpenF1Adapter()
        session = adapter.get_current_session()
        messages = adapter.get_penalty_messages(session.session_key)
    """
    
    BASE_URL = "https://api.openf1.org/v1"
    
    def __init__(self) -> None:
        """Initialize the adapter."""
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "PitWallAI/1.0"})
        self._driver_cache: dict[tuple[int, int], LiveDriver] = {}
    
    def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            self._session.close()
    
    def __enter__(self) -> "OpenF1Adapter":
        return self
    
    def __exit__(self, *args) -> None:
        self.close()
    
    def _get(self, endpoint: str, params: dict | None = None) -> list[dict] | None:
        """Make a GET request to the API."""
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.warning(f"OpenF1 API error: {e}")
            return None
    
    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """Parse ISO datetime string from API."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    
    # =========================================================================
    # LiveDataSourcePort Implementation
    # =========================================================================
    
    def get_current_session(self) -> LiveSession | None:
        """Get the current or most recent F1 session."""
        data = self._get("/sessions", params={"session_key": "latest"})
        if not data or len(data) == 0:
            return None
        
        s = data[0]
        return LiveSession(
            session_key=s.get("session_key"),
            session_name=s.get("session_name", ""),
            location=s.get("location", ""),
            country=s.get("country_name", ""),
            circuit=s.get("circuit_short_name", ""),
            date_start=self._parse_datetime(s.get("date_start")),
            year=s.get("year", 2025),
        )
    
    def get_race_control_messages(
        self,
        session_key: int | str = "latest",
        driver_number: int | None = None,
    ) -> list[LiveRaceControlMessage]:
        """Get race control messages for a session."""
        params: dict = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        
        data = self._get("/race_control", params=params)
        if not data:
            return []
        
        messages = []
        for msg in data:
            messages.append(
                LiveRaceControlMessage(
                    date=self._parse_datetime(msg.get("date")) or datetime.now(),
                    message=msg.get("message", ""),
                    category=msg.get("category", "Other"),
                    driver_number=msg.get("driver_number"),
                    lap_number=msg.get("lap_number"),
                )
            )
        
        # Sort by date, newest first
        messages.sort(key=lambda m: m.date, reverse=True)
        return messages
    
    def get_penalty_messages(
        self,
        session_key: int | str = "latest",
    ) -> list[LiveRaceControlMessage]:
        """Get only penalty-relevant messages."""
        all_messages = self.get_race_control_messages(session_key)
        return [m for m in all_messages if m.is_penalty_relevant]
    
    def get_drivers(
        self,
        session_key: int | str = "latest",
    ) -> list[LiveDriver]:
        """Get all drivers for a session."""
        data = self._get("/drivers", params={"session_key": session_key})
        if not data:
            return []
        
        drivers = []
        seen_numbers = set()  # API sometimes returns duplicates
        
        for d in data:
            num = d.get("driver_number")
            if num in seen_numbers:
                continue
            seen_numbers.add(num)
            
            driver = LiveDriver(
                driver_number=num,
                full_name=d.get("full_name", ""),
                name_acronym=d.get("name_acronym", ""),
                team_name=d.get("team_name", ""),
            )
            drivers.append(driver)
            
            # Cache for lookups
            if isinstance(session_key, int):
                self._driver_cache[(session_key, num)] = driver
        
        return drivers
    
    def get_driver_name(
        self,
        driver_number: int,
        session_key: int,
    ) -> str | None:
        """Get driver name from number, using cache."""
        cache_key = (session_key, driver_number)
        if cache_key in self._driver_cache:
            return self._driver_cache[cache_key].full_name
        
        # Fetch and cache all drivers
        self.get_drivers(session_key)
        
        if cache_key in self._driver_cache:
            return self._driver_cache[cache_key].full_name
        
        return None
```

#### 1.3 Update Exports

**File:** `src/core/ports/__init__.py`

```python
"""Core ports (interfaces) for the F1 Penalty Agent."""

from .analytics_port import AnalyticsPort
from .data_source_port import RaceDataSourcePort, RegulationsSourcePort
from .embedding_port import EmbeddingPort
from .live_data_port import (
    LiveDataSourcePort,
    LiveDriver,
    LiveRaceControlMessage,
    LiveSession,
)
from .llm_port import LLMPort
from .vector_store_port import VectorStorePort

__all__ = [
    "AnalyticsPort",
    "RaceDataSourcePort",
    "RegulationsSourcePort",
    "EmbeddingPort",
    "LiveDataSourcePort",
    "LiveDriver",
    "LiveRaceControlMessage",
    "LiveSession",
    "LLMPort",
    "VectorStorePort",
]
```

#### 1.4 Add Tests

**File:** `tests/unit/test_openf1_adapter.py`

```python
"""Unit tests for OpenF1 adapter."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.core.ports.live_data_port import LiveRaceControlMessage


class TestLiveRaceControlMessage:
    """Tests for message classification properties."""
    
    @pytest.mark.unit
    def test_is_investigation(self):
        msg = LiveRaceControlMessage(
            date=datetime.now(),
            message="CAR 1 (VER) UNDER INVESTIGATION - CAUSING A COLLISION",
            category="Other",
        )
        assert msg.is_investigation is True
        assert msg.is_penalty is False
    
    @pytest.mark.unit
    def test_is_penalty(self):
        msg = LiveRaceControlMessage(
            date=datetime.now(),
            message="CAR 1 (VER) - 5 SECOND TIME PENALTY",
            category="Other",
        )
        assert msg.is_penalty is True
    
    @pytest.mark.unit
    def test_is_track_limits(self):
        msg = LiveRaceControlMessage(
            date=datetime.now(),
            message="TRACK LIMITS - LAP TIME DELETED FOR CAR 44",
            category="Other",
        )
        assert msg.is_track_limits is True
    
    @pytest.mark.unit
    def test_is_penalty_relevant(self):
        relevant = LiveRaceControlMessage(
            date=datetime.now(),
            message="CAR 1 NOTED - FORCING ANOTHER DRIVER OFF TRACK",
            category="Other",
        )
        assert relevant.is_penalty_relevant is True
        
        not_relevant = LiveRaceControlMessage(
            date=datetime.now(),
            message="DRS ENABLED",
            category="Drs",
        )
        assert not_relevant.is_penalty_relevant is False


class TestOpenF1Adapter:
    """Tests for OpenF1Adapter with mocked HTTP."""
    
    @pytest.fixture
    def mock_session(self):
        with patch("requests.Session") as mock:
            yield mock.return_value
    
    @pytest.mark.unit
    def test_get_current_session(self, mock_session):
        from src.adapters.outbound.data_sources.openf1_adapter import OpenF1Adapter
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            "session_key": 9999,
            "session_name": "Race",
            "location": "Monaco",
            "country_name": "Monaco",
            "circuit_short_name": "monaco",
            "year": 2025,
        }]
        mock_session.get.return_value = mock_response
        
        adapter = OpenF1Adapter()
        adapter._session = mock_session
        
        session = adapter.get_current_session()
        
        assert session is not None
        assert session.session_name == "Race"
        assert session.location == "Monaco"
    
    @pytest.mark.unit
    def test_get_penalty_messages_filters_correctly(self, mock_session):
        from src.adapters.outbound.data_sources.openf1_adapter import OpenF1Adapter
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"date": "2025-05-25T14:30:00Z", "message": "DRS ENABLED", "category": "Drs"},
            {"date": "2025-05-25T14:31:00Z", "message": "CAR 1 UNDER INVESTIGATION", "category": "Other"},
            {"date": "2025-05-25T14:32:00Z", "message": "GREEN FLAG", "category": "Flag"},
        ]
        mock_session.get.return_value = mock_response
        
        adapter = OpenF1Adapter()
        adapter._session = mock_session
        
        messages = adapter.get_penalty_messages("latest")
        
        assert len(messages) == 1
        assert "INVESTIGATION" in messages[0].message
```

### Phase 2: Integrate Live Data into Retrieval (~2-3 hours)

#### 2.1 Extend RetrievalContext

**File:** `src/core/domain/agent.py` - Update dataclass

```python
"""Agent-related models for query classification and responses."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .document import SearchResult
    from ..ports.live_data_port import LiveRaceControlMessage, LiveSession


class QueryType(Enum):
    """Type of user query for the F1 agent."""
    
    PENALTY_EXPLANATION = "penalty_explanation"
    RULE_LOOKUP = "rule_lookup"
    ANALYTICS = "analytics"
    GENERAL = "general"


@dataclass
class ChatMessage:
    """A single message in the chat history."""
    
    role: str
    content: str


@dataclass
class RetrievalContext:
    """Context retrieved for answering a question.
    
    Holds search results from different collections plus live data
    that will be used to build the LLM prompt context.
    """
    
    regulations: list["SearchResult"]
    stewards_decisions: list["SearchResult"]
    race_data: list["SearchResult"]
    query: str
    
    # Live data from OpenF1 (empty if no active session)
    live_messages: list["LiveRaceControlMessage"] = field(default_factory=list)
    live_session: "LiveSession | None" = None
    
    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Normalize text for safe use in prompts."""
        from .utils import normalize_text
        return normalize_text(text)
    
    @property
    def has_live_data(self) -> bool:
        """Check if live data is present."""
        return len(self.live_messages) > 0
    
    def get_combined_context(self, max_chars: int = 8000) -> str:
        """Get combined context string for the LLM.
        
        Priority order:
        1. Live race control (what's happening NOW)
        2. FIA regulations (the rules)
        3. Stewards decisions (precedent)
        4. Historical race data
        """
        from .utils import normalize_text
        
        parts = []
        char_count = 0
        
        # =====================================================================
        # LIVE CONTEXT FIRST (most immediately relevant)
        # =====================================================================
        if self.live_messages:
            session_info = ""
            if self.live_session:
                session_info = f" - {self.live_session.display_name}"
            
            parts.append(f"=== LIVE RACE CONTROL{session_info} ===")
            parts.append("(Real-time messages from the current session)\n")
            
            # Reserve ~25% of budget for live data
            live_budget = int(max_chars * 0.25)
            
            for msg in self.live_messages[:10]:
                if char_count > live_budget:
                    break
                
                timestamp = msg.date.strftime("%H:%M:%S") if msg.date else ""
                lap_info = f"[Lap {msg.lap_number}] " if msg.lap_number else ""
                driver_info = f"(Car {msg.driver_number}) " if msg.driver_number else ""
                
                line = f"[{timestamp}] {lap_info}{driver_info}{msg.message}"
                parts.append(line)
                char_count += len(line)
            
            parts.append("")  # Blank separator
        
        # =====================================================================
        # REGULATIONS (authoritative rules)
        # =====================================================================
        if self.regulations:
            parts.append("=== FIA REGULATIONS ===")
            for result in self.regulations:
                if char_count > max_chars:
                    break
                content = normalize_text(result.document.content or "")
                source = normalize_text(result.document.metadata.get("source", "Unknown") or "")
                parts.append(f"\n[Source: {source}]\n{content}")
                char_count += len(content)
        
        # =====================================================================
        # STEWARDS DECISIONS (precedent)
        # =====================================================================
        if self.stewards_decisions:
            parts.append("\n\n=== STEWARDS DECISIONS ===")
            for result in self.stewards_decisions:
                if char_count > max_chars:
                    break
                content = normalize_text(result.document.content or "")
                event = normalize_text(result.document.metadata.get("event", "Unknown") or "")
                parts.append(f"\n[Event: {event}]\n{content}")
                char_count += len(content)
        
        # =====================================================================
        # HISTORICAL RACE DATA
        # =====================================================================
        if self.race_data:
            parts.append("\n\n=== RACE CONTROL MESSAGES ===")
            for result in self.race_data:
                if char_count > max_chars:
                    break
                content = normalize_text(result.document.content or "")
                parts.append(f"\n{content}")
                char_count += len(content)
        
        if not parts:
            return "No specific context found. Provide a general response based on F1 knowledge."
        
        return "\n".join(parts)


@dataclass
class AgentResponse:
    """Response from the F1 agent."""
    
    answer: str
    query_type: QueryType
    sources_used: list[str]
    context: "RetrievalContext | None" = None
```

#### 2.2 Update RetrievalService

**File:** `src/core/services/retrieval_service.py` - Add live data fetching

Add to imports:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ports.live_data_port import LiveDataSourcePort, LiveRaceControlMessage, LiveSession
```

Update `__init__`:
```python
def __init__(
    self,
    vector_store: VectorStorePort,
    use_reranker: bool = True,
    live_data_source: "LiveDataSourcePort | None" = None,  # NEW
) -> None:
    """Initialize the retriever.
    
    Args:
        vector_store: QdrantVectorStore instance for document retrieval.
        use_reranker: Whether to use cross-encoder re-ranking.
        live_data_source: Optional live data source for real-time context.
    """
    self.vector_store = vector_store
    self.reranker = CrossEncoderReranker() if use_reranker else None
    self._live_source = live_data_source
    
    if self.reranker:
        logger.info("Cross-encoder re-ranking enabled")
```

Add lazy loading property:
```python
@property
def live_source(self) -> "LiveDataSourcePort":
    """Lazy-load live data source on first access."""
    if self._live_source is None:
        from ...adapters.outbound.data_sources.openf1_adapter import OpenF1Adapter
        self._live_source = OpenF1Adapter()
        logger.debug("OpenF1 adapter initialized")
    return self._live_source
```

Add live data fetching methods:
```python
def _fetch_live_context(
    self,
    query: str,
    query_context: dict | None,
) -> tuple[list["LiveRaceControlMessage"], "LiveSession | None"]:
    """Fetch relevant live race control messages.
    
    Args:
        query: User's question
        query_context: Detected driver/race context
        
    Returns:
        Tuple of (messages, session)
    """
    try:
        session = self.live_source.get_current_session()
        if not session:
            logger.debug("No active session for live data")
            return [], None
        
        logger.debug(f"Fetching live data from: {session.display_name}")
        
        messages = self.live_source.get_penalty_messages(session.session_key)
        
        if not messages:
            logger.debug("No penalty-relevant messages in current session")
            return [], session
        
        # Prioritize messages for queried driver if specified
        if query_context and query_context.get("driver"):
            messages = self._prioritize_driver_messages(
                messages,
                query_context["driver"],
                session.session_key,
            )
        
        logger.info(f"Found {len(messages)} live penalty messages")
        return messages[:15], session
        
    except Exception as e:
        logger.warning(f"Failed to fetch live context: {e}")
        return [], None

def _prioritize_driver_messages(
    self,
    messages: list["LiveRaceControlMessage"],
    driver_query: str,
    session_key: int,
) -> list["LiveRaceControlMessage"]:
    """Reorder messages to prioritize those for the queried driver."""
    driver_query_lower = driver_query.lower()
    
    def matches_driver(msg: "LiveRaceControlMessage") -> bool:
        if not msg.driver_number:
            return False
        
        if driver_query_lower in msg.message.lower():
            return True
        
        driver_name = self.live_source.get_driver_name(msg.driver_number, session_key)
        if driver_name and driver_query_lower in driver_name.lower():
            return True
        
        return False
    
    driver_msgs = [m for m in messages if matches_driver(m)]
    other_msgs = [m for m in messages if not matches_driver(m)]
    
    return driver_msgs + other_msgs
```

Update `retrieve` method signature:
```python
def retrieve(
    self,
    query: str,
    top_k: int = 5,
    include_regulations: bool = True,
    include_stewards: bool = True,
    include_race_data: bool = True,
    include_live: bool = True,  # NEW
    query_context: dict | None = None,
) -> RetrievalContext:
    """Retrieve relevant context for a query.
    
    Args:
        query: User's question.
        top_k: Number of results per category.
        include_regulations: Whether to search regulations.
        include_stewards: Whether to search stewards decisions.
        include_race_data: Whether to search race control data.
        include_live: Whether to fetch live OpenF1 data.
        query_context: Optional dict with detected driver/race/season.
        
    Returns:
        RetrievalContext with documents and live data.
    """
    regulations = []
    stewards = []
    race_data = []
    live_messages = []
    live_session = None
    
    expanded_query = self.expand_query(query)
    
    # === FETCH LIVE DATA FIRST (fast API call) ===
    if include_live:
        live_messages, live_session = self._fetch_live_context(query, query_context)
    
    # ... existing vector search code ...
    
    return RetrievalContext(
        regulations=regulations,
        stewards_decisions=stewards,
        race_data=race_data,
        query=query,
        live_messages=live_messages,  # NEW
        live_session=live_session,    # NEW
    )
```

#### 2.3 Update AgentService

**File:** `src/core/services/agent_service.py` - Add `include_live` parameter

```python
def ask(
    self,
    query: str,
    messages: list[object] | None = None,
    stream: bool = False,
    include_live: bool = True,  # NEW
) -> AgentResponse:
    """Ask a question and get a response.
    
    Args:
        query: User's question about F1 penalties/rules.
        messages: Optional chat history for context.
        stream: Whether to stream the response.
        include_live: Whether to include live session data.
        
    Returns:
        AgentResponse with the answer and metadata.
    """
    # ... existing code ...
    
    # Retrieve documents + live data
    logger.debug("Searching knowledge base...")
    context = self.retriever.retrieve(
        search_query,
        top_k=5,
        query_context=query_context,
        include_live=include_live,  # Pass through
    )
    
    if context.has_live_data:
        logger.info(f"Live data included from: {context.live_session.display_name}")
    
    # ... rest of existing code ...
    
    sources = self.get_sources(context)
    
    # Add live session as first source if present
    if context.live_session:
        sources.insert(0, {
            "source": f"[LIVE] {context.live_session.display_name}",
            "doc_type": "live",
            "score": 1.0,
        })
    
    return AgentResponse(
        answer=answer,
        query_type=query_type,
        sources_used=sources,
        context=context,
    )
```

#### 2.4 Update Dependency Injection

**File:** `src/adapters/inbound/api/deps.py`

```python
from functools import lru_cache

from ....adapters.outbound.data_sources.openf1_adapter import OpenF1Adapter
# ... existing imports ...


@lru_cache
def get_live_data_source() -> OpenF1Adapter:
    """Get or create the OpenF1Adapter singleton."""
    logger.info("Initializing OpenF1Adapter...")
    return OpenF1Adapter()


@lru_cache
def get_retriever() -> F1Retriever:
    """Get or create the F1Retriever singleton."""
    logger.info("Initializing F1Retriever...")
    vector_store = get_vector_store()
    live_source = get_live_data_source()  # NEW
    return F1Retriever(
        vector_store,
        use_reranker=False,
        live_data_source=live_source,  # Inject
    )
```

#### 2.5 Update API Models

**File:** `src/adapters/inbound/api/models.py`

```python
class QuestionRequest(BaseModel):
    """Request model for asking a question."""
    
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The F1 penalty or regulation question to ask",
    )
    messages: list[ChatMessage] = Field(
        default_factory=list,
        description="Chat history for context",
    )
    include_live: bool = Field(
        default=True,
        description="Include live race control data if a session is active",
    )


class AnswerResponse(BaseModel):
    """Response model for an answered question."""
    
    answer: str = Field(..., description="The AI-generated answer")
    sources: list[SourceInfo] = Field(default_factory=list)
    question: str = Field(..., description="The original question asked")
    model_used: str = Field(default="gemini-2.0-flash")
    live_session: str | None = Field(
        default=None,
        description="Active session name if live data was included",
    )
```

#### 2.6 Update Chat Router

**File:** `src/adapters/inbound/api/routers/chat.py`

```python
@router.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest) -> AnswerResponse:
    """Ask a question about F1 penalties or regulations."""
    try:
        agent = get_agent()
        normalized_question = normalize_text(request.question)
        
        # ... existing validation ...
        
        history = [DomainChatMessage(role=m.role, content=m.content) for m in request.messages]
        
        response = agent.ask(
            normalized_question,
            messages=history,
            include_live=request.include_live,  # Pass through
        )
        
        # ... build sources ...
        
        # Get live session name if present
        live_session_name = None
        if response.context and response.context.live_session:
            live_session_name = response.context.live_session.display_name
        
        return AnswerResponse(
            answer=response.answer,
            sources=sources,
            question=normalized_question,
            model_used="gemini-2.0-flash",
            live_session=live_session_name,  # NEW
        )
    
    except Exception as e:
        # ... error handling ...
```

#### 2.7 Update Prompts for Live Awareness

**File:** `src/core/services/prompts.py` - Update system prompt

Add to `F1_SYSTEM_PROMPT`:

```python
F1_SYSTEM_PROMPT = """You are PitWallAI, an expert Formula 1 race engineer...

## Context Priority

You receive context in this priority order:

1. **LIVE RACE CONTROL** (if present): Real-time messages from the current session
   - This is what's happening RIGHT NOW
   - Use this for questions about ongoing incidents
   - Be clear when referencing live/current situations vs historical

2. **FIA Regulations**: The official rules
   - Use to explain WHY something is a violation
   - Always cite specific articles when available

3. **Stewards Decisions**: Historical precedent
   - Use to show how similar incidents were handled
   - Helps predict likely outcomes

4. **Historical Race Control**: Past incidents from this season

## Response Style

For questions about CURRENT incidents (when LIVE RACE CONTROL present):
1. Acknowledge what's happening NOW (cite the live message)
2. Explain which rule likely applies
3. Describe typical outcomes based on precedent
4. Note if investigation is ongoing (outcome not yet known)

For questions about PAST incidents:
1. Describe what happened
2. State the penalty given
3. Explain which rule was broken
4. Provide stewards' reasoning

...
"""
```

---

## Part 2: Seasonal Data Freshness

### Goal

Keep the knowledge base current throughout the F1 season:
- New stewards decisions indexed within hours of publication
- Race control messages from latest races available
- Outdated/superseded documents cleaned up

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Data Freshness System                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────────┐
        ▼                            ▼                                ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────────────┐
│  Scheduled Sync   │    │   On-Demand Sync  │    │   Incremental Updates     │
│  (Cloud Scheduler)│    │   (Manual/CI)     │    │   (Post-Race Trigger)     │
└─────────┬─────────┘    └─────────┬─────────┘    └─────────────┬─────────────┘
          │                        │                            │
          └────────────────────────┼────────────────────────────┘
                                   ▼
                    ┌──────────────────────────────┐
                    │      DataSyncService         │
                    │  (Orchestrates all updates)  │
                    └──────────────┬───────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
┌───────────────┐        ┌───────────────┐        ┌───────────────────┐
│  FIA Scraper  │        │ FastF1 Loader │        │ Cleanup Service   │
│ (New Docs)    │        │ (Race Data)   │        │ (Orphan Removal)  │
└───────────────┘        └───────────────┘        └───────────────────┘
        │                        │                          │
        └────────────────────────┼──────────────────────────┘
                                 ▼
                    ┌──────────────────────────────┐
                    │  Qdrant + SQLite (Upsert)    │
                    └──────────────────────────────┘
```

### Phase 3: Data Sync Service (~3-4 hours)

#### 3.1 Create the Sync Service

**File:** `src/core/services/data_sync_service.py`

```python
"""Data synchronization service for keeping knowledge base fresh.

This service orchestrates incremental updates to the knowledge base:
- Scrapes new FIA documents (regulations, stewards decisions)
- Loads race control messages from completed races
- Cleans up orphaned/outdated documents
- Supports both full sync and incremental updates
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from ..domain import Document
from ..domain.utils import chunk_text, normalize_text
from ..ports.data_source_port import RaceDataSourcePort, RegulationsSourcePort
from ..ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a sync operation."""
    
    regulations_added: int = 0
    regulations_updated: int = 0
    stewards_added: int = 0
    stewards_updated: int = 0
    race_data_added: int = 0
    orphans_removed: int = 0
    errors: list[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def total_changes(self) -> int:
        return (
            self.regulations_added + self.regulations_updated +
            self.stewards_added + self.stewards_updated +
            self.race_data_added + self.orphans_removed
        )
    
    def to_dict(self) -> dict:
        return {
            "regulations": {"added": self.regulations_added, "updated": self.regulations_updated},
            "stewards_decisions": {"added": self.stewards_added, "updated": self.stewards_updated},
            "race_data": {"added": self.race_data_added},
            "orphans_removed": self.orphans_removed,
            "total_changes": self.total_changes,
            "errors": self.errors,
        }


@dataclass
class SyncOptions:
    """Options for sync operation."""
    
    season: int = 2025
    include_regulations: bool = True
    include_stewards: bool = True
    include_race_data: bool = True
    cleanup_orphans: bool = True
    force_full_sync: bool = False
    # For incremental: only sync docs newer than this
    since_date: datetime | None = None
    # Limit races to sync (0 = all completed races)
    race_limit: int = 0


class DataSyncService:
    """Orchestrates data synchronization for the knowledge base.
    
    Usage:
        sync_service = DataSyncService(
            vector_store=qdrant,
            fia_scraper=fia_adapter,
            race_loader=fastf1_adapter,
            data_dir=Path("./data"),
        )
        
        # Full sync
        result = sync_service.sync(SyncOptions(season=2025, force_full_sync=True))
        
        # Incremental sync (new docs only)
        result = sync_service.sync(SyncOptions(
            season=2025,
            since_date=datetime.now() - timedelta(days=7),
        ))
    """
    
    def __init__(
        self,
        vector_store: VectorStorePort,
        fia_scraper: RegulationsSourcePort,
        race_loader: RaceDataSourcePort,
        sql_adapter=None,  # Optional for structured stats
        data_dir: Path = Path("./data"),
    ) -> None:
        self.vector_store = vector_store
        self.fia_scraper = fia_scraper
        self.race_loader = race_loader
        self.sql_adapter = sql_adapter
        self.data_dir = data_dir
        
        # Track what's been indexed (for incremental)
        self._indexed_doc_hashes: set[str] = set()
    
    def sync(self, options: SyncOptions) -> SyncResult:
        """Run a sync operation with the given options.
        
        Args:
            options: Configuration for the sync.
            
        Returns:
            SyncResult with counts of changes made.
        """
        result = SyncResult()
        logger.info(f"Starting sync for season {options.season}")
        
        if options.include_regulations:
            try:
                reg_result = self._sync_regulations(options)
                result.regulations_added = reg_result["added"]
                result.regulations_updated = reg_result["updated"]
            except Exception as e:
                logger.error(f"Regulations sync failed: {e}")
                result.errors.append(f"Regulations: {e}")
        
        if options.include_stewards:
            try:
                stewards_result = self._sync_stewards(options)
                result.stewards_added = stewards_result["added"]
                result.stewards_updated = stewards_result["updated"]
            except Exception as e:
                logger.error(f"Stewards sync failed: {e}")
                result.errors.append(f"Stewards: {e}")
        
        if options.include_race_data:
            try:
                race_result = self._sync_race_data(options)
                result.race_data_added = race_result["added"]
            except Exception as e:
                logger.error(f"Race data sync failed: {e}")
                result.errors.append(f"Race data: {e}")
        
        if options.cleanup_orphans:
            try:
                result.orphans_removed = self._cleanup_orphans(options)
            except Exception as e:
                logger.error(f"Cleanup failed: {e}")
                result.errors.append(f"Cleanup: {e}")
        
        logger.info(f"Sync complete: {result.total_changes} changes")
        return result
    
    def _sync_regulations(self, options: SyncOptions) -> dict:
        """Sync FIA regulations."""
        logger.info(f"Syncing regulations for {options.season}...")
        
        # Scrape available regulations
        regulations = self.fia_scraper.scrape_regulations(options.season)
        
        added = 0
        updated = 0
        
        for reg in regulations:
            # Download and extract
            self.fia_scraper.download_document(reg)
            self.fia_scraper.extract_text(reg)
            
            if not reg.text_content:
                continue
            
            # Check if already indexed (by URL hash)
            doc_hash = f"reg_{hash(reg.url) % 10000}"
            
            # For incremental, skip if already indexed and not forcing
            if not options.force_full_sync and doc_hash in self._indexed_doc_hashes:
                continue
            
            # Chunk and index
            clean_text = normalize_text(reg.text_content)
            chunks = chunk_text(clean_text, chunk_size=1500, chunk_overlap=200)
            
            docs = []
            for i, chunk in enumerate(chunks):
                docs.append(Document(
                    doc_id=f"{doc_hash}-{i}",
                    content=chunk,
                    metadata={
                        "source": normalize_text(reg.title),
                        "type": "regulation",
                        "url": reg.url,
                        "season": options.season,
                        "chunk_index": i,
                        "indexed_at": datetime.now().isoformat(),
                    },
                ))
            
            if docs:
                self.vector_store.add_documents(docs, "regulations")
                self._indexed_doc_hashes.add(doc_hash)
                
                if doc_hash in self._indexed_doc_hashes:
                    updated += 1
                else:
                    added += 1
        
        logger.info(f"Regulations: {added} added, {updated} updated")
        return {"added": added, "updated": updated}
    
    def _sync_stewards(self, options: SyncOptions) -> dict:
        """Sync stewards decisions."""
        logger.info(f"Syncing stewards decisions for {options.season}...")
        
        decisions = self.fia_scraper.scrape_stewards_decisions(options.season)
        
        added = 0
        updated = 0
        
        for dec in decisions:
            self.fia_scraper.download_document(dec)
            self.fia_scraper.extract_text(dec)
            
            if not dec.text_content:
                continue
            
            doc_hash = f"dec_{hash(dec.url) % 10000}"
            
            if not options.force_full_sync and doc_hash in self._indexed_doc_hashes:
                continue
            
            clean_text = normalize_text(dec.text_content)
            chunks = chunk_text(clean_text, chunk_size=1500, chunk_overlap=200)
            
            docs = []
            for i, chunk in enumerate(chunks):
                docs.append(Document(
                    doc_id=f"{doc_hash}-{i}",
                    content=chunk,
                    metadata={
                        "source": normalize_text(dec.title),
                        "type": "stewards_decision",
                        "event": normalize_text(dec.event_name or ""),
                        "url": dec.url,
                        "season": options.season,
                        "chunk_index": i,
                        "indexed_at": datetime.now().isoformat(),
                    },
                ))
            
            if docs:
                self.vector_store.add_documents(docs, "stewards_decisions")
                self._indexed_doc_hashes.add(doc_hash)
                added += 1
        
        logger.info(f"Stewards decisions: {added} added")
        return {"added": added, "updated": updated}
    
    def _sync_race_data(self, options: SyncOptions) -> dict:
        """Sync race control data from FastF1."""
        logger.info(f"Syncing race data for {options.season}...")
        
        events = self.race_loader.get_season_events(options.season)
        
        if options.race_limit > 0:
            events = events[:options.race_limit]
        
        added = 0
        
        for event in events:
            try:
                penalties = self.race_loader.get_race_control_messages(
                    options.season, event, "Race"
                )
                
                for penalty in penalties:
                    if penalty.category not in ["Penalty", "Investigation", "Track Limits"]:
                        continue
                    
                    doc_hash = f"race_{hash(f'{event}-{penalty.message}') % 10000}"
                    
                    if not options.force_full_sync and doc_hash in self._indexed_doc_hashes:
                        continue
                    
                    content = normalize_text(
                        f"Race: {penalty.race_name} ({penalty.session})\n"
                        f"Driver: {penalty.driver or 'Unknown'}\n"
                        f"Team: {penalty.team or 'Unknown'}\n"
                        f"Message: {penalty.message}\n"
                        f"Category: {penalty.category}"
                    )
                    
                    doc = Document(
                        doc_id=doc_hash,
                        content=content,
                        metadata={
                            "source": f"{penalty.race_name} {penalty.session}",
                            "type": "race_control",
                            "driver": normalize_text(penalty.driver or ""),
                            "team": normalize_text(penalty.team or ""),
                            "race": normalize_text(penalty.race_name),
                            "season": options.season,
                            "indexed_at": datetime.now().isoformat(),
                        },
                    )
                    
                    self.vector_store.add_documents([doc], "race_data")
                    self._indexed_doc_hashes.add(doc_hash)
                    added += 1
                    
                    # Also add to SQL if available
                    if self.sql_adapter:
                        self.sql_adapter.insert_penalty(
                            season=options.season,
                            race_name=penalty.race_name,
                            driver=penalty.driver or "Unknown",
                            category=penalty.category,
                            message=penalty.message,
                            session=penalty.session,
                            team=penalty.team or "Unknown",
                        )
                        
            except Exception as e:
                logger.warning(f"Failed to sync {event}: {e}")
                continue
        
        logger.info(f"Race data: {added} added")
        return {"added": added}
    
    def _cleanup_orphans(self, options: SyncOptions) -> int:
        """Remove orphaned documents that are no longer on FIA site."""
        logger.info("Cleaning up orphaned documents...")
        
        # Get current documents from FIA
        current_docs = self.fia_scraper.get_available_documents(options.season)
        
        # Use the scraper's cleanup method
        removed = self.fia_scraper.cleanup_orphaned_files(current_docs)
        
        # Note: Qdrant documents are upserted by ID, so orphan vectors
        # will naturally be replaced when new docs are indexed.
        # For true cleanup, we'd need to track IDs and delete explicitly.
        
        return removed
```

#### 3.2 Create Sync API Endpoint

**File:** `src/adapters/inbound/api/routers/sync.py`

```python
"""Data sync endpoints for keeping knowledge base fresh."""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from .....adapters.outbound.data_sources.fastf1_adapter import FastF1Adapter
from .....adapters.outbound.data_sources.fia_adapter import FIAAdapter
from .....adapters.outbound.sqlite_adapter import SQLiteAdapter
from .....config.settings import settings
from .....core.services.data_sync_service import DataSyncService, SyncOptions
from ..deps import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


class SyncRequest(BaseModel):
    """Request model for sync operation."""
    
    season: int = Field(default=2025, description="F1 season year")
    include_regulations: bool = Field(default=True)
    include_stewards: bool = Field(default=True)
    include_race_data: bool = Field(default=True)
    cleanup_orphans: bool = Field(default=True)
    force_full_sync: bool = Field(default=False, description="Re-index all documents")
    days_back: int | None = Field(
        default=7,
        description="Only sync documents from the last N days (None for all)",
    )


class SyncResponse(BaseModel):
    """Response model for sync operation."""
    
    status: str
    message: str
    result: dict | None = None


# Track ongoing sync to prevent concurrent runs
_sync_in_progress = False


def _run_sync_task(options: SyncOptions) -> dict:
    """Background task to run sync."""
    global _sync_in_progress
    
    try:
        _sync_in_progress = True
        
        vector_store = get_vector_store()
        data_dir = settings.data_dir
        
        fia_scraper = FIAAdapter(data_dir)
        race_loader = FastF1Adapter(data_dir / "fastf1_cache")
        sql_adapter = SQLiteAdapter()
        
        sync_service = DataSyncService(
            vector_store=vector_store,
            fia_scraper=fia_scraper,
            race_loader=race_loader,
            sql_adapter=sql_adapter,
            data_dir=data_dir,
        )
        
        result = sync_service.sync(options)
        return result.to_dict()
        
    finally:
        _sync_in_progress = False


@router.post("/trigger", response_model=SyncResponse)
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
) -> SyncResponse:
    """Trigger a data sync operation.
    
    This runs in the background and returns immediately.
    Use /sync/status to check progress.
    """
    global _sync_in_progress
    
    if _sync_in_progress:
        raise HTTPException(
            status_code=409,
            detail="A sync operation is already in progress",
        )
    
    # Build options
    since_date = None
    if request.days_back:
        since_date = datetime.now() - timedelta(days=request.days_back)
    
    options = SyncOptions(
        season=request.season,
        include_regulations=request.include_regulations,
        include_stewards=request.include_stewards,
        include_race_data=request.include_race_data,
        cleanup_orphans=request.cleanup_orphans,
        force_full_sync=request.force_full_sync,
        since_date=since_date,
    )
    
    # Run in background
    background_tasks.add_task(_run_sync_task, options)
    
    return SyncResponse(
        status="started",
        message=f"Sync started for season {request.season}. Check /sync/status for progress.",
    )


@router.get("/status", response_model=SyncResponse)
async def get_sync_status() -> SyncResponse:
    """Get the status of the sync operation."""
    global _sync_in_progress
    
    if _sync_in_progress:
        return SyncResponse(
            status="in_progress",
            message="Sync operation is currently running",
        )
    
    return SyncResponse(
        status="idle",
        message="No sync operation in progress",
    )


@router.post("/quick", response_model=SyncResponse)
async def quick_sync() -> SyncResponse:
    """Run a quick incremental sync (last 3 days, stewards only).
    
    This is a synchronous operation for fast updates after a race weekend.
    """
    global _sync_in_progress
    
    if _sync_in_progress:
        raise HTTPException(status_code=409, detail="Sync already in progress")
    
    try:
        _sync_in_progress = True
        
        options = SyncOptions(
            season=2025,
            include_regulations=False,
            include_stewards=True,
            include_race_data=True,
            cleanup_orphans=False,
            force_full_sync=False,
            since_date=datetime.now() - timedelta(days=3),
            race_limit=2,  # Only last 2 races
        )
        
        result = _run_sync_task(options)
        
        return SyncResponse(
            status="completed",
            message=f"Quick sync completed with {result['total_changes']} changes",
            result=result,
        )
        
    finally:
        _sync_in_progress = False
```

#### 3.3 Register Sync Router

**File:** `src/adapters/inbound/api/main.py` - Add router

```python
from .routers import chat, health, setup, sync  # Add sync

# ...

app.include_router(sync.router)  # Add this line
```

### Phase 4: Scheduled Sync with Cloud Scheduler (~1-2 hours)

#### 4.1 Create Cloud Scheduler Terraform

**File:** `infra/terraform/scheduler.tf`

```hcl
# Cloud Scheduler for automated data sync

# Enable Cloud Scheduler API
resource "google_project_service" "cloudscheduler" {
  service            = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}

# Service account for scheduler to invoke Cloud Run
resource "google_service_account" "scheduler" {
  account_id   = "f1-agent-scheduler"
  display_name = "F1 Agent Cloud Scheduler"
  description  = "Service account for Cloud Scheduler to invoke sync endpoints"
}

# Grant scheduler permission to invoke Cloud Run
resource "google_cloud_run_v2_service_iam_member" "scheduler_invoker" {
  count    = var.deploy_cloud_run ? 1 : 0
  name     = google_cloud_run_v2_service.f1_agent[0].name
  location = google_cloud_run_v2_service.f1_agent[0].location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

# Daily sync job - runs at 4 AM UTC (after most races finish)
resource "google_cloud_scheduler_job" "daily_sync" {
  count       = var.deploy_cloud_run ? 1 : 0
  name        = "f1-agent-daily-sync"
  description = "Daily incremental sync of F1 penalty data"
  schedule    = "0 4 * * *"  # 4 AM UTC daily
  time_zone   = "UTC"
  region      = var.region

  retry_config {
    retry_count          = 3
    min_backoff_duration = "30s"
    max_backoff_duration = "300s"
  }

  http_target {
    uri         = "${google_cloud_run_v2_service.f1_agent[0].uri}/api/v1/sync/trigger"
    http_method = "POST"
    
    headers = {
      "Content-Type" = "application/json"
    }
    
    body = base64encode(jsonencode({
      season             = 2025
      include_regulations = true
      include_stewards   = true
      include_race_data  = true
      cleanup_orphans    = false
      force_full_sync    = false
      days_back          = 7
    }))

    oidc_token {
      service_account_email = google_service_account.scheduler.email
      audience              = google_cloud_run_v2_service.f1_agent[0].uri
    }
  }

  depends_on = [google_project_service.cloudscheduler]
}

# Post-race sync job - runs Sunday and Monday at 8 PM UTC
resource "google_cloud_scheduler_job" "post_race_sync" {
  count       = var.deploy_cloud_run ? 1 : 0
  name        = "f1-agent-post-race-sync"
  description = "Post-race quick sync for latest stewards decisions"
  schedule    = "0 20 * * 0,1"  # 8 PM UTC on Sunday and Monday
  time_zone   = "UTC"
  region      = var.region

  retry_config {
    retry_count = 2
  }

  http_target {
    uri         = "${google_cloud_run_v2_service.f1_agent[0].uri}/api/v1/sync/quick"
    http_method = "POST"

    oidc_token {
      service_account_email = google_service_account.scheduler.email
      audience              = google_cloud_run_v2_service.f1_agent[0].uri
    }
  }

  depends_on = [google_project_service.cloudscheduler]
}

# Output scheduler job names
output "scheduler_daily_job" {
  description = "Daily sync scheduler job"
  value       = var.deploy_cloud_run ? google_cloud_scheduler_job.daily_sync[0].name : ""
}

output "scheduler_post_race_job" {
  description = "Post-race sync scheduler job"
  value       = var.deploy_cloud_run ? google_cloud_scheduler_job.post_race_sync[0].name : ""
}
```

#### 4.2 Add CLI Sync Command

**File:** `src/adapters/inbound/cli/commands.py` - Add sync command

```python
@app.command()
def sync(
    season: int = typer.Option(2025, help="F1 season year"),
    full: bool = typer.Option(False, help="Force full re-sync of all data"),
    days: int = typer.Option(7, help="Sync documents from the last N days"),
    regulations: bool = typer.Option(True, help="Include regulations"),
    stewards: bool = typer.Option(True, help="Include stewards decisions"),
    races: bool = typer.Option(True, help="Include race data"),
    cleanup: bool = typer.Option(True, help="Clean up orphaned files"),
):
    """Sync the knowledge base with latest F1 data.
    
    Run this after a race weekend to get the latest stewards decisions
    and race control messages.
    
    Examples:
        f1agent sync                    # Incremental sync (last 7 days)
        f1agent sync --full             # Full re-sync of everything
        f1agent sync --days 3           # Just last 3 days
        f1agent sync --no-regulations   # Skip regulations
    """
    from datetime import datetime, timedelta
    from pathlib import Path
    
    from ....adapters.outbound.data_sources.fastf1_adapter import FastF1Adapter
    from ....adapters.outbound.data_sources.fia_adapter import FIAAdapter
    from ....adapters.outbound.sqlite_adapter import SQLiteAdapter
    from ....adapters.outbound.vector_store.qdrant_adapter import QdrantAdapter
    from ....config.settings import settings
    from ....core.services.data_sync_service import DataSyncService, SyncOptions
    
    console.print("[bold]PitWallAI Data Sync[/]\n")
    
    if not settings.qdrant_url or not settings.qdrant_api_key:
        console.print("[red]Error: QDRANT_URL and QDRANT_API_KEY not set[/]")
        raise typer.Exit(1)
    
    try:
        # Build options
        since_date = None if full else datetime.now() - timedelta(days=days)
        
        options = SyncOptions(
            season=season,
            include_regulations=regulations,
            include_stewards=stewards,
            include_race_data=races,
            cleanup_orphans=cleanup,
            force_full_sync=full,
            since_date=since_date,
        )
        
        mode = "full" if full else f"incremental (last {days} days)"
        console.print(f"[dim]Mode: {mode}[/]")
        console.print(f"[dim]Season: {season}[/]\n")
        
        # Initialize services
        vector_store = QdrantAdapter(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            embedding_api_key=settings.google_api_key,
        )
        
        data_dir = Path(settings.data_dir)
        fia_scraper = FIAAdapter(data_dir)
        race_loader = FastF1Adapter(data_dir / "fastf1_cache")
        sql_adapter = SQLiteAdapter()
        
        sync_service = DataSyncService(
            vector_store=vector_store,
            fia_scraper=fia_scraper,
            race_loader=race_loader,
            sql_adapter=sql_adapter,
            data_dir=data_dir,
        )
        
        # Run sync
        with console.status("[bold green]Syncing...[/]"):
            result = sync_service.sync(options)
        
        # Report results
        console.print("\n[bold green]Sync Complete![/]\n")
        console.print(f"  Regulations: +{result.regulations_added} added, ~{result.regulations_updated} updated")
        console.print(f"  Stewards: +{result.stewards_added} added")
        console.print(f"  Race Data: +{result.race_data_added} added")
        
        if result.orphans_removed:
            console.print(f"  Orphans: -{result.orphans_removed} removed")
        
        if result.errors:
            console.print("\n[yellow]Warnings:[/]")
            for error in result.errors:
                console.print(f"  [dim]{error}[/]")
        
        console.print(f"\n[green]Total changes: {result.total_changes}[/]")
        
    except Exception as exc:
        handle_cli_error(exc)
        raise typer.Exit(1)
```

---

## Implementation Checklist

### Phase 1: OpenF1 Adapter
- [ ] Create `src/core/ports/live_data_port.py` with interfaces
- [ ] Create `src/adapters/outbound/data_sources/openf1_adapter.py`
- [ ] Update `src/core/ports/__init__.py` exports
- [ ] Create `tests/unit/test_openf1_adapter.py`
- [ ] Manual test: Verify API calls work during a session

### Phase 2: Live Data Integration
- [ ] Update `src/core/domain/agent.py` - Add `live_messages`, `live_session` to `RetrievalContext`
- [ ] Update `RetrievalContext.get_combined_context()` for live data priority
- [ ] Add `has_live_data` property
- [ ] Update `src/core/services/retrieval_service.py`:
  - [ ] Add `live_data_source` parameter to `__init__`
  - [ ] Add `live_source` lazy-loading property
  - [ ] Implement `_fetch_live_context()`
  - [ ] Implement `_prioritize_driver_messages()`
  - [ ] Add `include_live` parameter to `retrieve()`
- [ ] Update `src/core/services/agent_service.py`:
  - [ ] Add `include_live` parameter to `ask()`
  - [ ] Add live session to sources
- [ ] Update `src/adapters/inbound/api/deps.py`:
  - [ ] Add `get_live_data_source()`
  - [ ] Update `get_retriever()` to inject live source
- [ ] Update `src/adapters/inbound/api/models.py`:
  - [ ] Add `include_live` to `QuestionRequest`
  - [ ] Add `live_session` to `AnswerResponse`
- [ ] Update `src/adapters/inbound/api/routers/chat.py`:
  - [ ] Pass `include_live` to agent
  - [ ] Return `live_session` in response
- [ ] Update `src/core/services/prompts.py` for live awareness
- [ ] Write integration tests

### Phase 3: Data Sync Service
- [ ] Create `src/core/services/data_sync_service.py`
- [ ] Create `src/adapters/inbound/api/routers/sync.py`
- [ ] Register sync router in `main.py`
- [ ] Add `sync` command to CLI
- [ ] Write unit tests for sync service

### Phase 4: Scheduled Sync
- [ ] Create `infra/terraform/scheduler.tf`
- [ ] Add scheduler service account permissions
- [ ] Test Cloud Scheduler triggers
- [ ] Document sync schedule

---

## File Changes Summary

```
src/
├── core/
│   ├── domain/
│   │   └── agent.py                    # MODIFIED: Add live_messages, live_session
│   ├── ports/
│   │   ├── __init__.py                 # MODIFIED: Export live data types
│   │   └── live_data_port.py           # NEW: Live data interface
│   └── services/
│       ├── agent_service.py            # MODIFIED: Add include_live param
│       ├── data_sync_service.py        # NEW: Sync orchestration
│       ├── retrieval_service.py        # MODIFIED: Live data fetching
│       └── prompts.py                  # MODIFIED: Live-aware prompts
│
├── adapters/
│   ├── inbound/
│   │   ├── api/
│   │   │   ├── deps.py                 # MODIFIED: Inject OpenF1Adapter
│   │   │   ├── main.py                 # MODIFIED: Register sync router
│   │   │   ├── models.py               # MODIFIED: Add live fields
│   │   │   └── routers/
│   │   │       ├── chat.py             # MODIFIED: Pass include_live
│   │   │       └── sync.py             # NEW: Sync endpoints
│   │   └── cli/
│   │       └── commands.py             # MODIFIED: Add sync command
│   └── outbound/
│       └── data_sources/
│           └── openf1_adapter.py       # NEW: OpenF1 API client
│
├── infra/terraform/
│   └── scheduler.tf                    # NEW: Cloud Scheduler config
│
└── tests/
    └── unit/
        ├── test_openf1_adapter.py      # NEW: OpenF1 tests
        └── test_data_sync_service.py   # NEW: Sync tests
```

---

## Usage Examples

### Live Data During a Race

```bash
# Ask about a current incident (live data automatically included)
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Why is Verstappen under investigation?"}'

# Response includes live_session when active:
# {
#   "answer": "Max Verstappen is currently under investigation...",
#   "live_session": "Race at Monaco",
#   "sources": [{"source": "[LIVE] Race at Monaco", "doc_type": "live"}, ...]
# }

# For historical queries, disable live:
curl -X POST http://localhost:8000/api/v1/ask \
  -d '{"question": "What happened at Austria 2024?", "include_live": false}'
```

### Data Sync

```bash
# CLI - Incremental sync (recommended after race weekends)
f1agent sync

# CLI - Full sync (for initial setup or recovery)
f1agent sync --full

# API - Trigger async sync
curl -X POST http://localhost:8000/api/v1/sync/trigger \
  -H "Content-Type: application/json" \
  -d '{"season": 2025, "days_back": 7}'

# API - Quick sync (synchronous, stewards only)
curl -X POST http://localhost:8000/api/v1/sync/quick

# API - Check sync status
curl http://localhost:8000/api/v1/sync/status
```

### Cloud Scheduler (Automated)

- **Daily sync**: 4 AM UTC - Full incremental sync
- **Post-race sync**: Sunday/Monday 8 PM UTC - Quick sync for latest decisions

---

## Testing During Live Sessions

1. Wait for an F1 session (Practice, Quali, or Race)
2. Start the API: `uvicorn src.adapters.inbound.api.main:app --reload`
3. Ask: "What's happening with the investigation?" or "Why is [driver] under investigation?"
4. Verify response includes `live_session` field
5. Verify live messages appear first in context

Between sessions:
- Live data will be empty (no errors)
- Falls back to historical data only
- `live_session` will be `null` in response

---

## Estimated Effort

| Phase | Description | Time |
|-------|-------------|------|
| 1 | OpenF1 Adapter | 2-3 hours |
| 2 | Live Integration | 2-3 hours |
| 3 | Data Sync Service | 3-4 hours |
| 4 | Cloud Scheduler | 1-2 hours |
| **Total** | | **8-12 hours** |

---

## Future Enhancements (Out of Scope)

- **Webhook triggers**: FIA document RSS feed monitoring
- **Real-time WebSocket**: Push live updates to frontend
- **Prediction model**: Predict penalty outcomes based on precedent
- **Multi-season support**: Compare across seasons
- **Notification system**: Alert users when new decisions published