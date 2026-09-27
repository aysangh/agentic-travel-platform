import pytest


@pytest.mark.asyncio
async def test_create_and_list_conversations(client, auth_headers):
    create_resp = await client.post("/conversations", headers=auth_headers)
    assert create_resp.status_code == 201
    conversation_id = create_resp.json()["id"]

    list_resp = await client.get("/conversations", headers=auth_headers)
    assert list_resp.status_code == 200
    ids = [c["id"] for c in list_resp.json()]
    assert conversation_id in ids


@pytest.mark.asyncio
async def test_get_conversation_detail(client, auth_headers):
    create_resp = await client.post("/conversations", headers=auth_headers)
    conversation_id = create_resp.json()["id"]

    detail_resp = await client.get(f"/conversations/{conversation_id}", headers=auth_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == conversation_id
    assert detail_resp.json()["messages"] == []


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_conversation(
    client, auth_headers, db_session
):
    import uuid
    from app.db.models import User
    from app.core.security import hash_password, create_access_token

    other_user = User(
        email=f"other-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    other_headers = {"Authorization": f"Bearer {create_access_token(other_user.id)}"}

    create_resp = await client.post("/conversations", headers=other_headers)
    conversation_id = create_resp.json()["id"]

    # Original test_user tries to access other_user's conversation.
    response = await client.get(f"/conversations/{conversation_id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation_cascades_messages(client, auth_headers, db_session):
    from sqlalchemy import select
    from app.db.models import Message, Conversation

    create_resp = await client.post("/conversations", headers=auth_headers)
    conversation_id = create_resp.json()["id"]

    message = Message(
        conversation_id=conversation_id,
        role="user",
        content="test message",
    )
    db_session.add(message)
    await db_session.commit()

    delete_resp = await client.delete(f"/conversations/{conversation_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    result = await db_session.execute(
        select(Message).where(Message.conversation_id == conversation_id)
    )
    assert result.scalar_one_or_none() is None

    result = await db_session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    assert result.scalar_one_or_none() is None
