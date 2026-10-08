"""Run the same release checks locally and in GitHub Actions."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "AGENTS.md",
    "Dockerfile.render",
    "render.yaml",
    ".env.example",
    "requirements.txt",
    "frontend/package.json",
)


def run(label: str, command: list[str]) -> None:
    print(f"\n==> {label}")
    subprocess.run(command, cwd=ROOT, check=True)


def fail(message: str) -> None:
    print(f"PREFLIGHT FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    if missing:
        fail(f"missing required production files: {', '.join(missing)}")

    tracked_env = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".env"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if tracked_env.returncode == 0:
        fail(".env is tracked by Git")

    if not os.getenv("DATABASE_URL") and not (ROOT / ".env").is_file():
        fail("DATABASE_URL is required to run integration tests")

    run("Python compile", [sys.executable, "-m", "compileall", "-q", "app"])
    run("Create test tables", [sys.executable, "-m", "app.create_tables"])
    run("Python tests", [sys.executable, "-m", "pytest", "-q", "tests"])
    run("Frontend clean install", ["npm", "ci", "--prefix", "frontend"])
    run("Frontend production build", ["npm", "run", "build", "--prefix", "frontend"])

    if shutil.which("docker") is None:
        fail("Docker is required to verify Dockerfile.render")
    run(
        "Production Docker build",
        ["docker", "build", "-f", "Dockerfile.render", "-t", "ai-saas-preflight", "."],
    )
    print("\nPREFLIGHT PASSED")


if __name__ == "__main__":
    main()
