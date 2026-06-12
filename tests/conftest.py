import pytest
from unittest.mock import AsyncMock, MagicMock
from core.unit_of_work import UnitOfWork   # ← absolute, not ..core


@pytest.fixture
def mock_uow():
    uow = MagicMock(spec=UnitOfWork)
    uow.users = AsyncMock()
    uow.refresh_tokens = AsyncMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    return uow