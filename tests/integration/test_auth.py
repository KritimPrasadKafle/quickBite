import pytest
from unittest.mock import patch, AsyncMock
# from tests.integration.conftest import REGISTER_PAYLOAD


# ─── Register ────────────────────────────────────────────────────────────────
# tests/integration/test_auth.py — add at the top, remove the import line
REGISTER_PAYLOAD = {
    "email": "kritim@quickbite.com",
    "phone": "9800000001",
    "full_name": "Kritim Test",
    "password": "Password123!",
    "role": "customer",
}


@pytest.mark.asyncio
async def test_register_201(client):
    resp = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == REGISTER_PAYLOAD["email"]


@pytest.mark.asyncio
async def test_register_duplicate_email_400(client):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    resp = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


# ─── Login ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_200(client):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    resp = await client.post("/api/v1/auth/login", json={
        "email": REGISTER_PAYLOAD["email"],
        "password": REGISTER_PAYLOAD["password"],
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]


@pytest.mark.asyncio
async def test_login_wrong_password_401(client):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    resp = await client.post("/api/v1/auth/login", json={
        "email": REGISTER_PAYLOAD["email"],
        "password": "WrongPassword!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_401(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "ghost@quickbite.com",
        "password": "anything",
    })
    assert resp.status_code == 401


# ─── /me ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_me_200(client, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == REGISTER_PAYLOAD["email"]


@pytest.mark.asyncio
async def test_get_me_no_token_401(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_garbage_token_401(client):
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


# ─── Logout ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_200(client, auth_headers):
    resp = await client.post("/api/v1/auth/logout", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_logout_blacklists_token(client, auth_headers):
    await client.post("/api/v1/auth/logout", headers=auth_headers)
    # same token must now be rejected
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 401


# ─── Refresh ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_issues_new_tokens(client, auth_tokens):
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": auth_tokens["refresh_token"]
    })
    assert resp.status_code == 200
    new = resp.json()["data"]
    assert new["access_token"] != auth_tokens["access_token"]
    assert new["refresh_token"] != auth_tokens["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_token_rotation_single_use(client, auth_tokens):
    """Each refresh token is single-use. Reusing it must fail."""
    old_token = auth_tokens["refresh_token"]
    await client.post("/api/v1/auth/refresh", json={"refresh_token": old_token})

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_token})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token_401(client):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
    assert resp.status_code == 401


# ─── Forgot password ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forgot_password_always_200(client):
    """Response must be identical whether or not the email exists."""
    with patch("modules.users.service.send_reset_email_task") as mock_task:
        mock_task.delay = lambda *a: None

        r1 = await client.post("/api/v1/auth/forgot-password",
                               json={"email": "ghost@quickbite.com"})
        await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        r2 = await client.post("/api/v1/auth/forgot-password",
                               json={"email": REGISTER_PAYLOAD["email"]})

    assert r1.status_code == 200
    assert r2.status_code == 200
    # response body must be identical — no info leak
    assert r1.json()["message"] == r2.json()["message"]


# ─── Reset password ──────────────────────────────────────────────────────────




@pytest.mark.asyncio
async def test_reset_password_end_to_end(client):
    """
    Full flow:
    register → forgot-password → capture token → reset-password
    → old password fails → new password works
    """
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    captured = {}
    with patch("modules.users.service.send_reset_email_task") as mock_task:
        mock_task.delay = lambda email, token: captured.update({"token": token})
        await client.post("/api/v1/auth/forgot-password",
                          json={"email": REGISTER_PAYLOAD["email"]})

    assert "token" in captured, "Token was not captured — task.delay not called"

    resp = await client.post("/api/v1/auth/reset-password", json={
        "token": captured["token"],
        "new_password": "NewPassword123!",
    })
    assert resp.status_code == 200

    # old password no longer works
    old_login = await client.post("/api/v1/auth/login", json={
        "email": REGISTER_PAYLOAD["email"],
        "password": REGISTER_PAYLOAD["password"],
    })
    assert old_login.status_code == 401

    # new password works
    new_login = await client.post("/api/v1/auth/login", json={
        "email": REGISTER_PAYLOAD["email"],
        "password": "NewPassword123!",
    })
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_single_use_token(client):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    captured = {}
    with patch("modules.users.service.send_reset_email_task") as mock_task:
        mock_task.delay = lambda email, token: captured.update({"token": token})
        await client.post("/api/v1/auth/forgot-password",
                          json={"email": REGISTER_PAYLOAD["email"]})

    payload = {"token": captured["token"], "new_password": "NewPassword123!"}

    first = await client.post("/api/v1/auth/reset-password", json=payload)
    assert first.status_code == 200

    second = await client.post("/api/v1/auth/reset-password", json=payload)
    assert second.status_code == 400  # token already consumed


@pytest.mark.asyncio
async def test_reset_password_bad_token_400(client):
    resp = await client.post("/api/v1/auth/reset-password", json={
        "token": "garbage",
        "new_password": "NewPass123!",
    })
    assert resp.status_code == 400