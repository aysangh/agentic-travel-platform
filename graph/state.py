from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class TravelState(TypedDict):
    messages: Annotated[list, add_messages]

    flight_task: str | None
    hotel_task: str | None

    supervisor_context: str | None

    flight_results: dict | None
    hotel_results: dict | None

    response: str | None

    user_preferences: list | None
