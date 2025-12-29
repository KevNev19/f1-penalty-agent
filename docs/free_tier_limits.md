# Staying within free-tier limits

This repository now ships with configurable rate limiters for the Gemini LLM and the text-embedding endpoint. The defaults are conservative placeholders; set them to match the quotas in your own Google AI Studio and Qdrant Cloud dashboards before running ingestion.

## How to set the limits

1. Look up your current **requests-per-minute** allowances in the provider consoles (Gemini for generation + embeddings, and any write throttles in Qdrant Cloud). Free-tier quotas change over time, so confirm the numbers directly in your account. This repo is developed in an offline CI environment, so we cannot auto-fetch or embed up-to-date quotas—please rely on the dashboards for authoritative numbers.
2. Export the limits in `.env` (or your deployment environment):

```env
LLM_REQUESTS_PER_MINUTE=15
EMBEDDING_REQUESTS_PER_MINUTE=60
```

   - Use the values from step 1; the numbers above are safe defaults, not authoritative quotas.
   - Setting a value to `0` or leaving it unset disables client-side limiting.
3. Run `f1agent setup` and `f1agent chat` as usual; the adapters will block and drip API calls to respect the configured limits.

## Where the limits are enforced
- **LLM calls** (`GeminiClient`): every generate/count/stream request acquires a token from the limiter before hitting the Gemini API.
- **Embedding calls** (`GeminiEmbeddingFunction`): each batch embedding request honors the embedding limiter to keep ingestion within quota.
- **Composition + CLI**: both the FastAPI wiring (`src/composition/container.py`) and CLI setup/status commands now pass the embedding limiter into the vector store so ingestion respects the same controls.

## Tips to avoid throttling
- Run setup during off-peak hours if you are close to the quota ceiling.
- Keep ingestion batch sizes small enough that a single batch cannot exceed your per-minute limit.
- If you hit repeated 429s, lower the configured values until retries stop.

## Ensuring the agent has internet access
Gemini and Qdrant are remote services; the agent container must reach the public internet to work. If you are starting the app in a locked-down environment:

- Verify DNS and egress by curling a public endpoint from inside the container (e.g., `curl https://aistudio.google.com`).
- If your runtime sits behind an HTTP/HTTPS proxy, set `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` in the container environment before starting the app.
- For Kubernetes or Cloud Run, ensure the service account and network policy allow outbound traffic; when using a private subnet, configure a NAT gateway.
- If you must run fully offline, the agent cannot call Gemini or Qdrant; consider stubbing the LLM/retriever ports with local adapters for testing only.
