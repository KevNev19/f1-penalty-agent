#!/usr/bin/env python3
"""Compare local and Secret Manager API keys after update."""

import secrets
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

# Check for BOM
local_bom = local.startswith(chr(0xFEFF))
secret_bom = secret.startswith(chr(0xFEFF))

print("\n=== COMPARISON ===")
# Use constant-time comparison to prevent timing attacks
if secrets.compare_digest(local, secret):
    print("✅ MATCH - Local and Secret Manager keys are identical!")
else:
    print("❌ MISMATCH")
    print("Check your .env file and Google Secret Manager to ensure they match.")
    print("Tip: Check for hidden BOM characters or whitespace.")
