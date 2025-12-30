#!/usr/bin/env python3
"""Test the API locally to isolate Cloud Run environment issues."""

import threading
import time

import requests
import uvicorn

from src.adapters.inbound.api.main import app


def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")


# Start server in background thread
thread = threading.Thread(target=run_server, daemon=True)
thread.start()
time.sleep(5)  # Wait for server to start

# Test local API
print("Testing LOCAL API...")
try:
    r = requests.post(
        "http://127.0.0.1:8765/api/v1/ask",
        json={"question": "What is track limits penalty?"},
        timeout=120,
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        answer = data.get("answer", "")
        print("✅ SUCCESS!")
        print(f"Answer: {answer[:400]}...")
        print(f"Sources: {len(data.get('sources', []))}")
    else:
        print(f"❌ Error: {r.text[:500]}")
except Exception as e:
    print(f"Request failed: {e}")
