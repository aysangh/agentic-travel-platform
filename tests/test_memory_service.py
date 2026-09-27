import pytest

from memory.service import MemoryService


@pytest.mark.asyncio
async def test_add_memory_embeds_and_stores(db_session, test_user, monkeypatch):
    service = MemoryService(db_session)

    async def fake_embed(text: str):
        return [0.42] * 1536

    monkeypatch.setattr(service.embedding_service, "embed", fake_embed)

    memory = await service.add_memory(
        user_id=test_user.id,
        content="Prefers aisle seats.",
        memory_type="preference",
    )

    assert memory.content == "Prefers aisle seats."
    assert memory.embedding == [0.42] * 1536


@pytest.mark.asyncio
async def test_search_memories_scoped_to_user(db_session, test_user, monkeypatch):
    service = MemoryService(db_session)

    async def fake_embed(text: str):
        return [0.1] * 1536

    monkeypatch.setattr(service.embedding_service, "embed", fake_embed)

    await service.add_memory(test_user.id, "Prefers boutique hotels.", "preference")

    results = await service.search_memories(
        user_id=test_user.id,
        query="hotel preferences",
        limit=5,
    )

    assert len(results) == 1
    assert results[0][0].user_id == test_user.id
