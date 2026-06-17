# app/modules/restaurants/model.py
from __future__ import annotations
import enum
from uuid import UUID
from decimal import Decimal
from datetime import time

import sqlalchemy as sa
from sqlalchemy import String, Text, Boolean, ForeignKey, Numeric, Integer, Time, Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.enums import RestaurantStatus, CuisineType

from core.database import Base, UUIDMixin, TimestampMixin

class Restaurant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "restaurants"

    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    city: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # cuisine_types — callable default + server_default
    cuisine_types: Mapped[list[str]] = mapped_column(
        PG_ARRAY(String(50)),
        nullable=False,
        default=list,              # callable, not [] — avoids shared mutable
        server_default="{}",       # DB-level default for raw inserts
    )
    status: Mapped[RestaurantStatus] = mapped_column(
        SAEnum(RestaurantStatus, name="restaurant_status", native_enum=False),
        default=RestaurantStatus.pending,
        nullable=False,
        index=True,
    )
    logo_url: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(200), nullable=True)
    opening_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    closing_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    average_rating: Mapped[Decimal | None] = mapped_column(Numeric(2, 1), nullable=True)
    total_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minimum_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    delivery_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    estimated_delivery_time: Mapped[int | None] = mapped_column(Integer, nullable=True)  # in minutes


      # ── Relationships ──
    owner: Mapped["User"] = relationship("User", back_populates="restaurants", lazy="select")
    categories: Mapped[list["Category"]] = relationship(
        "Category", back_populates="restaurant", cascade="all, delete-orphan"
    )
    menu_items: Mapped[list["MenuItem"]] = relationship(
        "MenuItem", back_populates="restaurant", cascade="all, delete-orphan"
    )

class Category(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "categories"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # for menu ordering
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="categories")
    menu_items: Mapped[list["MenuItem"]] = relationship(
        "MenuItem", back_populates="category"
    )


class MenuItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "menu_items"

    # Decision 4: MenuItem links to BOTH restaurant (direct) and category (optional).
    # Direct restaurant_id → "all items for this restaurant" with no join through categories.
    # Nullable category_id → an item can exist before being categorized.
    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discounted_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    image_url: Mapped[str | None] = mapped_column(String(500))

    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_vegetarian: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    preparation_time: Mapped[int | None] = mapped_column(Integer)  # minutes
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="menu_items")
    category: Mapped["Category | None"] = relationship("Category", back_populates="menu_items")