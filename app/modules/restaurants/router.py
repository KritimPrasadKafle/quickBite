from uuid import UUID
from fastapi import APIRouter, Depends, Query

from core.unit_of_work import UnitOfWork
from core.dependencies import get_uow, get_current_user, require_role
from modules.users.model import User
from modules.restaurants.service import RestaurantService
from modules.restaurants.schemas import (
    RestaurantCreate, RestaurantUpdate, RestaurantResponse,
)
from shared.base_schema import APIResponse
from shared.enums import UserRole

from fastapi import HTTPException  
from modules.restaurants.schemas import RestaurantStatusUpdate
from shared.enums import RestaurantStatus
from shared.enums import RestaurantSortBy, CuisineType
from modules.restaurants.schemas import PaginatedRestaurants, PaginationMeta




router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


def get_restaurant_service(uow: UnitOfWork = Depends(get_uow)) -> RestaurantService:
    return RestaurantService(uow)


@router.post("", response_model=APIResponse[RestaurantResponse], status_code=201)
async def create_restaurant(
    data: RestaurantCreate,
    current_user: User = Depends(require_role(UserRole.restaurant_owner.value)),
    service: RestaurantService = Depends(get_restaurant_service),
):
    r = await service.create(data, current_user)
    return APIResponse(
        message="Restaurant created. Awaiting admin approval.",
        status_code=201,
        data=RestaurantResponse.model_validate(r),
    )


@router.get("", response_model=APIResponse[list[RestaurantResponse]])
async def list_restaurants(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: RestaurantService = Depends(get_restaurant_service),
):
    items = await service.list_active(limit, offset)
    return APIResponse(
        message="Restaurants fetched.",
        status_code=200,
        data=[RestaurantResponse.model_validate(r) for r in items],
    )


@router.get("/me", response_model=APIResponse[list[RestaurantResponse]])
async def my_restaurants(
    current_user: User = Depends(require_role(UserRole.restaurant_owner.value)),
    service: RestaurantService = Depends(get_restaurant_service),
):
    items = await service.my_restaurants(current_user)
    return APIResponse(
        message="Your restaurants fetched.",
        status_code=200,
        data=[RestaurantResponse.model_validate(r) for r in items],
    )


@router.get("/{restaurant_id}", response_model=APIResponse[RestaurantResponse])
async def get_restaurant(
    restaurant_id: UUID,
    service: RestaurantService = Depends(get_restaurant_service),
):
    r = await service.get_or_404(restaurant_id)
    return APIResponse(
        message="Restaurant fetched.",
        status_code=200,
        data=RestaurantResponse.model_validate(r),
    )


@router.put("/{restaurant_id}", response_model=APIResponse[RestaurantResponse])
async def update_restaurant(
    restaurant_id: UUID,
    data: RestaurantUpdate,
    current_user: User = Depends(get_current_user),
    service: RestaurantService = Depends(get_restaurant_service),
):
    r = await service.update(restaurant_id, data, current_user)
    return APIResponse(
        message="Restaurant updated.",
        status_code=200,
        data=RestaurantResponse.model_validate(r),
    )


@router.delete("/{restaurant_id}", response_model=APIResponse[None])
async def delete_restaurant(
    restaurant_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RestaurantService = Depends(get_restaurant_service),
):
    await service.delete(restaurant_id, current_user)
    return APIResponse(message="Restaurant deleted.", status_code=200, data=None)



@router.patch("/{restaurant_id}/status", response_model=APIResponse[RestaurantResponse])
async def change_restaurant_status(
    restaurant_id: UUID,
    data: RestaurantStatusUpdate,
    _: User = Depends(require_role(UserRole.admin.value)),   # admin only
    service: RestaurantService = Depends(get_restaurant_service),
):
    try:
        r = await service.change_status(restaurant_id, data.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return APIResponse(
        message=f"Restaurant status changed to {data.status.value}.",
        status_code=200,
        data=RestaurantResponse.model_validate(r),
    )


@router.get("", response_model=APIResponse[PaginatedRestaurants])
async def list_restaurants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    city: str | None = Query(None, description="Partial, case-insensitive city match"),
    cuisine: CuisineType | None = Query(None, description="Filter by a single cuisine"),
    min_rating: float | None = Query(None, ge=0, le=5, description="Minimum average rating"),
    open_now: bool = Query(False, description="Only restaurants open at the current time (NPT)"),
    sort_by: RestaurantSortBy = Query(RestaurantSortBy.rating),
    service: RestaurantService = Depends(get_restaurant_service),
):
    items, meta = await service.list_restaurants(
        page=page,
        page_size=page_size,
        city=city,
        cuisine=cuisine.value if cuisine else None,
        min_rating=min_rating,
        open_now=open_now,
        sort_by=sort_by,
    )
    return APIResponse(
        message="Restaurants fetched.",
        status_code=200,
        data=PaginatedRestaurants(
            items=[RestaurantResponse.model_validate(r) for r in items],
            pagination=meta,
        ),
    )