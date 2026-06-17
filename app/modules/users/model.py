
from __future__ import annotations  # for forward references in relationships
import uuid
from datetime import datetime

from modules.restaurants.model import Restaurant
from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, UUIDMixin, TimestampMixin
from shared.enums import UserRole



class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, unique=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    avatar_url: Mapped[str | None] = mapped_column(String)

    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete"
    )

    addresses = relationship(
        "UserAddress",
        back_populates="user",
        cascade="all, delete"
    )
    restaurants: Mapped[list["Restaurant"]] = relationship(
        "Restaurant", back_populates="owner", lazy="select"
)


class RefreshToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    token_hash: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="refresh_tokens")


class UserAddress(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_addresses"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    label: Mapped[str] = mapped_column(String)  # Home, Work, Other
    address_line: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False)

    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))

    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="addresses")