#!/usr/bin/env python
"""Test script to debug embedding and chromadb indexing."""
import sys

print("Testing embedding and indexing...", flush=True)

from src.config import settings
print(f"API key configured: {bool(settings.google_api_key)}", flush=True)

from src.rag.vectorstore import VectorStore, GeminiEmbeddingFunction
print("Imports complete.", flush=True)

# Test embedding function directly
ef = GeminiEmbeddingFunction(settings.google_api_key)
print("EF created.", flush=True)

try:
    result = ef(["Test embedding text"])
    print(f"Embedding result: {len(result)} vectors, {len(result[0])} dims", flush=True)
except Exception as e:
    print(f"Embedding error: {e}", flush=True)
    sys.exit(1)

try:
    print("Creating VectorStore...", file=sys.stderr)
    vs = VectorStore(settings.chroma_persist_dir, settings.google_api_key)
    print("VectorStore created.", file=sys.stderr)

    print("Getting collection...", file=sys.stderr)
    col = vs._get_collection("f1_regulations")
    print(f"Collection count before: {col.count()}", file=sys.stderr)
except Exception as e:
    print(f"Setup error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

from src.rag.vectorstore import Document
doc = Document(content="Test regulation about 5 second time penalties in F1", metadata={"doc_type": "test"}, doc_id="test_5sec_penalty")

try:
    count = vs.add_documents([doc], "f1_regulations")
    print(f"Added {count} documents", flush=True)
except Exception as e:
    print(f"Add error: {e}", flush=True)
    import traceback
    traceback.print_exc()
    
stats = vs.get_collection_stats("f1_regulations")
print(f"Final stats: {stats}", flush=True)
