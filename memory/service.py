import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from memory.embedding import EmbeddingService
from memory.repository import MemoryRepository


class MemoryService:

    def __init__(self, session: AsyncSession):
        self.repository = MemoryRepository(session)
        self.embedding_service = EmbeddingService()

    async def add_memory(
        self,
        user_id: uuid.UUID,
        content: str,
        memory_type: str,
        extra_data: dict | None = None,
    ):
        embedding = await self.embedding_service.embed(content)

        return await self.repository.create(
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            embedding=embedding,
            extra_data=extra_data,
        )

    async def search_memories(
        self,
        user_id: uuid.UUID,
        query: str,
        limit: int = 5,
    ):
        query_embedding = await self.embedding_service.embed(query)

        return await self.repository.search_similar(
            user_id=user_id,
            query_embedding=query_embedding,
            limit=limit,
            threshold=config.sim_threshold,
        )