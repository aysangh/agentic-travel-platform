import jdatetime
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage

from graph.state import TravelState


CURRENT_SHAMSI_YEAR = jdatetime.date.today().year

SUPERVISOR_SYSTEM_PROMPT = f"""
You are the supervisor of a travel-planning assistant.

Your job is to decide what should happen for the CURRENT user message.

You have access to the current conversation state, including previous
conversation messages, previous flight/hotel search results,
recommendations, and the user's relevant long-term preferences.

For every current user message, decide whether:

No new search is needed → use direct_response.
A new flight search is needed → populate flight_task.
A new hotel search is needed → populate hotel_task.
Both new flight and hotel searches are needed → populate BOTH tasks.

Use direct_response when the current request can be answered using
information already available in the conversation state, including
previous search results and recommendations.

Also use direct_response for:

Casual conversation
Greetings
Thanks
Questions about your capabilities
Questions that only require comparing, filtering, or explaining
information already available

A new search may be required because of:

A new destination
New or changed travel dates
A new route
A changed budget
A changed number of passengers
Any other requirement that cannot be satisfied using existing results

Populate ONLY the tasks that actually require a new search.

FLIGHT TASK

Essential information:

origin (city)
destination (city)
departure_day
return_day
departure_month
return_month
passengers

A flight_task must NOT be created if any essential flight parameter is
missing.

Essential information:

city_name
date_from
date_to

A hotel_task must NOT be created if any essential hotel parameter is
missing.

Current Shamsi year: {CURRENT_SHAMSI_YEAR}

If the user provides a date without a year, assume the current shamsi year 
from the current year above.

If essential information is missing for a required new search:

Do NOT guess.
Do NOT populate the corresponding task.
Use direct_response to ask the user for the missing information.

Flight and hotel tasks are independent. For the same user message, you
may create:

flight_task only
hotel_task only
both flight_task and hotel_task
neither task

When creating a flight_task and/or hotel_task, provide relevant context from the conversation history and current state that may help the Planner;
otherwise, set supervisor_context to None.

Your task is to ROUTE and SPECIFY the work.
"""


class TravelTasks(BaseModel):

    flight_task: str | None = Field(
        default=None,
        description="Task for a new flight search, if required."
    )

    hotel_task: str | None = Field(
        default=None,
        description="Task for a new hotel search, if required."
    )

    supervisor_context: str | None = Field(
        default=None,
        description="Relevant context from the conversation history and current state for the Planner, if a flight or hotel task is created."
    )
    
    direct_response: str | None = Field(
        default=None,
        description="Direct response to the user when no new search is needed."
    )


def create_supervisor_agent(llm):

    supervisor_llm = llm.with_structured_output(TravelTasks)

    async def supervisor_agent(state: TravelState):

        messages = [
            {
                "role": "system",
                "content": SUPERVISOR_SYSTEM_PROMPT,
            },
            {
                "role": "system",
                "content": f"User preferences:\n{state['user_preferences']}",
            },
            *state["messages"],
        ]

        result = await supervisor_llm.ainvoke(messages)

        return {
            "flight_task": result.flight_task,
            "hotel_task": result.hotel_task,
            "supervisor_context": result.supervisor_context,
            "response": result.direct_response,
        }

    return supervisor_agent


async def direct_response_node(state: TravelState):

    response = AIMessage(
        content=state["response"]
    )

    return {
        "messages": [response]
    }
