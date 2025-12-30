#!/usr/bin/env python3
"""Compare local and Secret Manager API keys after update."""

import subprocess

from dotenv import dotenv_values

# Get local key
local = dotenv_values(".env").get("GOOGLE_API_KEY", "")

# Get secret manager key
result = subprocess.run(
    [
        r"C:\Users\addis\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "secrets",
        "versions",
        "access",
        "latest",
        "--secret=f1-agent-google-api-key",
        "--project=gen-lang-client-0855046443",
    ],
    capture_output=True,
    text=True,
)
secret = result.stdout.strip()

print("=" * 60)
print("KEY COMPARISON - Local vs Secret Manager")
print("=" * 60)

print("\n=== Local .env ===")
print(f"Length: {len(local)}")
print(
    f"First char: {repr(local[0]) if local else 'empty'} (ord: {ord(local[0]) if local else 'N/A'})"
)
print(f"Starts with BOM: {local.startswith(chr(0xfeff))}")
print(f"Value: {local[:15]}...{local[-5:]}")

print("\n=== Secret Manager ===")
print(f"Length: {len(secret)}")
print(
    f"First char: {repr(secret[0]) if secret else 'empty'} (ord: {ord(secret[0]) if secret else 'N/A'})"
)
print(f"Starts with BOM: {secret.startswith(chr(0xfeff))}")
print(f"Value: {secret[:15]}...{secret[-5:]}")

print("\n=== COMPARISON ===")
if local == secret:
    print("✅ MATCH - Local and Secret Manager keys are identical!")
else:
    print("❌ MISMATCH")
    print(f"Local length: {len(local)}, Secret length: {len(secret)}")
    if local.strip() == secret.strip():
        print("  → Keys match after stripping whitespace")
    elif local.lstrip(chr(0xFEFF)) == secret.lstrip(chr(0xFEFF)):
        print("  → Keys match after stripping BOM")
