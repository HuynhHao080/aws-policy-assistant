#!/usr/bin/env python
"""Run unit tests and capture results."""
import subprocess
import sys

print("Running unit tests...")
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/unit", "-v", "--tb=short"],
    capture_output=True,
    text=True,
    timeout=180
)

print("=" * 60)
print("STDOUT:")
print(result.stdout)
print("=" * 60)
print("STDERR:")
print(result.stderr)
print("=" * 60)
print(f"Return code: {result.returncode}")
print("=" * 60)

if result.returncode == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")