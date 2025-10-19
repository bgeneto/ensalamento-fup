#!/usr/bin/env python3
"""
Test runner script for Phase 1 tests.
Runs all tests and generates coverage report.
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_tests():
    """Run all tests with coverage."""
    print("=" * 80)
    print("🧪 PHASE 1 TEST SUITE")
    print("=" * 80)

    # Install test dependencies
    print("\n📦 Installing test dependencies...")
    subprocess.run(["pip", "install", "-q", "pytest", "pytest-cov"], check=False)

    # Run tests with coverage
    print("\n🏃 Running tests...\n")
    result = subprocess.run(
        [
            "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
        ],
        cwd=PROJECT_ROOT,
    )

    if result.returncode == 0:
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print("\n📊 Coverage report generated in: htmlcov/index.html")
    else:
        print("\n" + "=" * 80)
        print("❌ SOME TESTS FAILED")
        print("=" * 80)

    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
