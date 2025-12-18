import sys
import os
import shutil
import traceback

# Add root to sys.path
sys.path.append(os.getcwd())

from src.rag.vectorstore import GeminiEmbeddingFunction
from src.config import settings
import chromadb

# Ensure rich console is available (simulating vectorstore environment)
try:
    from rich.console import Console
    console = Console()
    print("Rich console imported successfully.")
except ImportError:
    print("Rich console NOT found.")

def run_debug():
    print(f"Python: {sys.version}")
    print("Initializing EF...")
    
    try:
        ef = GeminiEmbeddingFunction(settings.google_api_key)
        print("EF Initialized.")
    except Exception as e:
        print(f"EF Init failed: {e}")
        return

    # Simulate the failing payload (338 docs)
    N = 338
    print(f"Generating {N} dummy texts...")
    texts = [f"This is test document {i} content. " * 20 for i in range(N)]
    
    print("Step 1: Generating embeddings (Call ef)...")
    try:
        embeddings = ef(texts)
        print(f"Success! Generated {len(embeddings)} embeddings.")
    except Exception as e:
        print(f"CRASH in ef: {e}")
        traceback.print_exc()
        return

    print("Step 2: Adding to ChromaDB (Local Persist)...")
    db_path = "data/chroma_debug"
    
    try:
        client = chromadb.PersistentClient(path=db_path)
        col = client.get_or_create_collection("debug_col", metadata={"hnsw:space": "cosine"})
        
        # Add in one batch
        ids = [f"id_{i}" for i in range(len(texts))]
        metadatas = [{"source": "test"} for _ in range(len(texts))]
        
        col.add(documents=texts, embeddings=embeddings, ids=ids, metadatas=metadatas)
        print("Success! Added to ChromaDB.")
        print(f"Collection count: {col.count()}")
        
    except Exception as e:
        print(f"CRASH in ChromaDB Add: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_debug()
