#!/usr/bin/env python3
"""
Cross-platform infrastructure setup script.
Uses Docker Desktop's built-in Kubernetes (no k3d needed).

Usage:
    python scripts/setup_infra.py          # Full setup
    python scripts/setup_infra.py --check  # Check prerequisites only
    python scripts/setup_infra.py --clean  # Remove resources
"""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        cls.GREEN = cls.YELLOW = cls.RED = cls.CYAN = cls.BOLD = cls.RESET = ""


if platform.system() == "Windows":
    try:
        os.system("")  # Enable ANSI
    except Exception:
        Colors.disable()


def log_info(msg: str):
    print(f"{Colors.CYAN}ℹ️  {msg}{Colors.RESET}")


def log_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")


def log_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")


def log_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")


def get_os_info() -> dict:
    """Detect operating system."""
    system = platform.system()
    return {
        "system": system,
        "is_windows": system == "Windows",
        "is_mac": system == "Darwin",
        "is_linux": system == "Linux",
    }


def run_cmd(cmd: list, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a command."""
    kwargs = {"check": check}
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    return subprocess.run(cmd, **kwargs)


def check_docker() -> bool:
    """Check Docker is running."""
    try:
        run_cmd(["docker", "info"], capture=True)
        log_success("Docker is running")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        log_error("Docker is not running. Please start Docker Desktop.")
        return False


def check_kubernetes() -> bool:
    """Check if Docker Desktop Kubernetes is enabled."""
    try:
        # Check if docker-desktop context exists
        result = run_cmd(["kubectl", "config", "get-contexts"], capture=True)
        if "docker-desktop" not in result.stdout:
            log_error("Docker Desktop Kubernetes is not enabled.")
            print()
            log_info("To enable Kubernetes in Docker Desktop:")
            print("  1. Open Docker Desktop")
            print("  2. Go to Settings (⚙️)")
            print("  3. Click 'Kubernetes' in the left sidebar")
            print("  4. Check 'Enable Kubernetes'")
            print("  5. Click 'Apply & Restart'")
            print("  6. Wait for Kubernetes to start (green icon)")
            print()
            return False

        # Switch to docker-desktop context
        run_cmd(["kubectl", "config", "use-context", "docker-desktop"], capture=True)

        # Check if cluster is responding
        result = run_cmd(["kubectl", "cluster-info"], capture=True, check=False)
        if result.returncode != 0:
            log_warning("Kubernetes not ready yet. Please wait for it to start.")
            return False

        log_success("Docker Desktop Kubernetes is enabled and running")
        return True
    except FileNotFoundError:
        log_error("kubectl not found")
        return False


def deploy_chromadb() -> bool:
    """Deploy ChromaDB to the cluster."""
    log_info("Deploying ChromaDB...")

    script_dir = Path(__file__).parent.parent

    try:
        # Apply namespace
        run_cmd(["kubectl", "apply", "-f", str(script_dir / "infra/k8s/namespace.yaml")])

        # Apply ChromaDB deployment
        run_cmd(["kubectl", "apply", "-f", str(script_dir / "infra/k8s/chromadb/deployment.yaml")])

        log_success("ChromaDB deployment created")

        # Wait for deployment
        log_info("Waiting for ChromaDB to be ready...")
        run_cmd(
            [
                "kubectl",
                "wait",
                "--for=condition=Available",
                "deployment/chromadb",
                "-n",
                "f1-agent",
                "--timeout=180s",
            ]
        )
        log_success("ChromaDB is ready!")
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to deploy: {e}")
        return False


def clean_resources() -> bool:
    """Remove ChromaDB resources."""
    log_info("Removing ChromaDB resources...")
    try:
        run_cmd(["kubectl", "delete", "namespace", "f1-agent", "--ignore-not-found"], check=False)
        log_success("Resources removed")
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="F1 Penalty Agent Infrastructure Setup")
    parser.add_argument("--check", action="store_true", help="Check prerequisites only")
    parser.add_argument("--clean", action="store_true", help="Remove resources")
    args = parser.parse_args()

    print()
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}  F1 Penalty Agent - Infrastructure Setup{Colors.RESET}")
    print(f"{Colors.BOLD}  (Using Docker Desktop Kubernetes){Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")

    os_info = get_os_info()
    log_info(f"Operating System: {os_info['system']}")

    # Check Docker
    if not check_docker():
        sys.exit(1)

    # Check Kubernetes
    if not check_kubernetes():
        sys.exit(1)

    if args.check:
        print()
        log_success("All prerequisites met!")
        sys.exit(0)

    if args.clean:
        clean_resources()
        sys.exit(0)

    # Deploy ChromaDB
    if not deploy_chromadb():
        sys.exit(1)

    # Success
    print()
    print(f"{Colors.GREEN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.GREEN}  ✅ Setup complete!{Colors.RESET}")
    print(f"{Colors.GREEN}{'=' * 60}{Colors.RESET}")
    print()
    log_info("To access ChromaDB, run in a separate terminal:")
    print("    kubectl port-forward -n f1-agent svc/chromadb 8000:8000")
    print()
    log_info("ChromaDB will be at: http://localhost:8000")
    print()
    log_info("Useful commands:")
    print("    kubectl get pods -n f1-agent")
    print("    kubectl logs -f deployment/chromadb -n f1-agent")


if __name__ == "__main__":
    main()
