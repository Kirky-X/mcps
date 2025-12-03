#!/usr/bin/env python3
"""MCP服务启动入口点"""

import os
import sys

def main() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from library.main import main as run_main
    run_main()

if __name__ == "__main__":
    main()
