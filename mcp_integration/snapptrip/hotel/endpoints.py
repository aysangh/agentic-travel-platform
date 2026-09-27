class Endpoints:
    BASE = "https://hapi.snapptrip.com"
    SEARCH = f"{BASE}/hotel/api/v2/"

    @staticmethod
    def city(city_name: str) -> str:
        return f"{Endpoints.SEARCH}search-text?text={city_name}&token=Jek&provider=flightio"

    @staticmethod
    def hotel(city_id: int, date_from: str, date_to: str, order_by: str) -> str:
        return f"{Endpoints.SEARCH}search-city?city_id={city_id}&date_from={date_from}&date_to={date_to}&page=1&order_by={order_by}&token=Jek&no_rooms=1"

    @staticmethod
    def room(hotel_id: int, date_from: str, date_to: str) -> str:
       return f"{Endpoints.SEARCH}hotels/{hotel_id}/rooms?date_from={date_from}&date_to={date_to}&token=Jek"
