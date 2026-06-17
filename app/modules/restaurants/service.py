import re
from uuid import UUID

from fastapi import HTTPException, status

from core.unit_of_work import UnitOfWork
from modules.restaurants.model import Restaurant
from modules.restaurants.schemas import RestaurantCreate, RestaurantUpdate
from modules.users.model import User
from shared.enums import UserRole, RestaurantStatus
from modules.restaurants.state_machine import assert_can_transition
from shared.enums import RestaurantStatus   

def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug.strip("-")


class RestaurantService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def _unique_slug(self, name: str) -> str:
        base = _slugify(name) or "restaurant"
        slug, counter = base, 1
        while await self.uow.restaurants.get_by_slug(slug):
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    def _assert_owner_or_admin(self, restaurant: Restaurant, user: User) -> None:
        if user.role == UserRole.admin:
            return
        if restaurant.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this restaurant.",
            )

    async def get_or_404(self, restaurant_id: UUID) -> Restaurant:
        r = await self.uow.restaurants.get(restaurant_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found.",
            )
        return r

    async def create(self, data: RestaurantCreate, owner: User) -> Restaurant:
        slug = await self._unique_slug(data.name)
        restaurant = Restaurant(
            owner_id=owner.id,
            slug=slug,
            status=RestaurantStatus.pending,   # starts pending, admin approves (step 5)
            cuisine_types=[ct.value for ct in data.cuisine_types],
            **data.model_dump(exclude={"cuisine_types"}),
        )
        restaurant = await self.uow.restaurants.create(restaurant)
        await self.uow.commit()
        await self.uow.session.refresh(restaurant)
        return restaurant

    async def list_active(self, limit: int, offset: int) -> list[Restaurant]:
        return await self.uow.restaurants.list_active(limit, offset)

    async def my_restaurants(self, owner: User) -> list[Restaurant]:
        return await self.uow.restaurants.get_by_owner(owner.id)

    async def update(self, restaurant_id: UUID, data: RestaurantUpdate, user: User) -> Restaurant:
        r = await self.get_or_404(restaurant_id)
        self._assert_owner_or_admin(r, user)

        update_data = data.model_dump(exclude_none=True)
        if "cuisine_types" in update_data and data.cuisine_types is not None:
            update_data["cuisine_types"] = [ct.value for ct in data.cuisine_types]

        updated = await self.uow.restaurants.update(r, **update_data)
        await self.uow.commit()
        await self.uow.session.refresh(updated)
        return updated

    async def delete(self, restaurant_id: UUID, user: User) -> None:
        r = await self.get_or_404(restaurant_id)
        self._assert_owner_or_admin(r, user)
        await self.uow.restaurants.delete(r)
        await self.uow.commit()
    

    async def change_status(
        self, restaurant_id: UUID, new_status: RestaurantStatus
    ) -> Restaurant:
        """
        Admin-only status change. Enforces the state machine.
        No ownership check — admins act on ANY restaurant (the router guards
        this with require_role("ADMIN")).
        """
        r = await self.get_or_404(restaurant_id)

        # state machine — raises ValueError on illegal transition,
        # which the router maps to 400
        assert_can_transition(r.status, new_status)

        updated = await self.uow.restaurants.update(r, status=new_status)
        await self.uow.commit()
        await self.uow.session.refresh(updated)
        return updated