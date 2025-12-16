# Production Roadmap

This document outlines the current state of the F1 Penalty Agent POC and the improvements required for production readiness.

## Current POC Status

### Retrieval Accuracy Metrics

| Collection | Average Score | Max Score | Min Score |
|------------|--------------|-----------|-----------|
| **Regulations** | 0.64 | 0.76 | 0.53 |
| **Stewards Decisions** | 0.58 | 0.65 | 0.51 |
| **Race Data** | 0.59 | 0.66 | 0.53 |
| **Overall** | **0.60** | 0.76 | 0.51 |

### POC Features Implemented ✅

| Feature | Description | Impact |
|---------|-------------|--------|
| Query Expansion | F1-specific synonym expansion (18 terms) | +3-5% |
| Keyword Boosting | +2% score boost per keyword match (max 10%) | +2-3% |
| Score Threshold | Filter results below 0.5 similarity | Removes noise |
| Content Deduplication | Hash-based duplicate removal | Cleaner results |
| Context-Aware Retrieval | Season/race metadata filtering | Better relevance |
| **Streamlit Chat UI** | Web-based chat interface with F1 theming | User-facing |

### ⚠️ Known Limitations

#### Data Coverage: Stewards Decisions (Critical for Season-Wide Queries)

**Issue:** The FIA scraper currently only retrieves stewards decisions from the **most recent race** (Abu Dhabi 2025), not the entire season.

| Collection | Documents | Coverage |
|------------|-----------|----------|
| Regulations | 32,127 | ✅ Full (2025 + 2026) |
| Stewards Decisions | 456 | ⚠️ **Abu Dhabi 2025 only** |
| Race Data | 68 | Partial (FastF1 messages) |

**Root Cause:**
```python
# Current URL only shows most recent race
DECISIONS_BASE_URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14"
```

The FIA website shows documents per-event. The main page only lists the most recent race.

**Impact:**
- Queries like "What penalties did Norris get in 2025?" only return Abu Dhabi data
- Users expect full season coverage but POC only has one race

**Fix Required (2-3 hours):**

Modify `src/data/fia_scraper.py` to iterate through each race event:

```python
# Add race event URLs for 2025 season
RACE_EVENTS_2025 = [
    "bahrain-grand-prix",
    "saudi-arabian-grand-prix",
    "australian-grand-prix",
    "japanese-grand-prix",
    "chinese-grand-prix",
    "miami-grand-prix",
    "emilia-romagna-grand-prix",
    "monaco-grand-prix",
    # ... all 24 races
    "abu-dhabi-grand-prix",
]

def scrape_all_race_decisions(self, season: int = 2025) -> list[FIADocument]:
    """Scrape stewards decisions from ALL race events in a season."""
    all_docs = []
    for race in RACE_EVENTS_2025:
        event_url = f"{self.FIA_BASE_URL}/documents/season/season-2025-702/event-{race}"
        docs = self.scrape_event_decisions(event_url)
        all_docs.extend(docs)
    return all_docs
```

**Expected Result After Fix:**
- 24 races × ~20-40 decisions per race = **500-800+ stewards decisions**
- Full season coverage for penalty queries

---

## Frontend Implementation

### Current POC: Streamlit Chat Interface ✅

**File:** `app.py`  
**Run:** `streamlit run app.py`

| Feature | Status |
|---------|--------|
| Chat interface | ✅ Implemented |
| Session state (conversation history) | ✅ Implemented |
| F1-themed styling (red/dark theme) | ✅ Implemented |
| Source citations display | ✅ Implemented |
| Example questions sidebar | ✅ Implemented |
| ChromaDB connection status | ✅ Implemented |
| Streaming responses | ⏸️ Deferred (see below) |

### Production Frontend Improvements

#### 5.1 Streaming Responses (Medium Effort)
**Current:** Wait for full response before displaying  
**Production:** Token-by-token streaming like ChatGPT

```python
# Streamlit streaming implementation
def stream_response(prompt):
    response_placeholder = st.empty()
    full_response = ""
    
    for chunk in agent.ask_stream(prompt):
        full_response += chunk
        response_placeholder.markdown(full_response + "▌")
    
    response_placeholder.markdown(full_response)
```

| Metric | Impact |
|--------|--------|
| UX | Significant improvement - feels responsive |
| Effort | 2-4 hours |

#### 5.2 FastAPI + React (High Effort, Production-Ready)

**Architecture:**
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   React     │────▶│   FastAPI   │────▶│  F1 Agent   │
│   Frontend  │◀────│   Backend   │◀────│  + ChromaDB │
└─────────────┘     └─────────────┘     └─────────────┘
     (Vercel)          (Cloud Run)         (GKE/k3d)
