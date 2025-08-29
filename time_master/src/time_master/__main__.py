#!/usr/bin/env python3
"""
TimeMaster CLI entry point for module execution.

This module allows TimeMaster to be executed as:
    python -m timemaster
    uv run -m timemaster
"""

from time_master.cli import main

if __name__ == "__main__":
    main()