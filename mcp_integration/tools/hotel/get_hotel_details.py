from fastmcp import FastMCP
from typing import Any

from mcp_integration.snapptrip.hotel.client import client
from mcp_integration.snapptrip.hotel.parser import parse_hotel_detail, shamsi_to_miladi


def register_get_hotel_details(mcp: FastMCP) -> None:
    @mcp.tool("get_hotel_details")
    async def get_hotel_details(
        hotel_id: int, 
        date_from: str, 
        date_to: str) -> dict[str, Any]:
        """Get room details and prices for a specific hotel.

        Args:
            hotel_id: Unique hotel identifier returned by ``search_hotels``.

            date_from: Check-in date in Shamsi format ``YYYY-MM-DD``,
                for example ``1405-05-25``.

            date_to: Check-out date in Shamsi format ``YYYY-MM-DD``,
                for example ``1405-05-28``.

        Returns:
            A dictionary containing a rooms list. Each room entry includes:

            - title: Room title.
            - num_adults: Maximum number of adults allowed.
            - num_available_rooms: Number of available rooms of this type.
            - description: Room description.
            - price: Total room price in Iranian Toman for the specified occupancy and stay dates.
            - num_extra_bed: Number of extra beds available.
            - extra_bed_price: Extra bed price in Iranian Toman.
            - breakfast_included: Whether breakfast is included.
            - has_full_board: Whether full board is available.
            - full_board_price: Full board price in Iranian Toman.

        Notes:
            - Use the ``hotel_id`` returned from ``search_hotels``.
            - Dates must be provided in Shamsi format: ``1405-05-25``.
        """
        date_from, date_to = shamsi_to_miladi(date_from), shamsi_to_miladi(date_to)
        response = await client.get_details(hotel_id, date_from, date_to)
        return parse_hotel_detail(response)
