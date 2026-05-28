

from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    message: str
    status_code: int
    data: T | None = None

    