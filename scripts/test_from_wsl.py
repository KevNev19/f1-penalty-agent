#!/usr/bin/env python3
"""Test API from Linux/WSL to rule out Windows encoding issues."""

import json

import requests

url = "https://f1-penalty-agent-mb4t5jwica-ey.a.run.app/api/v1/ask"

# Explicitly create clean JSON without any BOM
payload = {"question": "test"}
json_data = json.dumps(payload, ensure_ascii=True)

print("Testing from Linux/WSL...")
print(f"URL: {url}")
print(f"Payload bytes: {json_data.encode('utf-8')[:50]}")
print(f"First byte: {json_data.encode('utf-8')[0]}")
print()

headers = {"Content-Type": "application/json; charset=utf-8"}

try:
    response = requests.post(url, data=json_data.encode("utf-8"), headers=headers, timeout=120)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
