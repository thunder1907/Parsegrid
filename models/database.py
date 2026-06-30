import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    func
)
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship
)

from config import settings


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for SQLAlchemy 2.0 declarative models with async support."""
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    upload_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    
    # Relationships
    extracted_data: Mapped[Optional["ExtractedData"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        uselist=False
    )

    __table_args__ = (
        Index("ix_documents_file_hash", "file_hash"),
    )


class ExtractedData(Base):
    __tablename__ = "extracted_data"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False
    )
    party_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contract_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    payment_terms_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    penalty_clause_exists: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    governing_law: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="extracted_data")

    __table_args__ = (
        Index("ix_extracted_data_payment_terms_days", "payment_terms_days"),
        Index("ix_extracted_data_needs_review", "needs_review"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    output_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False
    )


# Database Engine and Session Factory Setup
async_engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)
