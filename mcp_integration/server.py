from fastmcp import FastMCP

from config import config
from mcp_integration.tools import register_all_tools


INSTRUCTION = """
Travel MCP provides tools for travel planning.

Hotel workflow:
1. Call `search_hotels` first to find available hotels for the requested city and dates.
2. `search_hotels` returns hotel IDs for the available hotels.
3. Never call `get_hotel_details` tool before `search_hotels`.
"""

mcp = FastMCP(
    name="Travel MCP",
    instructions=INSTRUCTION,
)

register_all_tools(mcp)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=config.mcp_host,
        port=config.mcp_port,
    )