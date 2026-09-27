import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.models import User
from app.main import app


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/trv_test",
)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """
    Create a fresh async engine and database session for each test.

    The engine is created inside the test's event loop so asyncpg
    connections are never shared across different event loops.
    """
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    try:
        async with AsyncSession(
            bind=test_engine,
            expire_on_commit=False,
        ) as session:
            yield session
    finally:
        await test_engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email=f"test-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("correct-password"),
    )

    db_session.add(user)

    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
def auth_headers(test_user: User):
    token = create_access_token(test_user.id)

    return {
        "Authorization": f"Bearer {token}",
    }