#!/usr/bin/env python3
"""Development environment setup script.

This script is called automatically by poetry install via the post-install hook.
It ensures pre-commit hooks are installed for all developers who clone the repo.
"""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Install pre-commit hooks if in a git repository."""
    # Check if we're in a git repo
    git_dir = Path(".git")
    if not git_dir.exists():
        print("Not in a git repository, skipping pre-commit install")
        return 0

    # Check if pre-commit hooks are already installed
    pre_commit_hook = git_dir / "hooks" / "pre-commit"
    if pre_commit_hook.exists():
        print("pre-commit hooks already installed")
        return 0

    # Install pre-commit hooks
    print("Installing pre-commit hooks...")
    try:
        subprocess.run(
            ["pre-commit", "install", "--install-hooks"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["pre-commit", "install", "--hook-type", "pre-push"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✅ pre-commit hooks installed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Failed to install pre-commit hooks: {e.stderr}")
        return 1
    except FileNotFoundError:
        print("pre-commit not found, skipping hook installation")
        return 0


if __name__ == "__main__":
    sys.exit(main())
