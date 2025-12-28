# Hexagonal Architecture Refactor Plan

This document outlines how to transition the current FastAPI + agent + RAG implementation into a hexagonal (ports-and-adapters) architecture. It lists the proposed layers, new interfaces, and an incremental migration strategy so we can stage changes without breaking existing behavior.

## Current coupling highlights
- **API composition is flat:** `src/api/main.py` wires routers directly into the app lifecycle and logging without any application service boundary. HTTP concerns are mixed with startup/shutdown logic and the routers touch concrete orchestrators.
- **Agent owns orchestration and infrastructure:** `F1Agent` directly depends on `GeminiClient` and `F1Retriever`, mixes classification, prompt construction, retrieval, and LLM calls in a single class, and returns transport-ready strings rather than domain models.
- **Retriever encapsulates infra choices:** Retrieval is bound to Qdrant, the cross-encoder reranker, and concrete document schemas, making it hard to swap vector stores or adjust scoring without rewriting the agent.

## Target layering
- **Domain layer (pure):** Domain models like `Question`, `QueryType`, `RetrievedChunk`, `Answer`, and `SourceCitation`; pure services for query classification and prompt building; no FastAPI, Qdrant, or Gemini imports.
- **Application layer (use-cases):** Services such as `AskQuestionService` and `SetupKnowledgeBaseService` that orchestrate domain services and ports, returning domain responses. Contains transactional and policy logic (e.g., select prompt template based on query type, enforce source limits, assemble response DTOs).
- **Ports (interfaces):**
  - `LLMPort` with `generate(prompt, system_prompt)` and `stream(prompt, system_prompt)`.
  - `RetrievalPort` with `retrieve(query, hints, top_k)` and context extraction helpers.
  - `IngestionPort` for loading/storing FIA documents and race data.
  - `TelemetryPort` (optional) for structured logs/metrics/trace spans.
- **Adapters (infrastructure/entrypoints):**
  - Infrastructure: Gemini client adapter implements `LLMPort`; Qdrant + reranker implements `RetrievalPort`; filesystem/GCS ingest implements `IngestionPort`.
  - Entrypoints: FastAPI router layer maps HTTP DTOs to application requests; CLI/batch adapters reuse the same application services.
  - Configuration/composition root builds the graph of adapters and injects them into the application layer.

## Directory layout proposal
```
src/
  domain/
    models/ (Question, Answer, SourceCitation, QueryType, RetrievalContext)
    services/ (QueryClassifier, PromptBuilder)
  application/
    services/ (AskQuestionService, SetupKnowledgeBaseService)
    dto.py (request/response contracts for use-cases)
  ports/
    llm.py (LLMPort)
    retrieval.py (RetrievalPort)
    ingestion.py (IngestionPort)
    telemetry.py (TelemetryPort)
  adapters/
    api/ (FastAPI routers, request/response schemas)
    llm/gemini_client.py (implements LLMPort)
    retrieval/qdrant_retriever.py (implements RetrievalPort)
    ingestion/...
  composition/
    container.py (wire adapters to services for API/CLI)
```

## Migration steps
1. **Extract domain types and classifiers**
   - Move `QueryType` and prompt selection logic into `domain` services and create a pure `PromptBuilder` that accepts domain `RetrievalContext` without referencing Gemini/Qdrant classes.
2. **Introduce ports**
   - Define `LLMPort` and `RetrievalPort` interfaces and update `GeminiClient` and `F1Retriever` to implement them. Keep existing names initially via thin adapter wrappers to minimize churn.
3. **Create an application service**
   - Add `AskQuestionService` that depends only on ports and domain services. Port the logic currently in `F1Agent.ask`/`ask_stream` to this service and return a domain `Answer` aggregate (text + citations + classification).
4. **Refit entrypoints**
   - Update FastAPI routers to call the application service, mapping HTTP schemas to the service request DTOs and back. Preserve streaming endpoints by delegating to the service’s generator-returning method.
5. **Backfill tests**
   - Unit-test domain services (classifier, prompt builder) and the application service with mocked ports. Add adapter-level tests for Gemini/Qdrant wiring where feasible.
6. **Decompose remaining orchestrators**
   - Gradually remove direct coupling in `F1Agent` by turning it into a thin facade over the application service or deprecating it entirely.
7. **Composition root**
   - Add a `composition/container.py` (or dependency injection module) that builds concrete adapters, injects ports into services, and exposes factories for API/CLI setups.

## Incremental delivery notes
- Start with interfaces and adapters that wrap existing classes to avoid breaking API handlers. Once ports are in place, refactor the handlers to depend on the application service.
- Maintain backward compatibility for environment configuration by having the composition root read the same settings currently consumed by `GeminiClient` and the retriever.
- Use feature flags or routing toggles to switch the API to the new service while keeping the existing `F1Agent` available during the transition.
