from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware

from graph.state import TravelState


HOTEL_AGENT_SYSTEM_PROMPT = f"""
You are a hotel search agent.

You will receive a hotel search task describing what the user needs.
Your only job is to search for hotels and return hotel search results.

Rules:
- Use the available hotel tools to complete the task.
- Always call `search_hotels` first when a hotel search is requested.
- If detailed room or pricing information is needed for a specific hotel,
  call `get_hotel_details` using a `hotel_id` returned by `search_hotels`.
- Never call `get_hotel_details` with an invented or unknown hotel ID.
- Do not ask follow-up questions unless a required tool parameter is genuinely
  missing and cannot be inferred from the task.
- Do not ask about optional preferences or businesses/services that are not
  required to complete the task.
- Do not provide recommendations, opinions, explanations, or conversational
  commentary.
- Do not describe what you are going to do.
- Do not explain the tool calls.
- Do not invent or guess missing required values.
- If the required information is available, call the tool immediately.
- After obtaining the tool result, stop and return the result.
- Keep the final response concise. Prefer returning the tool result directly
  with minimal formatting.
"""


def create_hotel_agent(llm, hotel_tools):

    agent = create_agent(
        model=llm,
        tools=hotel_tools,
        system_prompt=HOTEL_AGENT_SYSTEM_PROMPT,
        middleware=[
            ToolCallLimitMiddleware(
                run_limit=8,
                exit_behavior="end",
            )
                    
        ],
    )

    async def hotel_agent(state: TravelState):

        task = state["hotel_task"]

        if not task:
            return {
                "hotel_results": None,
            }

        result = await agent.ainvoke({
            "messages": [
                {
                    "role": "user",
                    "content": task,
                }
            ]
        })

        hotel_results = result["messages"][-1].content

        return {
            "hotel_results": hotel_results,
        }

    return hotel_agent
