import httpx 
from typing import Any

from .endpoints import Endpoints


HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.snapptrip.com/",
    "Origin": "https://www.snapptrip.com",
    "channel": "web",          
    "Content-Type": "application/json",
}

class SnapptripClient:
    def __init__(self, timeout: float = 60):
        self.client = httpx.AsyncClient(timeout=timeout, headers=HEADERS, follow_redirects=True)

    async def get(self, url: str, params: dict[str, Any] | None = None) -> dict:
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def search_city(self, city_name: str) -> dict:
        return await self.get(Endpoints.city(city_name))

    async def search_hotel(self, city_id: int, date_from: str, date_to: str, order_by: str) -> dict:
        return await self.get(
            Endpoints.hotel(city_id, date_from, date_to, order_by)
            )

    async def get_details(self, hotel_id: int, date_from: str, date_to: str) -> dict:
        return await self.get(
            Endpoints.room(hotel_id, date_from, date_to)
        )


client = SnapptripClient()