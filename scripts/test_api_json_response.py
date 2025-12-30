#!/usr/bin/env python3
"""Test script to verify API JSON response format and headers.

This script tests both local and deployed API endpoints to verify:
1. Correct Content-Type headers
2. No BOM in response body
3. Valid JSON parsing
4. Response format matches expected schema
"""

import json
import sys

import requests


def test_api_endpoint(
    url: str, question: str = "What is the penalty for track limits?", timeout: int = 60
) -> dict:
    """Test an API endpoint for proper JSON response.

    Args:
        url: The API endpoint URL
        question: Test question to send
        timeout: Request timeout in seconds

    Returns:
        Dict with test results
    """
    results = {"url": url, "success": False, "checks": {}, "errors": []}

    print(f"\n{'='*60}")
    print(f"Testing: {url}")
    print("=" * 60)

    try:
        # Make the request
        payload = {"question": question}
        print(f"Sending: {json.dumps(payload)}")

        response = requests.post(url, json=payload, timeout=timeout)

        # Check 1: Status code
        results["checks"]["status_code"] = response.status_code
        print(f"\n1. Status Code: {response.status_code}")
        if response.status_code != 200:
            results["errors"].append(f"Non-200 status code: {response.status_code}")

        # Check 2: Content-Type header
        content_type = response.headers.get("Content-Type", "")
        results["checks"]["content_type"] = content_type
        print(f"2. Content-Type: {content_type}")
        if "application/json" not in content_type:
            results["errors"].append(f"Unexpected Content-Type: {content_type}")

        # Check 3: Raw bytes for BOM
        raw_bytes = response.content
        results["checks"]["response_length"] = len(raw_bytes)
        print(f"3. Response Length: {len(raw_bytes)} bytes")

        # Check for UTF-8 BOM at start
        has_bom = raw_bytes.startswith(b"\xef\xbb\xbf")
        results["checks"]["has_utf8_bom"] = has_bom
        print(f"4. Has UTF-8 BOM at start: {has_bom}")
        if has_bom:
            results["errors"].append("Response starts with UTF-8 BOM!")

        # Check first few bytes
        print(f"5. First 50 bytes: {repr(raw_bytes[:50])}")

        # Check 4: BOM character in decoded text
        text = response.text
        has_bom_char = "\ufeff" in text
        results["checks"]["has_bom_char"] = has_bom_char
        print(f"6. Has BOM char (\\ufeff) in text: {has_bom_char}")
        if has_bom_char:
            pos = text.find("\ufeff")
            results["errors"].append(f"BOM character found at position {pos}")
            print(f"   Position: {pos}")
            print(f"   Context: {repr(text[max(0,pos-20):pos+20])}")

        # Check 5: First character
        if text:
            first_char = text[0]
            first_ord = ord(first_char)
            print(f"7. First character: {repr(first_char)} (ord: {first_ord})")
            if first_ord == 0xFEFF:
                results["errors"].append("First character is BOM!")

        # Check 6: JSON validity
        print("\n8. Attempting JSON parse...")
        try:
            data = response.json()
            results["checks"]["json_valid"] = True
            print("   ✅ JSON parsed successfully")

            # Check response structure
            if "answer" in data:
                print(f"   - answer: {data['answer'][:100]}...")
                # Check answer for BOM
                if "\ufeff" in data.get("answer", ""):
                    results["errors"].append("BOM found in answer field")
                    print("   ⚠️  BOM found in answer!")
            if "sources" in data:
                print(f"   - sources: {len(data['sources'])} items")
            if "question" in data:
                print(f"   - question: {data['question']}")
            if "model_used" in data:
                print(f"   - model_used: {data['model_used']}")

        except json.JSONDecodeError as e:
            results["checks"]["json_valid"] = False
            results["errors"].append(f"JSON parse error: {e}")
            print(f"   ❌ JSON parse failed: {e}")
            print(f"   Raw text (first 500 chars): {repr(text[:500])}")

        # Overall success
        results["success"] = len(results["errors"]) == 0

    except requests.exceptions.Timeout:
        results["errors"].append("Request timeout")
        print("❌ Request timed out")
    except requests.exceptions.ConnectionError as e:
        results["errors"].append(f"Connection error: {e}")
        print(f"❌ Connection error: {e}")
    except Exception as e:
        results["errors"].append(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")

    # Summary
    print(f"\n{'='*40}")
    if results["success"]:
        print("✅ PASSED - No issues found")
    else:
        print("❌ FAILED - Issues found:")
        for error in results["errors"]:
            print(f"   - {error}")

    return results


def main():
    """Run API tests against local and/or deployed endpoints."""
    print("=" * 60)
    print("API JSON Response Tester")
    print("=" * 60)

    # Define endpoints to test
    endpoints = [
        # Local endpoint (assumes API is running)
        "http://localhost:8000/api/v1/ask",
        # Deployed endpoint
        "https://f1-penalty-agent-mb4t5jwica-ey.a.run.app/api/v1/ask",
    ]

    # Check command line args for specific endpoint
    if len(sys.argv) > 1:
        if sys.argv[1] == "--local":
            endpoints = [endpoints[0]]
        elif sys.argv[1] == "--deployed":
            endpoints = [endpoints[1]]
        elif sys.argv[1].startswith("http"):
            endpoints = [sys.argv[1]]

    all_results = []

    for endpoint in endpoints:
        results = test_api_endpoint(endpoint)
        all_results.append(results)

    # Overall summary
    print("\n" + "=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in all_results if r["success"])
    total = len(all_results)

    print(f"\nEndpoints tested: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")

    if passed == total:
        print("\n✅ All endpoint tests passed!")
        return 0
    else:
        print("\n❌ Some endpoint tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
