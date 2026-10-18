from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class DocumentStatus(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    DOWNLOADED = "DOWNLOADED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class RunStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_number: Mapped[int] = mapped_column(Integer, index=True)
    meeting_label: Mapped[str] = mapped_column(String(32))
    source_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    canonical_url: Mapped[str] = mapped_column(Text, unique=True)
    first_discovered_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default=DocumentStatus.DISCOVERED.value)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    observations: Mapped[list["ProductObservation"]] = relationship(back_populates="source_document")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    product_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    holder: Mapped[str | None] = mapped_column(Text, nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    registration_date_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_meeting_number: Mapped[int] = mapped_column(Integer)
    current_source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ProductObservation(Base):
    __tablename__ = "product_observations"
    __table_args__ = (
        UniqueConstraint("source_document_id", "observation_key", name="uq_observation_document_key"),
        Index("ix_observation_registration", "registration_no"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"))
    registration_no: Mapped[str] = mapped_column(String(80))
    observation_key: Mapped[str] = mapped_column(String(64))
    product_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    holder: Mapped[str | None] = mapped_column(Text, nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    registration_date_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    source_document: Mapped[SourceDocument] = relationship(back_populates="observations")


class ImportRun(Base):
    __tablename__ = "import_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trigger: Mapped[str] = mapped_column(String(24), default="CLI")
    status: Mapped[str] = mapped_column(String(24), default=RunStatus.QUEUED.value, index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    discovered_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    downloaded_count: Mapped[int] = mapped_column(Integer, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ImportRunDocument(Base):
    __tablename__ = "import_run_documents"
    __table_args__ = (UniqueConstraint("run_id", "source_document_id", name="uq_run_document"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("import_runs.id", ondelete="CASCADE"), index=True)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(24))
    records_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScheduleConfig(Base):
    __tablename__ = "schedule_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    cadence: Mapped[str] = mapped_column(String(16), default="MONTHLY")
    local_time: Mapped[str] = mapped_column(String(5), default="09:00")
    weekday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_of_month: Mapped[int] = mapped_column(Integer, default=8)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kuala_Lumpur")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Session(Base):
    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("admin_users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
