from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[str] = mapped_column(String(32))
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(String(500))
    storage_provider: Mapped[str] = mapped_column(String(32), default="local")
    status: Mapped[str] = mapped_column(String(32), default="processing")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    contract_number: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(255))
    client_name: Mapped[str] = mapped_column(String(255), index=True)
    provider_name: Mapped[str] = mapped_column(String(255), default="独立顾问")
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="needs_review")
    extraction_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))
    source_evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    milestones: Mapped[list[PaymentMilestone]] = relationship(
        back_populates="contract", cascade="all, delete-orphan", order_by="PaymentMilestone.sequence"
    )


class PaymentMilestone(Base):
    __tablename__ = "payment_milestones"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), index=True)
    sequence: Mapped[int]
    label: Mapped[str] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    due_date: Mapped[date] = mapped_column(Date)
    condition: Mapped[str] = mapped_column(Text)
    invoice_required: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))
    evidence_page: Mapped[int] = mapped_column(default=1)
    evidence_quote: Mapped[str] = mapped_column(Text)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    contract: Mapped[Contract] = relationship(back_populates="milestones")


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    __table_args__ = (UniqueConstraint("tenant_id", "source_hash", name="uq_transaction_source"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    direction: Mapped[str] = mapped_column(String(16), default="inflow")
    counterparty: Mapped[str] = mapped_column(String(255), index=True)
    memo: Mapped[str] = mapped_column(Text, default="")
    source_hash: Mapped[str] = mapped_column(String(64))
    import_batch: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ReconciliationMatch(Base):
    __tablename__ = "reconciliation_matches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    milestone_id: Mapped[str] = mapped_column(ForeignKey("payment_milestones.id"), index=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("bank_transactions.id"), index=True)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(String(32))
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    amount_difference: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RiskAlert(Base):
    __tablename__ = "risk_alerts"
    __table_args__ = (UniqueConstraint("tenant_id", "milestone_id", "alert_type", name="uq_alert_type"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    milestone_id: Mapped[str] = mapped_column(ForeignKey("payment_milestones.id"), index=True)
    alert_type: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(255))
    explanation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(24), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CollectionDraft(Base):
    __tablename__ = "collection_drafts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    alert_id: Mapped[str] = mapped_column(ForeignKey("risk_alerts.id"), index=True)
    tone: Mapped[str] = mapped_column(String(24), default="friendly")
    channel: Mapped[str] = mapped_column(String(24), default="email")
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    evidence_summary: Mapped[str] = mapped_column(Text)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(64))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
