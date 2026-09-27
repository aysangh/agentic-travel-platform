from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from graph.state import TravelState


FLIGHT_AGENT_SYSTEM_PROMPT = """
You are a flight search agent.

You will receive a flight search task describing what the user needs.
Your only job is to search for flights and return the flight search result.

Rules:
- Use the available flight tools to complete the task.
- Do not ask follow-up questions unless a required tool parameter is genuinely
  missing and cannot be inferred from the task.
- Do not ask about preferences, budget, airlines, baggage, seating, or other
  optional information unless the tool explicitly requires it.
- Do not provide recommendations, opinions, explanations, or conversational
  commentary.
- Do not describe what you are going to do.
- Do not explain the tool calls.
- If the required information is available, call the tool immediately.
- Preserve the important information returned by the tool, especially flight
  options, dates, times, prices, airlines, and availability.
- Keep the final response concise. Prefer returning the tool result directly
  with minimal formatting.
- If the passenger numbers are not separated by passenger type, assume
  all specified passengers are adults.
- After obtaining the tool result, stop and return the result.
"""


def create_flight_agent(llm, flight_tools):

    agent = create_agent(
        model=llm,
        tools=flight_tools,
        system_prompt=FLIGHT_AGENT_SYSTEM_PROMPT,
        middleware=[
            ToolCallLimitMiddleware(
                run_limit=8,
                exit_behavior="end",
            )
                    
        ],
    )

    async def flight_agent(state: TravelState):

        task = state["flight_task"]

        if not task:
            return {
                "flight_results": None,
            }

        result = await agent.ainvoke({
            "messages": [
                {
                    "role": "user",
                    "content": task,
                }
            ]
        })

        flight_results = result["messages"][-1].content

        return {
            "flight_results": flight_results,
        }

    return flight_agent
