from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Evidence(ApiModel):
    page: int = 1
    quote: str


class DocumentOut(ApiModel):
    id: str
    filename: str
    document_type: str
    content_type: str | None
    sha256: str
    storage_provider: str
    status: str
    error_message: str | None
    page_count: int | None
    created_at: datetime


class MilestoneOut(ApiModel):
    id: str
    sequence: int
    label: str
    amount: Decimal
    due_date: date
    condition: str
    invoice_required: bool
    status: str
    confidence: Decimal
    evidence_page: int
    evidence_quote: str
    confirmed: bool
    paid_at: date | None


class ContractOut(ApiModel):
    id: str
    document_id: str | None
    contract_number: str
    title: str
    client_name: str
    provider_name: str
    currency: str
    total_amount: Decimal
    effective_date: date | None
    end_date: date | None
    status: str
    extraction_confidence: Decimal
    source_evidence: dict
    milestones: list[MilestoneOut] = []
    created_at: datetime
    updated_at: datetime


class DocumentUploadOut(ApiModel):
    document: DocumentOut
    contract: ContractOut | None = None


class MilestoneReviewUpdate(ApiModel):
    id: str
    label: str | None = None
    amount: Decimal | None = Field(default=None, ge=0)
    due_date: date | None = None
    condition: str | None = None
    invoice_required: bool | None = None
    confirmed: bool = True


class ContractReviewUpdate(ApiModel):
    client_name: str | None = None
    contract_number: str | None = None
    title: str | None = None
    total_amount: Decimal | None = Field(default=None, ge=0)
    effective_date: date | None = None
    end_date: date | None = None
    confirmed: bool = True
    milestones: list[MilestoneReviewUpdate] = []


class BankTransactionOut(ApiModel):
    id: str
    transaction_date: date
    amount: Decimal
    direction: str
    counterparty: str
    memo: str
    import_batch: str
    created_at: datetime


class BankImportResult(ApiModel):
    batch_id: str
    imported: int
    skipped_duplicates: int
    errors: list[str]


class MatchOut(ApiModel):
    id: str
    milestone_id: str
    transaction_id: str
    score: Decimal
    status: str
    reasons: list[str]
    amount_difference: Decimal
    confirmed: bool
    contract_title: str | None = None
    milestone_label: str | None = None
    transaction_counterparty: str | None = None
    transaction_amount: Decimal | None = None


class ReconciliationResult(ApiModel):
    auto_matched: int
    needs_review: int
    unmatched: int
    matches: list[MatchOut]


class AlertOut(ApiModel):
    id: str
    milestone_id: str
    alert_type: str
    severity: str
    title: str
    explanation: str
    evidence: dict
    status: str
    created_at: datetime
    client_name: str | None = None
    contract_title: str | None = None
    amount: Decimal | None = None
    due_date: date | None = None


class DraftRequest(ApiModel):
    tone: Literal["friendly", "firm", "formal"] = "friendly"
    channel: Literal["email", "wechat"] = "email"


class DraftOut(ApiModel):
    id: str
    alert_id: str
    tone: str
    channel: str
    subject: str
    body: str
    evidence_summary: str
    reviewed: bool
    created_at: datetime


class DraftReviewUpdate(ApiModel):
    reviewed: bool = True


class ForecastPoint(ApiModel):
    date: date
    expected: Decimal
    overdue: Decimal


class DashboardMetrics(ApiModel):
    total_receivable: Decimal
    overdue_amount: Decimal
    due_soon_amount: Decimal
    paid_amount: Decimal
    open_alerts: int
    unmatched_transactions: int


class DashboardOut(ApiModel):
    as_of: date
    metrics: DashboardMetrics
    forecast: list[ForecastPoint]
    milestones: list[dict]
    alerts: list[AlertOut]


class AuditEventOut(ApiModel):
    id: str
    event_type: str
    entity_type: str
    entity_id: str
    detail: dict
    created_at: datetime


class HealthOut(ApiModel):
    status: str
    database: str
    storage_provider: str
    ocr_provider: str
    model_provider: str
    demo_today: date