```

**Benefits over Streamlit:**
- Better scalability (stateless backend)
- Custom UI/UX (full control)
- Mobile-responsive design
- WebSocket for real-time streaming
- Authentication integration

| Metric | Details |
|--------|---------|
| Effort | 1-2 weeks |
| Frontend | React + TailwindCSS |
| Backend | FastAPI + Pydantic |
| Deployment | Vercel (FE) + Cloud Run (BE) |

#### 5.3 Mobile App (Future)

**Options:**
1. **React Native** - Share code with web frontend
2. **Flutter** - Cross-platform with native performance
3. **PWA** - Progressive Web App from React frontend

| Option | Effort | Best For |
|--------|--------|----------|
| PWA | 1-2 days | Quick mobile support |
| React Native | 2-3 weeks | iOS + Android apps |
| Flutter | 3-4 weeks | Native performance |

---

## Production Improvements Required

### Priority 1: Quick Wins (Low Effort, Medium Impact)

#### 1.1 Upgrade Embedding Model
**Current:** `models/text-embedding-004` (Gemini)  
**Recommended:** `text-embedding-3-large` (OpenAI) or fine-tuned model

| Metric | Current | Expected |
|--------|---------|----------|
| Accuracy | 0.60 avg | 0.65-0.70 avg |
| Cost | ~$0.001/1K tokens | ~$0.005/1K tokens |
| Effort | Config change | 1 hour |

#### 1.2 Increase Chunk Overlap
**Current:** 200 character overlap  
**Recommended:** 400 character overlap

Improves context preservation at chunk boundaries.

---

### Priority 2: Cross-Encoder Re-Ranking (Medium Effort, High Impact)

**What:** Add a second-stage re-ranker using a cross-encoder model after initial retrieval.

**Implementation:**
```python
# Example using sentence-transformers
from sentence_transformers import CrossEncoder
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

# Retrieve top 20 with embeddings, re-rank to top 5
initial_results = vector_store.search(query, top_k=20)
pairs = [(query, r.document.content) for r in initial_results]
scores = reranker.predict(pairs)
reranked = sorted(zip(initial_results, scores), key=lambda x: x[1], reverse=True)[:5]
```

| Metric | Impact |
|--------|--------|
| Accuracy | +10-15% improvement |
| Latency | +200-500ms per query |
| Memory | +500MB for model |
| Effort | 4-8 hours implementation |

**Dependencies:**
- `sentence-transformers` package
- Model download (~100MB)

---

### Priority 3: Fine-Tuned Embeddings (High Effort, High Impact)

**What:** Train a custom embedding model on F1-specific query-document pairs.

**Requirements:**
1. **Training Data:** 5,000-10,000 labeled pairs
   - Query: "What is a 5 second penalty?"
   - Positive Doc: Regulation article about time penalties
   - Negative Docs: Unrelated regulation sections

2. **Infrastructure:**
   - GPU compute for training (A100 recommended)
   - Model hosting infrastructure
   - Versioning and deployment pipeline

3. **Maintenance:**
   - Retrain when new regulations are published
   - A/B testing framework for model comparison

| Metric | Impact |
|--------|--------|
| Accuracy | +15-25% improvement |
| Cost | $500-2000 training compute |
| Effort | 2-4 weeks |

---

### Priority 4: Additional Production Features

#### 4.1 Caching Layer
- Redis/Memcached for frequently asked questions
- Reduces API costs and latency
- Estimated: 60-70% cache hit rate for common queries

#### 4.2 Monitoring & Observability
- Query latency metrics
- Retrieval score distributions
- User feedback collection (thumbs up/down)
- Error rate tracking

#### 4.3 Rate Limiting & Quotas
- Per-user rate limits
- API key management
- Cost controls for embedding API

#### 4.4 Multi-Season Support
- Historical regulations archive
- Season-specific routing
- Regulation change tracking

---

## Production Architecture Recommendation

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │───▶│   F1 Agent      │───▶│   ChromaDB      │
│   (Rate Limit)  │    │   Service       │    │   (Vector DB)   │
└─────────────────┘    └────────┬────────┘    └─────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │ Gemini  │ │ Redis   │ │ Re-rank │
              │ LLM API │ │ Cache   │ │ Model   │
              └─────────┘ └─────────┘ └─────────┘
```

---

## Accuracy Target Summary

| Stage | Average Score | Gap to 0.9 |
|-------|---------------|------------|
| **Current POC** | 0.60 | 0.30 (30%) |
| + Embedding Upgrade | 0.67 | 0.23 (23%) |
| + Cross-Encoder | 0.77 | 0.13 (13%) |
| + Fine-Tuned Embeddings | 0.90+ | 0% ✅ |

---

## Recommendation for Next Phase

For a **production MVP**, we recommend:

1. ✅ Keep current POC implementation
2. 🎯 Add cross-encoder re-ranking (best effort-to-value ratio)
3. 🎯 Add caching layer for cost optimization
4. 🎯 Add basic monitoring

**Timeline:** 2-3 weeks for production MVP

For **enterprise production** with 0.9+ accuracy:
- All of the above, plus fine-tuned embeddings
- **Timeline:** 2-3 months

---

*Last Updated: December 2024*
