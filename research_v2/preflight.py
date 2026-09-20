"""Local preflight checks before any Research V2 API experiment.

This script does not make model API calls.

Usage:
    python -m research_v2.preflight
    python -m research_v2.preflight --require-keys
"""

import argparse
import compileall
import os
import subprocess
import sys

from research_v2.validate_design import main as validate_design


def check_imports():
    missing = []

    try:
        import openai  # noqa: F401
    except ImportError:
        missing.append("openai")

    try:
        from google import genai  # noqa: F401
    except ImportError:
        missing.append("google-genai")

    try:
        import dotenv  # noqa: F401
    except ImportError:
        missing.append("python-dotenv")

    if missing:
        raise RuntimeError(
            "Missing runtime dependencies: "
            + ", ".join(missing)
            + ". Run: pip install -r requirements.txt"
        )


def check_keys(require_keys: bool):
    names = ["NVIDIA_API_KEY", "GEMINI_API_KEY"]
    present = {name: bool(os.getenv(name)) for name in names}

    print("API key presence:")
    for name in names:
        print(f"  {name}: {'configured' if present[name] else 'missing'}")

    if require_keys and not all(present.values()):
        raise RuntimeError(
            "Required API keys are not configured. Put them in a local .env "
            "file; never commit or paste the key values into the repository."
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-keys",
        action="store_true",
        help="Fail if NVIDIA_API_KEY or GEMINI_API_KEY is missing.",
    )
    args = parser.parse_args()

    print("[1/5] Compiling Research V2 source...")
    ok = compileall.compile_dir("research_v2", quiet=1)
    ok = compileall.compile_dir("tests", quiet=1) and ok
    if not ok:
        raise RuntimeError("Python compilation failed.")

    print("[2/5] Validating frozen dataset design...")
    validate_design()

    print("[3/5] Running dependency-free unit tests...")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_research_v2.py",
            "-v",
        ],
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("Unit tests failed.")

    print("[4/5] Checking runtime dependencies...")
    check_imports()

    print("[5/5] Checking API-key configuration...")
    check_keys(args.require_keys)

    print("Research V2 preflight passed.")
    print("No model API calls were made.")


if __name__ == "__main__":
    main()
