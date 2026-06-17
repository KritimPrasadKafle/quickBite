from uuid import UUID
from datetime import time
from decimal import Decimal
from pydantic import BaseModel, EmailStr, ConfigDict

from shared.enums import CuisineType, RestaurantStatus


class RestaurantCreate(BaseModel):
    name: str
    description: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    city: str | None = None
    cuisine_types: list[CuisineType] = []
    opening_time: time | None = None
    closing_time: time | None = None
    minimum_order_amount: Decimal | None = None
    delivery_fee: Decimal | None = None
    estimated_delivery_time: int | None = None


class RestaurantUpdate(BaseModel):
    # all optional — patch semantics
    name: str | None = None
    description: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    city: str | None = None
    cuisine_types: list[CuisineType] | None = None
    opening_time: time | None = None
    closing_time: time | None = None
    minimum_order_amount: Decimal | None = None
    delivery_fee: Decimal | None = None
    estimated_delivery_time: int | None = None


class RestaurantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    slug: str
    description: str | None
    phone: str | None
    email: str | None
    address: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    city: str | None
    cuisine_types: list[str]
    status: RestaurantStatus
    logo_url: str | None
    cover_image_url: str | None
    opening_time: time | None
    closing_time: time | None
    average_rating: Decimal | None
    total_reviews: int
    minimum_order_amount: Decimal | None
    delivery_fee: Decimal | None
    estimated_delivery_time: int | None



class RestaurantStatusUpdate(BaseModel):
    status: RestaurantStatus

from pydantic import BaseModel


class PaginationMeta(BaseModel):
    total: int          # total matching records (ignoring page)
    page: int           # current page (1-based)
    page_size: int      # items per page
    total_pages: int    # ceil(total / page_size)
    has_next: bool
    has_prev: bool


class PaginatedRestaurants(BaseModel):
    items: list[RestaurantResponse]
    pagination: PaginationMeta