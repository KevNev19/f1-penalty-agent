#!/usr/bin/env python3
"""Script to scan Qdrant database for BOM characters in stored data.

This script connects to the Qdrant database and checks all collections
for any documents containing BOM (Byte Order Mark) characters that could
cause JSON encoding issues in the API response.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.outbound.vector_store.qdrant_adapter import QdrantAdapter as QdrantVectorStore
from src.config.settings import settings


def check_text_for_problematic_chars(text: str, field_name: str) -> list[dict]:
    """Check a text string for BOM and other problematic characters.

    Args:
        text: The text to check
        field_name: Name of the field being checked (for reporting)

    Returns:
        List of issues found
    """
    issues = []

    if not text:
        return issues

    # Check for BOM characters
    if "\ufeff" in text:
        pos = text.find("\ufeff")
        issues.append(
            {
                "char": "BOM (\\ufeff)",
                "field": field_name,
                "position": pos,
                "context": repr(text[max(0, pos - 20) : pos + 20]),
            }
        )

    if "\ufffe" in text:
        pos = text.find("\ufffe")
        issues.append(
            {
                "char": "BOM (\\ufffe)",
                "field": field_name,
                "position": pos,
                "context": repr(text[max(0, pos - 20) : pos + 20]),
            }
        )

    # Check for null bytes
    if "\x00" in text:
        pos = text.find("\x00")
        issues.append(
            {
                "char": "NULL byte (\\x00)",
                "field": field_name,
                "position": pos,
                "context": repr(text[max(0, pos - 20) : pos + 20]),
            }
        )

    # Check for first character being BOM
    if text and ord(text[0]) == 0xFEFF:
        issues.append(
            {"char": "Leading BOM", "field": field_name, "position": 0, "context": repr(text[:50])}
        )

    return issues


def scan_collection(vector_store: QdrantVectorStore, collection_name: str) -> dict:
    """Scan a collection for problematic characters.

    Args:
        vector_store: The Qdrant vector store instance
        collection_name: Name of the collection to scan

    Returns:
        Dict with scan results
    """
    print(f"\n{'='*60}")
    print(f"Scanning collection: {collection_name}")
    print("=" * 60)

    results = {
        "collection": collection_name,
        "documents_scanned": 0,
        "documents_with_issues": 0,
        "issues": [],
    }

    try:
        client = vector_store._get_client()

        # Get collection stats
        stats = vector_store.get_collection_stats(collection_name)
        total_count = stats.get("count", 0)
        print(f"Total documents in collection: {total_count}")

        if total_count == 0:
            print("  [Empty collection - skipping]")
            return results

        # Scroll through all points in batches
        batch_size = 100
        offset = None

        while True:
            # Use scroll to get all points
            scroll_result = client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            points, next_offset = scroll_result

            if not points:
                break

            for point in points:
                results["documents_scanned"] += 1
                doc_issues = []

                payload = point.payload or {}

                # Check content field
                content = payload.get("content", "")
                doc_issues.extend(check_text_for_problematic_chars(content, "content"))

                # Check all string fields in payload
                for key, value in payload.items():
                    if key == "content":
                        continue
                    if isinstance(value, str):
                        doc_issues.extend(
                            check_text_for_problematic_chars(value, f"metadata.{key}")
                        )

                if doc_issues:
                    results["documents_with_issues"] += 1
                    doc_id = payload.get("doc_id", f"point_{point.id}")
                    title = payload.get("title", payload.get("source", "Unknown"))[:50]

                    print(f"\n  ⚠️  Document: {doc_id}")
                    print(f"      Title: {title}")
                    for issue in doc_issues:
                        print(
                            f"      - {issue['char']} in {issue['field']} at pos {issue['position']}"
                        )
                        print(f"        Context: {issue['context']}")
                        results["issues"].append({"doc_id": doc_id, "title": title, **issue})

            if next_offset is None:
                break
            offset = next_offset

    except Exception as e:
        print(f"  ❌ Error scanning collection: {e}")
        results["error"] = str(e)

    print(
        f"\n  Summary: Scanned {results['documents_scanned']} documents, "
        f"found {results['documents_with_issues']} with issues"
    )

    return results


def main():
    """Main function to scan all collections for BOM issues."""
    print("=" * 60)
    print("BOM Character Database Scanner")
    print("=" * 60)
    print(f"\nConnecting to Qdrant at: {settings.qdrant_url}")

    # Initialize vector store
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        embedding_api_key=settings.google_api_key,
    )

    # Scan all collections
    all_results = []

    for collection in [
        QdrantVectorStore.REGULATIONS_NAMESPACE,
        QdrantVectorStore.STEWARDS_NAMESPACE,
        QdrantVectorStore.RACE_DATA_NAMESPACE,
    ]:
        results = scan_collection(vector_store, collection)
        all_results.append(results)

    # Summary
    print("\n" + "=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)

    total_scanned = sum(r["documents_scanned"] for r in all_results)
    total_with_issues = sum(r["documents_with_issues"] for r in all_results)
    total_issues = sum(len(r["issues"]) for r in all_results)

    print(f"\nTotal documents scanned: {total_scanned}")
    print(f"Documents with BOM/problematic chars: {total_with_issues}")
    print(f"Total issues found: {total_issues}")

    if total_issues > 0:
        print("\n⚠️  BOM characters found in database!")
        print("   These need to be cleaned before the API can return clean JSON.")
    else:
        print("\n✅ No BOM characters found in database.")
        print("   The issue may be elsewhere (API layer, logging, etc.)")

    return total_issues


if __name__ == "__main__":
    issue_count = main()
    sys.exit(1 if issue_count > 0 else 0)
