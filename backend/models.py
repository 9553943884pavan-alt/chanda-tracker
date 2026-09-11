import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    UUID,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin','collector','giver')"),
        CheckConstraint("year BETWEEN 1 AND 4"),
        CheckConstraint("branch IN ('IT','ECE')"),
        CheckConstraint("gender IN ('M','F')"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    roll_no: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    year: Mapped[int | None] = mapped_column(SmallInteger)
    branch: Mapped[str | None] = mapped_column(String(10))
    gender: Mapped[str | None] = mapped_column(String(10))
    email_verified: Mapped[bool | None] = mapped_column(Boolean, server_default=text("FALSE"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class CollectorGroup(Base):
    __tablename__ = "collector_groups"
    __table_args__ = (
        CheckConstraint("year BETWEEN 1 AND 4"),
        CheckConstraint("branch IN ('IT','ECE')"),
        CheckConstraint("gender IN ('M','F')"),
        UniqueConstraint("year", "branch", "gender"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    branch: Mapped[str | None] = mapped_column(String(10))
    gender: Mapped[str] = mapped_column(String(10), nullable=False)


class CollectorProfile(Base):
    __tablename__ = "collector_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    collector_group_id: Mapped[int] = mapped_column(Integer, ForeignKey("collector_groups.id"), nullable=False)
    upi_id: Mapped[str | None] = mapped_column(String(100))
    qr_image_key: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(15))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class OTPCode(Base):
    __tablename__ = "otp_codes"
    __table_args__ = (CheckConstraint("purpose IN ('signup','reset')"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    # signup pending data (full_name, roll_no, role, year, branch, gender) stored with the code so it survives restarts
    payload: Mapped[dict | None] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int | None] = mapped_column(SmallInteger, server_default=text("0"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


OtpCode = OTPCode


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("status IN ('pending','verified','rejected')"),
        UniqueConstraint("transaction_ref"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    giver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    collector_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    transaction_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    screenshot_key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str | None] = mapped_column(String(20), server_default=text("'pending'"), index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)


class Broadcast(Base):
    __tablename__ = "broadcasts"
    __table_args__ = (CheckConstraint("filter_role IN ('all','collector','giver')"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sent_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filter_role: Mapped[str | None] = mapped_column(String(20), server_default=text("'all'"), index=True)
    filter_year: Mapped[int | None] = mapped_column(SmallInteger, index=True)
    filter_branch: Mapped[str | None] = mapped_column(String(10), index=True)
    filter_gender: Mapped[str | None] = mapped_column(String(10), index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
