#!/usr/bin/env python
"""Run unit tests and save results to file."""
import subprocess
import sys

print("Running unit tests...")
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/unit", "-v", "--tb=short"],
    capture_output=True,
    text=True,
    timeout=180
)

with open("test_results.txt", "w") as f:
    f.write("=" * 60 + "\n")
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\n" + "=" * 60 + "\n")
    f.write("STDERR:\n")
    f.write(result.stderr)
    f.write("\n" + "=" * 60 + "\n")
    f.write(f"Return code: {result.returncode}\n")
    f.write("=" * 60 + "\n")

    if result.returncode == 0:
        f.write("ALL TESTS PASSED\n")
    else:
        f.write("SOME TESTS FAILED\n")

print("Done. Results saved to test_results.txt")
print(f"Return code: {result.returncode}")