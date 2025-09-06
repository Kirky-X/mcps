"""MCP Server Module

Provides the MCPServer class for the DevAgent system.
This module serves as a compatibility layer for imports.
"""

from .mcp_protocol import MCPServer, MCPError

__all__ = ["MCPServer", "MCPError"]