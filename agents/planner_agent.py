from langchain_core.messages import HumanMessage

from graph.state import TravelState


PLANNER_SYSTEM_PROMPT = """
You are the final travel planner.

Answer the user's request directly using the provided flight and hotel
results. Use only the provided information. Never invent prices,
availability, or other details.

Calculate total costs when relevant:
- Flight cost for all travelers
- Hotel cost based on rooms, guests, and nights
- Total trip cost when both are relevant

Clearly distinguish per-person costs from total costs and state any
necessary assumptions.

Use Markdown tables when comparing multiple flights or hotels;

Keep the response concise, natural, and useful.

Only discuss the travel categories relevant to the user's request. If the
user asks only about flights, do not discuss hotels, and vice versa.

Do not mention missing or unavailable information unless it is explicitly relevant to the user's current request.
"""

PLANNER_USER_PROMPT = """
Current user request:
{current_request}

Flight results:
{flight_results}

Hotel results:
{hotel_results}

User preferences:
{user_preferences}

Supervisor Context:
{supervisor_context}
"""


def _last_human_message(messages) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def create_planner_agent(llm):
    async def planner_agent(state: TravelState):
        current_request = _last_human_message(state["messages"])

        user_prompt = PLANNER_USER_PROMPT.format(
            current_request=current_request,
            flight_results=state.get("flight_results"), 
            hotel_results=state.get("hotel_results"),
            supervisor_context=state.get("supervisor_context"),
            user_preferences=state["user_preferences"],
        )

        response = await llm.ainvoke([
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])

        return {
            "messages": [response],
        }

    return planner_agent
