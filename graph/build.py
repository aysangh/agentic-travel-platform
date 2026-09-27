from contextlib import asynccontextmanager

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph, START, END

from config import config
from .state import TravelState
from mcp_integration.client import mcp_client

from agents import (
    create_planner_agent,
    create_supervisor_agent,
    create_flight_agent,
    create_hotel_agent,
    direct_response_node,
)


# ==================================================
# LLM
# ==================================================

llm = ChatOpenAI(
    model=config.model_name,
    api_key=config.openai_api_key,
    max_retries=2,
    timeout=60,
    streaming=True,
    stream_usage=True,
    reasoning_effort=None,
)


# ==================================================
# Routing
# ==================================================

def route_after_supervisor(state: TravelState):
    destinations = []

    if state.get("flight_task"):
        destinations.append("Flight")

    if state.get("hotel_task"):
        destinations.append("Hotel")

    return destinations or "DirectResponse"


# ==================================================
# Build graph
# ==================================================

@asynccontextmanager
async def build_travel_graph():

    # --------------------------------------------------
    # PostgreSQL checkpointer
    # --------------------------------------------------

    async with AsyncPostgresSaver.from_conn_string(
        config.langgraph_database_url
    ) as checkpointer:

        # Create LangGraph checkpoint tables if needed
        await checkpointer.setup()

        # --------------------------------------------------
        # MCP tools
        # --------------------------------------------------

        tools = await mcp_client.get_tools()

        flight_tools = [
            tool
            for tool in tools
            if tool.name == "search_flights"
        ]

        hotel_tools = [
            tool
            for tool in tools
            if tool.name in {
                "search_hotels",
                "get_hotel_details",
            }
        ]

        # --------------------------------------------------
        # Agents
        # --------------------------------------------------

        flight_agent = create_flight_agent(
            llm,
            flight_tools,
        )

        hotel_agent = create_hotel_agent(
            llm,
            hotel_tools,
        )

        planner_agent = create_planner_agent(
            llm
        )

        supervisor_agent = create_supervisor_agent(
            llm
        )

        # --------------------------------------------------
        # Graph
        # --------------------------------------------------

        workflow = StateGraph(TravelState)

        workflow.add_node("Supervisor", supervisor_agent)
        workflow.add_node("Flight", flight_agent)
        workflow.add_node("Hotel", hotel_agent)
        workflow.add_node("Planner", planner_agent)
        workflow.add_node("DirectResponse", direct_response_node)

        workflow.add_edge(START, "Supervisor")

        workflow.add_conditional_edges(
                "Supervisor",
                route_after_supervisor,
                {
                    "Flight": "Flight",
                    "Hotel": "Hotel",
                    "DirectResponse": "DirectResponse",
                },
            )

        workflow.add_edge("Flight", "Planner")
        workflow.add_edge("Hotel", "Planner")
        workflow.add_edge("Planner", END)
        workflow.add_edge("DirectResponse", END)
        
        # --------------------------------------------------
        # Compile 
        # --------------------------------------------------

        graph = workflow.compile(
            checkpointer=checkpointer,
        )

        yield graph