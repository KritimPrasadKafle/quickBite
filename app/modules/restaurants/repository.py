from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.base_repository import BaseRepository
from shared.enums import RestaurantStatus
from modules.restaurants.model import Restaurant
from datetime import datetime, time, timezone, timedelta
from sqlalchemy import select, func, and_, or_, asc, desc

from shared.enums import RestaurantStatus, RestaurantSortBy

# Nepal is UTC+5:45
NEPAL_TZ = timezone(timedelta(hours=5, minutes=45))



class RestaurantRepository(BaseRepository[Restaurant]):
    def __init__(self, session: AsyncSession):
        super().__init__(Restaurant, session)

    async def get_by_slug(self, slug: str) -> Restaurant | None:
        result = await self.session.execute(
            select(Restaurant).where(Restaurant.slug == slug)
        )
        return result.scalars().first()

    async def get_by_owner(self, owner_id: UUID) -> list[Restaurant]:
        result = await self.session.execute(
            select(Restaurant)
            .where(Restaurant.owner_id == owner_id)
            .order_by(Restaurant.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_active(self, limit: int = 20, offset: int = 0) -> list[Restaurant]:
        # Placeholder listing — only active restaurants, newest first.
        # Filtering/sorting/pagination metadata comes in step 6.
        result = await self.session.execute(
            select(Restaurant)
            .where(Restaurant.status == RestaurantStatus.active)
            .order_by(Restaurant.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def list_filtered(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        city: str | None = None,
        cuisine: str | None = None,        # single cuisine value, e.g. "NEPALI"
        min_rating: float | None = None,
        open_now: bool = False,
        sort_by: RestaurantSortBy = RestaurantSortBy.rating,
    ) -> tuple[list[Restaurant], int]:
        """
        Returns (items_for_page, total_matching_count).
        Only ACTIVE restaurants are ever returned.
        """
        # ── Base filter: always ACTIVE ──
        conditions = [Restaurant.status == RestaurantStatus.active]

        # ── City (case-insensitive partial match) ──
        if city:
            conditions.append(Restaurant.city.ilike(f"%{city}%"))

        # ── Cuisine (array membership) ──
        # cuisine_types is a Postgres TEXT[]. `.any()` → "is X in the array?"
        if cuisine:
            conditions.append(Restaurant.cuisine_types.any(cuisine))

        # ── Minimum rating ──
        # average_rating is nullable; NULL ratings are excluded when filtering.
        if min_rating is not None:
            conditions.append(Restaurant.average_rating >= min_rating)

        # ── Open now (midnight-crossing aware) ──
        if open_now:
            now_nepal = datetime.now(NEPAL_TZ).time()
            # Two cases:
            #   Normal hours (e.g. 09:00–22:00): opening <= now <= closing
            #   Overnight hours (e.g. 18:00–02:00): now >= opening OR now <= closing
            normal = and_(
                Restaurant.opening_time <= now_nepal,
                Restaurant.closing_time >= now_nepal,
                Restaurant.opening_time <= Restaurant.closing_time,  # not overnight
            )
            overnight = and_(
                Restaurant.opening_time > Restaurant.closing_time,   # crosses midnight
                or_(
                    Restaurant.opening_time <= now_nepal,
                    Restaurant.closing_time >= now_nepal,
                ),
            )
            # Restaurants with NULL hours are treated as closed (excluded).
            conditions.append(
                and_(
                    Restaurant.opening_time.is_not(None),
                    Restaurant.closing_time.is_not(None),
                    or_(normal, overnight),
                )
            )

        where_clause = and_(*conditions)

        # ── Count (total matching, before pagination) ──
        total = (
            await self.session.execute(
                select(func.count()).select_from(Restaurant).where(where_clause)
            )
        ).scalar_one()

        # ── Sorting ──
        # NULLS LAST so unrated/unset values sink to the bottom regardless of direction.
        sort_map = {
            RestaurantSortBy.rating:        desc(Restaurant.average_rating).nulls_last(),
            RestaurantSortBy.delivery_time: asc(Restaurant.estimated_delivery_time).nulls_last(),
            RestaurantSortBy.delivery_fee:  asc(Restaurant.delivery_fee).nulls_last(),
            RestaurantSortBy.newest:        desc(Restaurant.created_at),
        }
        order_clause = sort_map[sort_by]

        # ── Page query ──
        result = await self.session.execute(
            select(Restaurant)
            .where(where_clause)
            .order_by(order_clause, desc(Restaurant.created_at))  # tiebreaker
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        items = list(result.scalars().all())
        return items, total