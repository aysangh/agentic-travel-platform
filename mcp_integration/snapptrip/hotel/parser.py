import jdatetime
from typing import Any


def shamsi_to_miladi(shamsi_date: str) -> str:
    # input format: YYYY-MM-DD
    y, m, d = map(int, shamsi_date.split("-"))
    jalali = jdatetime.date(y, m, d)
    gregorian = jalali.togregorian()
    return gregorian.isoformat()


def parse_hotel_search(data: list[dict[str, Any]]) -> dict[str, Any]:
    hotels = []
    for hotel in data:
        available = str(hotel.get("is_available", "")).lower()
        if available == "true":
            hotels.append({
                "hotel_name": hotel.get("title"),
                "hotel_id": hotel.get("id"),
                "stars": hotel.get("stars"),
                "address": hotel.get("address"),
                "review": hotel.get("reviews", {}).get("ptp_ratings")
            })

    return {"hotels": hotels}

def parse_hotel_detail(response: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    rooms = []
    for room in response:
        rooms.append(
            {
                "title": room.get("title"),
                "num_adults": room.get("adults"),
                "num_available_rooms": room.get("available_rooms"),
                "description": room.get("description"),
                "price": room.get("prices", {}).get("local_price"),
                "num_extra_bed": room.get("extra_bed"),
                "extra_bed_price": room.get("prices", {}).get("extra_bed_price"),
                "breakfast_included": room.get("breakfast_included"),
                "has_full_board": room.get("prices", {}).get("has_full_board"),
                "full_board_price": room.get("prices", {}).get("full_board_price"),
                }
        )
    return {"rooms": rooms}
