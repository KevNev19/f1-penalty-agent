#!/usr/bin/env python3
"""Quick test to verify the BOM fix is deployed."""

import requests

url = "https://f1-penalty-agent-mb4t5jwica-ey.a.run.app/api/v1/ask"
payload = {"question": "What is the penalty for track limits?"}

print("Testing deployed API...")
print(f"URL: {url}\n")

try:
    response = requests.post(url, json=payload, timeout=120)

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print("\n✅ SUCCESS! API is working!\n")
        print(f"Answer preview: {data.get('answer', '')[:200]}...")
        print(f"\nSources: {len(data.get('sources', []))} found")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")

except Exception as e:
    print(f"Request failed: {e}")
