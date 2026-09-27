import pytest


@pytest.mark.asyncio
async def test_register_creates_user(client):
    response = await client.post("/auth/register", json={
        "email": "newuser@example.com",
        "password": "supersecret123",
    })
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(client):
    payload = {"email": "dupe@example.com", "password": "supersecret123"}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_login_correct_password(client):
    await client.post("/auth/register", json={
        "email": "login-test@example.com",
        "password": "correct-password",
    })

    response = await client.post("/auth/login", json={
        "email": "login-test@example.com",
        "password": "correct-password",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_incorrect_password(client):
    await client.post("/auth/register", json={
        "email": "wrongpass-test@example.com",
        "password": "correct-password",
    })

    response = await client.post("/auth/login", json={
        "email": "wrongpass-test@example.com",
        "password": "wrong-password",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_authentication(client):
    response = await client.get("/auth/me")
    assert response.status_code in (401, 403)  # 403 if using HTTPBearer's default


@pytest.mark.asyncio
async def test_me_returns_current_user(client, auth_headers, test_user):
    response = await client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(test_user.id)
