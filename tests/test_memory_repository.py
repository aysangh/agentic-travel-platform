import uuid
import pytest

from memory.repository import MemoryRepository


FAKE_DIM = 1536

def fake_embedding(seed: float) -> list[float]:
    """Deterministic fake vector — avoids real OpenAI calls in repository tests."""
    return [seed] * FAKE_DIM


@pytest.mark.asyncio
async def test_get_by_id_found_and_missing(db_session, test_user):
    repo = MemoryRepository(db_session)

    memory = await repo.create(
        user_id=test_user.id,
        content="Prefers budget hotels.",
        memory_type="preference",
        embedding=fake_embedding(0.1),
    )

    found = await repo.get_by_id(memory.id)
    assert found is not None
    assert found.content == "Prefers budget hotels."

    missing = await repo.get_by_id(uuid.uuid4())
    assert missing is None


@pytest.mark.asyncio
async def test_get_by_user_scoped_correctly(db_session, test_user):
    repo = MemoryRepository(db_session)

    await repo.create(
        user_id=test_user.id,
        content="Prefers window seats.",
        memory_type="preference",
        embedding=fake_embedding(0.2),
    )

    results = await repo.get_by_user(test_user.id)
    assert len(results) == 1
    assert results[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_search_similar_ordering_and_limit(db_session, test_user):
    repo = MemoryRepository(db_session)

    # Embeddings deliberately at increasing distance from the query vector.
    await repo.create(test_user.id, "closest", "preference", fake_embedding(1.0))
    await repo.create(test_user.id, "middle", "preference", fake_embedding(0.5))
    await repo.create(test_user.id, "farthest", "preference", fake_embedding(-1.0))

    results = await repo.search_similar(
        user_id=test_user.id,
        query_embedding=fake_embedding(1.0),
        limit=2,
    )

    assert len(results) == 2
    # Results are ordered by similarity descending.
    assert results[0][1] >= results[1][1]
    assert results[0][0].content == "closest"
