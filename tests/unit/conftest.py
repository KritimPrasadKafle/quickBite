import pytest
from modules.users.service import UserService


@pytest.fixture
def service(mock_uow) -> UserService:
    return UserService(mock_uow)