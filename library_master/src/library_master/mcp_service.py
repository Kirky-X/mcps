#!/usr/bin/env python3
"""MCP服务启动入口点"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    from library_master.main import main
    main()