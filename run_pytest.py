import sys
import pytest

# Run tests and capture results
exit_code = pytest.main([
    "tests/unit",
    "-v",
    "--tb=short",
    "-x"
])

print(f"\nExit code: {exit_code}")
sys.exit(exit_code)