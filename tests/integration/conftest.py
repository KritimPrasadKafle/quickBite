# tests/integration/conftest.py

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# ── imports without app. prefix ───────────────────────────────────────────────
from core.database import Base
from core.unit_of_work import UnitOfWork
from core.dependencies import get_uow
from main import app   # main.py lives inside app/, which is already in sys.path

TEST_DB_URL = "postgresql+asyncpg://quickbite:quickbite123@localhost:5434/quickbite_test"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionFactory = async_sessionmaker(test_engine, expire_on_commit=False)


class TestUnitOfWork(UnitOfWork):
    session_factory = TestSessionFactory


async def override_get_uow():
    async with TestUnitOfWork() as uow:
        yield uow


# ── create schema once per session, drop at end ───────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── wipe all rows between every test ──────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# ── http client with dependency override ──────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_uow] = override_get_uow
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ── pre-registered + logged-in user ───────────────────────────────────────────

REGISTER_PAYLOAD = {
    "email": "kritim@quickbite.com",
    "phone": "9800000001",
    "full_name": "Kritim Test",
    "password": "Password123!",
    "role": "customer",
}


@pytest_asyncio.fixture
async def auth_tokens(client):
    """Register + login, return {'access_token': ..., 'refresh_token': ...}"""
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    resp = await client.post("/api/v1/auth/login", json={
        "email": REGISTER_PAYLOAD["email"],
        "password": REGISTER_PAYLOAD["password"],
    })
    return resp.json()["data"]


@pytest_asyncio.fixture
async def auth_headers(auth_tokens):
    return {"Authorization": f"Bearer {auth_tokens['access_token']}"}