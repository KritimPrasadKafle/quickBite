import uuid
from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

T = TypeVar("T")

class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    async def get(self, db: AsyncSession, id: uuid.UUID) -> Optional[T]:
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalars().first()

    async def get_all(
        self, db: AsyncSession, limit: int = 100, offset: int = 0
    ) -> List[T]:
        result = await db.execute(select(self.model).limit(limit).offset(offset))
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_in: T) -> T:
        db.add(obj_in)
        await db.flush()
        await db.refresh(obj_in)
        return obj_in

    async def delete(self, db: AsyncSession, obj: T) -> None:
        await db.delete(obj)
        await db.flush()