#!/usr/bin/env python3
"""Setup script for Qdrant Cloud connection verification.

This script verifies connectivity to your Qdrant Cloud cluster and creates
the required collections if they don't exist.

Run with: python scripts/setup_qdrant.py

Requirements:
  - QDRANT_URL environment variable set (or in .env file)
  - QDRANT_API_KEY environment variable set (or in .env file)
"""

import os
import sys
from importlib.util import find_spec
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file if it exists
from dotenv import load_dotenv

load_dotenv()


def setup_qdrant():
    """Verify Qdrant Cloud connection and create collections."""
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")

    if not url:
        print("❌ QDRANT_URL not set!")
        print("   Set this in your .env file or as an environment variable.")
        print("   Get a free cluster at: https://cloud.qdrant.io/")
        return False

    if not api_key:
        print("❌ QDRANT_API_KEY not set!")
        print("   Set this in your .env file or as an environment variable.")
        return False

    print(f"🔗 Connecting to Qdrant at: {url}")

    if find_spec("qdrant_client") is None:
        print("❌ qdrant-client not installed!")
        print("   Run: poetry install")
        return False

    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams

    try:
        client = QdrantClient(url=url, api_key=api_key)
        
        # Test connection
        collections = client.get_collections()
        print("✅ Connected successfully!")
        print(f"   Found {len(collections.collections)} existing collections")

        # Define required collections
        required_collections = ["regulations", "stewards_decisions", "race_data"]
        embedding_dim = 768  # Gemini text-embedding-004

        for collection_name in required_collections:
            exists = any(c.name == collection_name for c in collections.collections)
            
            if exists:
                info = client.get_collection(collection_name)
                print(f"   ✅ {collection_name}: {info.points_count} vectors")
            else:
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=embedding_dim,
                        distance=Distance.COSINE,
                    ),
                )
                print(f"   🆕 Created collection: {collection_name}")

        print("\n✅ Qdrant setup complete!")
        print("\nNext steps:")
        print("  1. Run: poetry run f1agent setup --limit 3")
        print("  2. Test: poetry run f1agent ask 'What is the penalty for track limits?'")
        return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  - Check that QDRANT_URL is correct (should be https://...)")
        print("  - Check that QDRANT_API_KEY is valid")
        print("  - Ensure your cluster is running at cloud.qdrant.io")
        return False


if __name__ == "__main__":
    success = setup_qdrant()
    sys.exit(0 if success else 1)
