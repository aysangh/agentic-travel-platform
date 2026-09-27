import uuid

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from memory.service import MemoryService


class ExtractedPreference(BaseModel):
    content: str = Field(
        description="A single, self-contained user preference or fact, "
        "written so it makes sense without conversation context. "
        "E.g. 'Prefers window seats on long-haul flights.'"
    )
    memory_type: str = Field(
        description="One of: flight_preference, hotel_preference, "
        "budget_preference, general_preference, personal_fact"
    )


class ExtractedPreferences(BaseModel):
    preferences: list[ExtractedPreference] = Field(
        default_factory=list,
        description="Durable user preferences worth remembering long-term. "
        "Empty list if nothing new and durable was mentioned this turn.",
    )


EXTRACTION_SYSTEM_PROMPT = """
You extract durable, long-term user preferences 
from a travel-planning conversation turn.

Only extract things that will still be true and useful in future 
conversations (e.g. "always flies economy", "prefers boutique hotels over chains", 
"travels with a toddler"). 

Do NOT extract one-off details specific to this single trip request only 
(e.g. a specific destination city or specific travel dates for this one 
search), unless the user frames it as a standing preference.

If nothing durable was mentioned, return an empty list.
"""


class LongTermMemory:

    SIMILARITY_DEDUPE_THRESHOLD = 0.92

    def __init__(self, session: AsyncSession, llm):
        self.session = session
        self.service = MemoryService(session)
        self.llm = llm

    async def get(
        self,
        user_id: uuid.UUID,
        query: str | None = None,
        limit: int = 8,
    ) -> list[str]:
        """
        Fetch preferences to inject into the Supervisor prompt.
        If `query` (the latest user message) is given, does a
        semantic search so the most *relevant* preferences surface first.
        Otherwise returns the most recent memories.
        """
        if query:
            results = await self.service.search_memories(
                user_id=user_id,
                query=query,
                limit=limit,
            )
            return [memory.content for memory, _score in results]

        memories = await self.service.repository.get_by_user(user_id)
        return [memory.content for memory in memories[:limit]]

    async def extract_and_store(
        self,
        user_id: uuid.UUID,
        user_message: str,
        assistant_response: str,
    ) -> list[str]:
        """
        Call after a turn completes. Extracts durable preferences via LLM
        and stores any that aren't near-duplicates of existing memories.
        Returns the list of newly stored memory contents.
        """
        extractor = self.llm.with_structured_output(ExtractedPreferences)

        result = await extractor.ainvoke(
            [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"User: {user_message}\n"
                        f"Assistant: {assistant_response}"
                    ),
                },
            ]
        )

        stored: list[str] = []

        for pref in result.preferences:
            is_duplicate = await self._is_duplicate(user_id, pref.content)
            if is_duplicate:
                continue

            await self.service.add_memory(
                user_id=user_id,
                content=pref.content,
                memory_type=pref.memory_type,
            )
            stored.append(pref.content)

        return stored

    async def _is_duplicate(self, user_id: uuid.UUID, content: str) -> bool:
        similar = await self.service.search_memories(
            user_id=user_id,
            query=content,
            limit=1,
        )
        if not similar:
            return False

        _memory, score = similar[0]
        return score >= self.SIMILARITY_DEDUPE_THRESHOLD
