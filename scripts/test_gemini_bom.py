#!/usr/bin/env python3
"""Test Gemini client locally to check for BOM in responses."""

import sys

sys.path.insert(0, ".")

from src.adapters.outbound.llm.gemini_adapter import GeminiAdapter as GeminiClient
from src.config.settings import settings

client = GeminiClient(settings.google_api_key, settings.llm_model)
print("Testing Gemini client...")

try:
    response = client.generate("What is a track limit penalty?", max_tokens=100)
    print(f"Response received, length: {len(response)}")
    print(f"First 10 chars: {repr(response[:10])}")
    if response:
        print(f"First char ord: {ord(response[0])}")
    print(f"Has BOM: {chr(0xfeff) in response}")
    print(f"Response preview: {response[:200]}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
