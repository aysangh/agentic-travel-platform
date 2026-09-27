from fastmcp import FastMCP

from mcp_integration.snapptrip.flight.playwright_client import execute_flight_search


def register_search_flights(mcp: FastMCP):

    @mcp.tool("search_flights")
    async def search_flights(
        origin: str,
        destination: str,
        departure_day: int,
        return_day: int,
        departure_month: str,
        return_month: str,
        adults: int,
        children: int = 0,
        infants: int = 0,
    ):
        """
        Search for round-trip flights between two destinations on Snapptrip.

        Args:
            origin: Departure city in Persian.
            destination: Arrival city in Persian.
            departure_day: Departure day of the month.
            return_day: Return day of the month.
            departure_month: Departure month in Persian, e.g. "مرداد".
            return_month: Return month in Persian, e.g. "مرداد".
            adults: Number of adult passengers.
            children: Number of child passengers.
            infants: Number of infant passengers.

        Note: If the user does not specify passenger types or counts,
        assume all passengers are adults.

        Example:
            Search for a round-trip flight from Tehran to Mashhad
            departing on 25 Mordad and returning on 26 Mordad,
            for 2 adults and 1 child:

            origin="تهران"
            destination="مشهد"
            departure_day=25
            return_day=26
            departure_month="مرداد"
            return_month="مرداد"
            adults=2
            children=1
            infants=0
        """
        results = await execute_flight_search(
            origin=origin,
            destination=destination,
            departure_day=departure_day,
            return_day=return_day,
            departure_month=departure_month,
            return_month=return_month,
            adults=adults,
            children=children,
            infants=infants,
        )

        return results