from fastmcp import FastMCP
from mcp_integration.tools.hotel.get_hotel_details import register_get_hotel_details
from mcp_integration.tools.hotel.search_hotels import register_search_hotels
from mcp_integration.tools.flight.search_flights import register_search_flights

def register_all_tools(mcp: FastMCP) -> None:
    register_search_hotels(mcp)
    register_get_hotel_details(mcp)
    register_search_flights(mcp)
