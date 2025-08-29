import asyncio
import json
import logging
from typing import List
import pytz

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .core import TimeMaster

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize TimeMaster
timemaster = TimeMaster()
logger.info(f"TimeMaster initialized, online mode: {timemaster._is_online}")

# Create MCP server
server = Server("TimeMaster")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_time",
            description="Unified time interface - get current time or convert existing time between timezones",
            inputSchema={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Target timezone (default: local timezone)"
                    },
                    "time_str": {
                        "type": "string",
                        "description": "Time string to convert (if not provided, gets current time)"
                    },
                    "from_tz": {
                        "type": "string",
                        "description": "Source timezone for conversion (required if time_str is provided)"
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'iso' or 'friendly_cn' (default: 'iso')",
                        "default": "iso"
                    }
                }
            }
        ),

        Tool(
            name="get_local_timezone",
            description="Get the local system timezone",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="search_timezones",
            description="Search for timezones matching a query. Use empty string to list all timezones.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for timezone names (empty string returns all timezones)",
                        "default": ""
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 20)",
                        "default": 20
                    }
                }
            }
        ),


        Tool(
            name="calculate_time_difference",
            description="Calculate the time difference between two times in different timezones",
            inputSchema={
                "type": "object",
                "properties": {
                    "time1": {
                        "type": "string",
                        "description": "First time string"
                    },
                    "tz1": {
                        "type": "string",
                        "description": "Timezone for first time"
                    },
                    "time2": {
                        "type": "string",
                        "description": "Second time string"
                    },
                    "tz2": {
                        "type": "string",
                        "description": "Timezone for second time"
                    }
                },
                "required": ["time1", "tz1", "time2", "tz2"]
            }
        ),


        Tool(
            name="search_holiday",
            description="Search for holidays by name. Returns holiday date and days until. If query is empty, returns next upcoming holiday.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for holiday names (empty string returns next holiday)",
                        "default": ""
                    },
                    "country": {
                        "type": "string",
                        "description": "ISO country code (e.g., 'US', 'GB', 'FR')",
                        "default": ""
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone to infer country from (e.g., 'America/New_York')",
                        "default": ""
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year (default: current year)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="list_holidays",
            description="List all holidays for a specific country and year",
            inputSchema={
                "type": "object",
                "properties": {
                    "country": {
                        "type": "string",
                        "description": "ISO country code (e.g., 'US', 'GB', 'FR')",
                        "default": ""
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone to infer country from (e.g., 'America/New_York')",
                        "default": ""
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year (default: current year)"
                    }
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "get_time":
            timezone = arguments.get("timezone")
            time_str = arguments.get("time_str")
            from_tz = arguments.get("from_tz")
            format_type = arguments.get("format", "iso")
            
            result = timemaster.get_time(
                timezone=timezone,
                time_str=time_str,
                from_tz=from_tz,
                format=format_type
            )
            
            if time_str:
                actual_timezone = timezone if timezone else timemaster.get_local_timezone()
                return [TextContent(type="text", text=f"Converted time: {result} ({actual_timezone})")]
            else:
                actual_timezone = timezone if timezone else timemaster.get_local_timezone()
                return [TextContent(type="text", text=f"Current time in {actual_timezone}: {result}")]
        

        
        elif name == "get_local_timezone":
            local_tz = timemaster.get_local_timezone()
            return [TextContent(type="text", text=f"Local timezone: {local_tz}")]
        
        elif name == "search_timezones":
            query = arguments.get("query", "")
            limit = arguments.get("limit", 20)
            matches = timemaster.find_timezones(query, limit=limit)
            if matches:
                result = "\n".join([f"- {tz}" for tz in matches])
                if query:
                    return [TextContent(type="text", text=f"Matching timezones for '{query}':\n{result}")]
                else:
                    total_count = len(list(pytz.all_timezones))
                    suffix = f"\n... and {total_count - len(matches)} more" if len(matches) < total_count else ""
                    return [TextContent(type="text", text=f"All timezones (showing {len(matches)}):\n{result}{suffix}")]
            else:
                return [TextContent(type="text", text=f"No timezones found matching '{query}'")]
        

        

        
        elif name == "calculate_time_difference":
            tz1 = arguments["tz1"]
            tz2 = arguments["tz2"]
            diff = timemaster.difference(tz1, tz2)
            return [TextContent(type="text", text=f"Time difference between {tz1} and {tz2}: {diff}")]
        

        

        
        elif name == "search_holiday":
            query = arguments.get("query", "")
            country = arguments.get("country", "")
            timezone = arguments.get("timezone", "")
            year = arguments.get("year")
            limit = arguments.get("limit", 10)
            
            result = timemaster.search_holiday(
                query=query,
                country=country if country else None,
                timezone=timezone if timezone else None,
                year=year,
                limit=limit
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "list_holidays":
            country = arguments.get("country", "")
            timezone = arguments.get("timezone", "")
            year = arguments.get("year")
            
            result = timemaster.list_holidays(
                country=country if country else None,
                timezone=timezone if timezone else None,
                year=year
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing tool '{name}': {str(e)}")]

async def main():
    """Main entry point for the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

def async_main():
    """Async main entry point for script execution."""
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())