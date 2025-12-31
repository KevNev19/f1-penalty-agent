#!/usr/bin/env python3
"""Compare local and Secret Manager API keys after update."""

import hashlib
import subprocess

from dotenv import dotenv_values


def hash_key(key: str) -> str:
    """Return SHA-256 hash of the key."""
    if not key:
        return ""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


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

local_hash = hash_key(local)
secret_hash = hash_key(secret)

print("=" * 60)
print("KEY COMPARISON - Local vs Secret Manager (HASHED)")
print("=" * 60)

print("\n=== Local .env ===")
print(f"Length: {len(local)}")
print(f"Hash:   {local_hash}")
print(f"Starts with BOM: {local.startswith(chr(0xFEFF))}")

print("\n=== Secret Manager ===")
print(f"Length: {len(secret)}")
print(f"Hash:   {secret_hash}")
print(f"Starts with BOM: {secret.startswith(chr(0xFEFF))}")

print("\n=== COMPARISON ===")
if local == secret:
    print("✅ MATCH - Local and Secret Manager keys are identical!")
else:
    print("❌ MISMATCH")
    print(f"Local length: {len(local)}, Secret length: {len(secret)}")

    # Check if they match after common cleaning operations
    if local.strip() == secret.strip():
        print("  → Keys match after stripping whitespace")
    elif local.lstrip(chr(0xFEFF)) == secret.lstrip(chr(0xFEFF)):
        print("  → Keys match after stripping BOM")
    else:
        print("  → Keys are fundamentally different")
