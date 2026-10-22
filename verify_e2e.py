"""Compatibility entry point: credentials are prompted; tokens/URLs are never printed.

Supply --api-url, --client-id and --username. No live calls occur on import.
"""
from scripts.check_live import main

if __name__ == "__main__":
    raise SystemExit(main(default_mode="documents"))
