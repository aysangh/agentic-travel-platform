from fastmcp import FastMCP
from typing import Any

from mcp_integration.snapptrip.hotel.client import client
from mcp_integration.snapptrip.hotel.parser import parse_hotel_search, shamsi_to_miladi


def register_search_hotels(mcp: FastMCP) -> None:
    @mcp.tool(
        name="search_hotels"
    )
    async def search_hotels(
        city_name: str, 
        date_from: str, 
        date_to: str, 
    ) -> dict[str, Any]:
        """Search available hotels in an Iranian city for a given date range.

        This tool resolves the city name to a city ID and returns available hotels
        for the requested stay dates.

        Args:
            city_name: Name of the destination city in Persian, for example
                "رشت", "تهران", or "اصفهان".

            date_from: Check-in date in Shamsi format ``YYYY-MM-DD``,
                for example ``1405-05-25``.

            date_to: Check-out date in Shamsi format ``YYYY-MM-DD``,
                for example ``1405-05-28``.

        Returns:
            A dictionary containing available hotels with their names, hotel IDs,
            addresses, star ratings, and review information.

        Notes:
            - Dates must be provided in Shamsi format: ``1405-05-25``.
            - If the user provides a date without a year, assume the year is
              ``1405``.
            - Hotels are returned in the platform's default selling/popularity order.
            - Only hotels marked as available are returned.
        """
        # Get city_id by city_name
        city_name = city_name.strip()
        response = await client.search_city(city_name)
        city_id = response.get("data", {})[0].get("id")
        if not isinstance(city_id, int) or city_id<=0:
            raise ValueError(
                f"city_id must be positive integer, got {city_id!r}"
                )
        
        # Get hotels
        date_from, date_to = shamsi_to_miladi(date_from), shamsi_to_miladi(date_to)
        response = await client.search_hotel(city_id, date_from, date_to, order_by="selling")

        data = response.get("data", {})
        return parse_hotel_search(data)
    