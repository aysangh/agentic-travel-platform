import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Memory


class MemoryRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        content: str,
        memory_type: str,
        embedding: list[float] | None = None,
        extra_data: dict | None = None,
    ) -> Memory:

        memory = Memory(
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            embedding=embedding,
            extra_data=extra_data,
        )

        self.session.add(memory)

        await self.session.commit()
        await self.session.refresh(memory)

        return memory

    async def get_by_id(
        self,
        memory_id: uuid.UUID,
    ) -> Memory | None:

        result = await self.session.execute(
            select(Memory)
            .where(Memory.id == memory_id)
        )

        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
    ) -> list[Memory]:

        result = await self.session.execute(
            select(Memory)
            .where(Memory.user_id == user_id)
            .order_by(Memory.created_at.desc())
        )

        return list(result.scalars().all())

    async def search_similar(
        self,
        user_id: uuid.UUID,
        query_embedding: list[float],
        limit: int = 5,
        threshold: float | None = None,
    ) -> list[tuple[Memory, float]]:

        distance = Memory.embedding.cosine_distance(
            query_embedding
        ).label("distance")

        result = await self.session.execute(
            select(Memory, distance)
            .where(
                Memory.user_id == user_id,
                Memory.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(limit)
        )

        results = [
            (memory, 1 - distance_value)
            for memory, distance_value in result.all()
        ]

        if threshold is not None:
            results = [
                (memory, similarity)
                for memory, similarity in results
                if similarity >= threshold
            ]

        return results