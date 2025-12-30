#!/usr/bin/env python3
"""Test script to check if logging configuration adds problematic characters.

This script tests:
1. Logging format strings for BOM issues
2. Exception handling and error message formatting
3. Console output encoding
4. The normalize_text function's effectiveness
"""

import io
import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_logging_format():
    """Test that logging format strings don't add BOM characters."""
    print("\n" + "=" * 60)
    print("Test 1: Logging Format Strings")
    print("=" * 60)

    # Capture log output
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    # Use the same format as the API
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    test_logger = logging.getLogger("test_logging")
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.DEBUG)

    # Log various messages
    test_messages = [
        "Simple message",
        "Message with special chars: éàü",
        "Message with emoji: 🏎️",
        "Message with quote: 'test'",
        "Message with colon: key: value",
    ]

    for msg in test_messages:
        test_logger.info(msg)

    # Check output for BOM
    log_output = log_capture.getvalue()

    print(f"Log output length: {len(log_output)} chars")
    print(f"First 100 chars: {repr(log_output[:100])}")

    issues = []
    if "\ufeff" in log_output:
        pos = log_output.find("\ufeff")
        issues.append(f"BOM found at position {pos}")

    if log_output and ord(log_output[0]) == 0xFEFF:
        issues.append("Log output starts with BOM")

    if issues:
        print("❌ Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("✅ No BOM in logging output")
        return True


def test_json_format_logging():
    """Test JSON format logging (used in production)."""
    print("\n" + "=" * 60)
    print("Test 2: JSON Format Logging")
    print("=" * 60)

    # Capture log output
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    # JSON format as used in logging_config.py
    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
        '"module": "%(module)s", "message": "%(message)s"}'
    )
    handler.setFormatter(formatter)

    test_logger = logging.getLogger("test_json_logging")
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.DEBUG)

    test_logger.info("Test message with special chars: éàü 🏎️")

    log_output = log_capture.getvalue()

    print(f"JSON log output: {repr(log_output[:200])}")

    issues = []
    if "\ufeff" in log_output:
        issues.append("BOM in JSON log output")

    # Try to parse as JSON (line by line)
    for line in log_output.strip().split("\n"):
        if line:
            try:
                json.loads(line)
            except json.JSONDecodeError as e:
                issues.append(f"JSON parse error: {e}")

    if issues:
        print("❌ Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("✅ JSON logging works correctly")
        return True


def test_exception_handling():
    """Test that exception handling doesn't add BOM to error messages."""
    print("\n" + "=" * 60)
    print("Test 3: Exception Handling")
    print("=" * 60)

    from src.core.domain.utils import normalize_text

    # Test various exception scenarios
    test_cases = [
        ("Simple error", ValueError("Simple error")),
        ("Error with special chars", ValueError("Error: éàü")),
        ("Error with BOM", ValueError("Error with BOM: \ufeff")),
        ("Error with colon", ValueError("key: value: more")),
    ]

    issues = []

    for name, error in test_cases:
        error_str = str(error)
        normalized = normalize_text(error_str)

        print(f"\n  {name}:")
        print(f"    Original: {repr(error_str)}")
        print(f"    Normalized: {repr(normalized)}")

        if "\ufeff" in normalized:
            issues.append(f"BOM in normalized error: {name}")

    if issues:
        print("\n❌ Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("\n✅ Exception handling is clean")
        return True


def test_normalize_text_function():
    """Test the normalize_text function thoroughly."""
    print("\n" + "=" * 60)
    print("Test 4: normalize_text Function")
    print("=" * 60)

    from src.core.domain.utils import normalize_text

    test_cases = [
        ("Empty string", "", ""),
        ("None value", None, ""),
        ("Simple text", "Hello world", "Hello world"),
        ("Leading BOM", "\ufeffHello", "Hello"),
        ("Middle BOM", "Hello\ufeffWorld", "HelloWorld"),
        ("Multiple BOM", "\ufeff\ufeffTest\ufeff", "Test"),
        ("BOM variant", "\ufffeTest", "Test"),
        ("CRLF", "Line1\r\nLine2", "Line1\nLine2"),
        ("Extra spaces", "Too   many   spaces", "Too many spaces"),
        ("Unicode preserved", "Café Nürburgring", "Café Nürburgring"),
    ]

    issues = []

    for name, input_val, expected in test_cases:
        result = normalize_text(input_val)
        passed = result == expected
        status = "✅" if passed else "❌"

        print(f"  {status} {name}")
        print(f"      Input: {repr(input_val)}")
        print(f"      Expected: {repr(expected)}")
        print(f"      Got: {repr(result)}")

        if not passed:
            issues.append(f"Failed: {name}")

    if issues:
        print("\n❌ Some tests failed!")
        return False
    else:
        print("\n✅ All normalize_text tests passed")
        return True


def test_api_error_response_format():
    """Test that API error responses don't contain BOM."""
    print("\n" + "=" * 60)
    print("Test 5: API Error Response Format")
    print("=" * 60)

    from src.core.domain.utils import normalize_text

    # Simulate error messages that might be returned
    error_messages = [
        "Invalid request",
        "An error occurred while processing your question. Please try again.",
        "'ascii' codec can't encode character '\\ufeff' in position 0",
        "Error: something went wrong",
        "Field 'question' is required",
    ]

    issues = []

    for msg in error_messages:
        normalized = normalize_text(msg)

        # Check if it can be JSON encoded
        try:
            json.dumps({"error": normalized})
            print(f"  ✅ Can encode: {msg[:50]}...")
        except Exception:
            print(f"  ❌ Encode failed: {msg[:50]}...")
            issues.append(f"Cannot JSON encode: {msg[:50]}")

    if issues:
        print("\n❌ Some messages failed JSON encoding")
        return False
    else:
        print("\n✅ All error messages can be JSON encoded")
        return True


def main():
    """Run all logging and encoding tests."""
    print("=" * 60)
    print("Logging and Encoding Tests")
    print("=" * 60)

    results = [
        ("Logging Format", test_logging_format()),
        ("JSON Logging", test_json_format_logging()),
        ("Exception Handling", test_exception_handling()),
        ("normalize_text", test_normalize_text_function()),
        ("Error Response Format", test_api_error_response_format()),
    ]

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
