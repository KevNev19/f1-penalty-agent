#!/usr/bin/env python3
"""Comprehensive local API test suite."""

import threading
import time

import requests
import uvicorn

# Test questions covering different query types
TEST_QUESTIONS = [
    "What is the penalty for track limits?",
    "Why do drivers get 5 second penalties?",
    "What is Article 33.4 about?",
    "Explain unsafe release penalty",
    "What happens when a driver exceeds track limits 3 times?",
]


def run_server():
    from src.adapters.inbound.api.main import app

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="error")


def main():
    # Start server
    print("Starting local server...")
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(5)

    base_url = "http://127.0.0.1:8765"

    # Test 1: Health check
    print("\n" + "=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)
    try:
        r = requests.get(f"{base_url}/health", timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")
        assert r.status_code == 200, "Health check failed"
        print("✅ PASSED")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test 2: Setup status
    print("\n" + "=" * 60)
    print("TEST 2: Setup Status")
    print("=" * 60)
    try:
        r = requests.get(f"{base_url}/api/v1/setup/status", timeout=30)
        print(f"Status: {r.status_code}")
        data = r.json()
        print(f"Is Populated: {data.get('is_populated')}")
        print(f"Collections: {data.get('collections')}")
        assert r.status_code == 200, "Setup status check failed"
        assert data.get("is_populated"), "Database not populated"
        print("✅ PASSED")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test 3: Multiple /ask questions
    print("\n" + "=" * 60)
    print("TEST 3: Ask Questions (Multiple)")
    print("=" * 60)

    passed = 0
    failed = 0

    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"\n--- Question {i}: {question[:50]}...")
        try:
            r = requests.post(
                f"{base_url}/api/v1/ask",
                json={"question": question},
                timeout=120,
            )
            if r.status_code == 200:
                data = r.json()
                answer = data.get("answer", "")
                sources = data.get("sources", [])
                print("  Status: 200 ✅")
                print(f"  Answer length: {len(answer)} chars")
                print(f"  Sources: {len(sources)}")
                print(f"  Preview: {answer[:100]}...")
                passed += 1
            else:
                print(f"  Status: {r.status_code} ❌")
                print(f"  Error: {r.text[:200]}")
                failed += 1
        except Exception as e:
            print(f"  ❌ Request failed: {e}")
            failed += 1

    print(f"\n--- Results: {passed}/{len(TEST_QUESTIONS)} passed ---")

    # Test 4: Edge cases
    print("\n" + "=" * 60)
    print("TEST 4: Edge Cases")
    print("=" * 60)

    # Empty question should fail gracefully
    print("\n--- Empty question ---")
    try:
        r = requests.post(f"{base_url}/api/v1/ask", json={"question": ""}, timeout=30)
        print(f"Status: {r.status_code}")
        if r.status_code == 422:  # Validation error expected
            print("✅ Correctly rejected empty question")
        else:
            print(f"Response: {r.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

    # Unicode question
    print("\n--- Unicode question ---")
    try:
        r = requests.post(
            f"{base_url}/api/v1/ask",
            json={"question": "What is the penalty for Pérez at São Paulo?"},
            timeout=120,
        )
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print("✅ Unicode handled correctly")
            print(f"Answer preview: {data.get('answer', '')[:100]}...")
        else:
            print(f"Response: {r.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("ALL LOCAL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
