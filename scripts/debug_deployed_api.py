#!/usr/bin/env python3
"""Debug script to get the full error details from the deployed API."""

import json

import requests

url = "https://f1-penalty-agent-mb4t5jwica-ey.a.run.app/api/v1/ask"
payload = {"question": "test"}

print("Testing deployed API to capture full error...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload)}")
print()

try:
    response = requests.post(url, json=payload, timeout=90)

    print(f"Status Code: {response.status_code}")
    print("Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")

    print("\nRaw Content (hex):")
    print(response.content[:500].hex())

    print("\nRaw Content (repr):")
    print(repr(response.content[:500]))

    print("\nResponse Text:")
    print(response.text)

    print("\n\nTrying to parse as JSON...")
    try:
        data = response.json()
        print("JSON parsed successfully:")
        print(json.dumps(data, indent=2, default=str))
    except Exception as e:
        print(f"JSON parse failed: {e}")

except Exception as e:
    print(f"Request failed: {type(e).__name__}: {e}")
