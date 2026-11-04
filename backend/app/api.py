from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .config import get_settings
from .database import get_db
from .models import (
    AuditEvent,
    BankTransaction,
    CollectionDraft,
    Contract,
    Document,
    PaymentMilestone,
    ReconciliationMatch,
    RiskAlert,
    Tenant,
)
from .schemas import (
    AlertOut,
    AuditEventOut,
    BankImportResult,
    BankTransactionOut,
    ContractOut,
    ContractReviewUpdate,
    DashboardMetrics,
    DashboardOut,
    DocumentOut,
    DocumentUploadOut,
    DraftOut,
    DraftRequest,
    DraftReviewUpdate,
    ForecastPoint,
    HealthOut,
    MatchOut,
    ReconciliationResult,
)
from .services.bank_import import import_bank_transactions
from .services.document_parser import extract_contract, extract_pages
from .services.drafts import create_collection_draft
from .services.providers import HuaweiOcrProvider, ModelProvider
from .services.reconciliation import run_reconciliation
from .services.risks import refresh_risk_alerts
from .services.seed import DEMO_TENANT_ID, reset_demo_data
from .services.storage import get_storage_provider

settings = get_settings()
router = APIRouter(prefix=settings.api_prefix)
storage_provider = get_storage_provider(settings)
ocr_provider = HuaweiOcrProvider(settings)
model_provider = ModelProvider(settings)


def get_tenant_id(
    db: Session = Depends(get_db),
    x_tenant_id: str = Header(default=DEMO_TENANT_ID, alias="X-Tenant-ID"),
) -> str:
    tenant = db.get(Tenant, x_tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="租户不存在")
    return tenant.id


def _contract_query(db: Session, tenant_id: str):
    return db.query(Contract).options(joinedload(Contract.milestones)).filter(Contract.tenant_id == tenant_id)


def _enrich_match(db: Session, item: ReconciliationMatch) -> MatchOut:
    milestone = db.get(PaymentMilestone, item.milestone_id)
    contract = db.get(Contract, milestone.contract_id)
    transaction = db.get(BankTransaction, item.transaction_id)
    return MatchOut.model_validate(item).model_copy(
        update={
            "contract_title": contract.title,
            "milestone_label": milestone.label,
            "transaction_counterparty": transaction.counterparty,
            "transaction_amount": transaction.amount,
        }
    )


def _enrich_alert(db: Session, item: RiskAlert) -> AlertOut:
    milestone = db.get(PaymentMilestone, item.milestone_id)
    contract = db.get(Contract, milestone.contract_id)
    return AlertOut.model_validate(item).model_copy(
        update={
            "client_name": contract.client_name,
            "contract_title": contract.title,
            "amount": milestone.amount,
            "due_date": milestone.due_date,
        }
    )


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)) -> HealthOut:
    db.execute(select(1))
    return HealthOut(
        status="ok",
        database="connected",
        storage_provider=storage_provider.name,
        ocr_provider=ocr_provider.name if ocr_provider.configured else "digital-pdf-local",
        model_provider=model_provider.name,
        demo_today=settings.demo_today,
    )


@router.post("/demo/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_demo(db: Session = Depends(get_db)) -> None:
    reset_demo_data(db, settings.demo_today)


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), tenant_id: str = Depends(get_tenant_id)) -> list[Document]:
    return db.query(Document).filter_by(tenant_id=tenant_id).order_by(Document.created_at.desc()).all()


@router.post("/documents", response_model=DocumentUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> DocumentUploadOut:
    if document_type not in {"contract", "invoice", "other"}:
        raise HTTPException(status_code=422, detail="不支持的文档类型")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="上传文件为空")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="单个文件不能超过10MB")
    filename = file.filename or "document.bin"
    digest = hashlib.sha256(content).hexdigest()
    existing = db.query(Document).filter_by(tenant_id=tenant_id, sha256=digest).first()
    if existing:
        existing_contract = _contract_query(db, tenant_id).filter_by(document_id=existing.id).first()
        return DocumentUploadOut(document=DocumentOut.model_validate(existing), contract=existing_contract)

    storage_key = storage_provider.save(tenant_id, filename, content)
    document = Document(
        tenant_id=tenant_id,
        filename=filename,
        document_type=document_type,
        content_type=file.content_type,
        sha256=digest,
        storage_key=storage_key,
        storage_provider=storage_provider.name,
        status="processing",
    )
    db.add(document)
    db.flush()
    contract_model = None
    try:
        if document_type == "contract":
            pages = extract_pages(content, filename, ocr_provider)
            extracted = extract_contract(pages, filename)
            document.page_count = len(pages)
            contract_model = Contract(
                tenant_id=tenant_id,
                document_id=document.id,
                contract_number=extracted.contract_number,
                title=extracted.title,
                client_name=extracted.client_name,
                provider_name=extracted.provider_name,
                total_amount=extracted.total_amount,
                effective_date=extracted.effective_date,
                end_date=extracted.end_date,
                status="needs_review",
                extraction_confidence=extracted.confidence,
                source_evidence=extracted.evidence,
            )
            db.add(contract_model)
            db.flush()
            for index, milestone in enumerate(extracted.milestones, start=1):
                db.add(
                    PaymentMilestone(
                        tenant_id=tenant_id,
                        contract_id=contract_model.id,
                        sequence=index,
                        label=milestone.label,
                        amount=milestone.amount,
                        due_date=milestone.due_date,
                        condition=milestone.condition,
                        invoice_required=milestone.invoice_required,
                        confidence=milestone.confidence,
                        evidence_page=milestone.evidence_page,
                        evidence_quote=milestone.evidence_quote,
                        confirmed=False,
                    )
                )
        document.status = "needs_review" if document_type == "contract" else "ready"
        db.add(
            AuditEvent(
                tenant_id=tenant_id,
                event_type="document_uploaded",
                entity_type="document",
                entity_id=document.id,
                detail={"filename": filename, "document_type": document_type, "sha256": digest},
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        document = db.query(Document).filter_by(tenant_id=tenant_id, sha256=digest).first()
        if document:
            document.status = "failed"
            document.error_message = str(exc)[:500]
            db.commit()
        raise HTTPException(status_code=422, detail=f"文档处理失败：{exc}") from exc

    db.refresh(document)
    if contract_model:
        contract_model = _contract_query(db, tenant_id).filter_by(id=contract_model.id).one()
    return DocumentUploadOut(document=DocumentOut.model_validate(document), contract=contract_model)


@router.get("/contracts", response_model=list[ContractOut])
def list_contracts(db: Session = Depends(get_db), tenant_id: str = Depends(get_tenant_id)) -> list[Contract]:
    return _contract_query(db, tenant_id).order_by(Contract.updated_at.desc()).all()


@router.get("/contracts/{contract_id}/review", response_model=ContractOut)
def get_contract_review(
    contract_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> Contract:
    contract = _contract_query(db, tenant_id).filter_by(id=contract_id).first()
    if contract is None:
        raise HTTPException(status_code=404, detail="合同不存在")
    return contract


@router.patch("/contracts/{contract_id}/review", response_model=ContractOut)
def update_contract_review(
    contract_id: str,
    payload: ContractReviewUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> Contract:
    contract = _contract_query(db, tenant_id).filter_by(id=contract_id).first()
    if contract is None:
        raise HTTPException(status_code=404, detail="合同不存在")
    for field in ("client_name", "contract_number", "title", "total_amount", "effective_date", "end_date"):
        value = getattr(payload, field)
        if value is not None:
            setattr(contract, field, value)
    milestone_map = {item.id: item for item in contract.milestones}
    for update in payload.milestones:
        milestone = milestone_map.get(update.id)
        if milestone is None:
            raise HTTPException(status_code=422, detail=f"付款节点{update.id}不属于当前合同")
        for field in ("label", "amount", "due_date", "condition", "invoice_required"):
            value = getattr(update, field)
            if value is not None:
                setattr(milestone, field, value)
        milestone.confirmed = update.confirmed
    if payload.confirmed:
        contract.status = "confirmed"
        for milestone in contract.milestones:
            milestone.confirmed = True
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            event_type="contract_reviewed",
            entity_type="contract",
            entity_id=contract.id,
            detail={"confirmed": payload.confirmed, "milestones_updated": len(payload.milestones)},
        )
    )
    db.commit()
    refresh_risk_alerts(db, tenant_id, settings.demo_today)
    return _contract_query(db, tenant_id).filter_by(id=contract_id).one()


@router.post("/bank-imports", response_model=BankImportResult, status_code=status.HTTP_201_CREATED)
async def import_bank_statement(
    file: UploadFile = File(...),
    mapping: str | None = Form(default=None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> BankImportResult:
    content = await file.read()
    try:
        parsed_mapping = json.loads(mapping) if mapping else None
        batch_id, imported, duplicates, errors = import_bank_transactions(
            db, tenant_id, content, file.filename or "statement.csv", parsed_mapping
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return BankImportResult(
        batch_id=batch_id, imported=imported, skipped_duplicates=duplicates, errors=errors
    )


@router.get("/bank-transactions", response_model=list[BankTransactionOut])
def list_transactions(
    db: Session = Depends(get_db), tenant_id: str = Depends(get_tenant_id)
) -> list[BankTransaction]:
    return (
        db.query(BankTransaction)
        .filter_by(tenant_id=tenant_id)
        .order_by(BankTransaction.transaction_date.desc())
        .all()
    )


@router.post("/reconciliation-runs", response_model=ReconciliationResult)
def reconcile(db: Session = Depends(get_db), tenant_id: str = Depends(get_tenant_id)) -> ReconciliationResult:
    auto, review, unmatched, matches = run_reconciliation(db, tenant_id)
    refresh_risk_alerts(db, tenant_id, settings.demo_today)
    return ReconciliationResult(
        auto_matched=auto,
        needs_review=review,
        unmatched=unmatched,
        matches=[_enrich_match(db, item) for item in matches],
    )


@router.get("/reconciliation-matches", response_model=list[MatchOut])
def list_matches(db: Session = Depends(get_db), tenant_id: str = Depends(get_tenant_id)) -> list[MatchOut]:
    items = (
        db.query(ReconciliationMatch)
        .filter_by(tenant_id=tenant_id)
        .order_by(ReconciliationMatch.score.desc())
        .all()
    )
    return [_enrich_match(db, item) for item in items]


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(db: Session = Depends(get_db), tenant_id: str = Depends(get_tenant_id)) -> list[AlertOut]:
    refresh_risk_alerts(db, tenant_id, settings.demo_today)
    items = (
        db.query(RiskAlert)
        .filter_by(tenant_id=tenant_id, status="open")
        .order_by(RiskAlert.severity.desc(), RiskAlert.created_at.desc())
        .all()
    )
    return [_enrich_alert(db, item) for item in items]


@router.get("/alerts/{alert_id}", response_model=AlertOut)
def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> AlertOut:
    item = db.query(RiskAlert).filter_by(id=alert_id, tenant_id=tenant_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="风险提醒不存在")
    return _enrich_alert(db, item)


@router.post("/alerts/{alert_id}/draft", response_model=DraftOut, status_code=status.HTTP_201_CREATED)
def generate_draft(
    alert_id: str,
    payload: DraftRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> CollectionDraft:
    alert = db.query(RiskAlert).filter_by(id=alert_id, tenant_id=tenant_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="风险提醒不存在")
    return create_collection_draft(db, tenant_id, alert, payload.tone, payload.channel, model_provider)


@router.get("/drafts", response_model=list[DraftOut])
def list_drafts(
    db: Session = Depends(get_db), tenant_id: str = Depends(get_tenant_id)
) -> list[CollectionDraft]:
    return (
        db.query(CollectionDraft)
        .filter_by(tenant_id=tenant_id)
        .order_by(CollectionDraft.created_at.desc())
        .all()
    )


@router.patch("/drafts/{draft_id}", response_model=DraftOut)
def review_draft(
    draft_id: str,
    payload: DraftReviewUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> CollectionDraft:
    draft = db.query(CollectionDraft).filter_by(id=draft_id, tenant_id=tenant_id).first()
    if draft is None:
        raise HTTPException(status_code=404, detail="草稿不存在")
    draft.reviewed = payload.reviewed
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            event_type="collection_draft_reviewed",
            entity_type="collection_draft",
            entity_id=draft.id,
            detail={"reviewed": payload.reviewed},
        )
    )
    db.commit()
    db.refresh(draft)
    return draft


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), tenant_id: str = Depends(get_tenant_id)) -> DashboardOut:
    refresh_risk_alerts(db, tenant_id, settings.demo_today)
    contracts = _contract_query(db, tenant_id).all()
    milestones = [milestone for contract in contracts for milestone in contract.milestones]
    pending = [item for item in milestones if item.status != "paid"]
    paid = [item for item in milestones if item.status == "paid"]
    overdue = [item for item in pending if item.due_date < settings.demo_today]
    due_soon = [item for item in pending if 0 <= (item.due_date - settings.demo_today).days <= 14]
    matches = db.query(ReconciliationMatch).filter_by(tenant_id=tenant_id).all()
    matched_transaction_ids = {item.transaction_id for item in matches}
    inflows = db.query(BankTransaction).filter_by(tenant_id=tenant_id, direction="inflow").all()
    alerts = db.query(RiskAlert).filter_by(tenant_id=tenant_id, status="open").all()

    forecast_map: dict[date, dict[str, Decimal]] = defaultdict(
        lambda: {"expected": Decimal("0"), "overdue": Decimal("0")}
    )
    for item in pending:
        key = item.due_date
        if item.due_date < settings.demo_today:
            forecast_map[key]["overdue"] += item.amount
        else:
            forecast_map[key]["expected"] += item.amount
    forecast = [
        ForecastPoint(date=key, expected=value["expected"], overdue=value["overdue"])
        for key, value in sorted(forecast_map.items())
    ]
    contract_by_id = {item.id: item for item in contracts}
    milestone_rows = [
        {
            "id": item.id,
            "contract_id": item.contract_id,
            "contract_title": contract_by_id[item.contract_id].title,
            "client_name": contract_by_id[item.contract_id].client_name,
            "label": item.label,
            "amount": str(item.amount),
            "due_date": item.due_date.isoformat(),
            "status": item.status,
            "confirmed": item.confirmed,
        }
        for item in sorted(milestones, key=lambda row: row.due_date)
    ]
    return DashboardOut(
        as_of=settings.demo_today,
        metrics=DashboardMetrics(
            total_receivable=sum((item.amount for item in pending), Decimal("0")),
            overdue_amount=sum((item.amount for item in overdue), Decimal("0")),
            due_soon_amount=sum((item.amount for item in due_soon), Decimal("0")),
            paid_amount=sum((item.amount for item in paid), Decimal("0")),
            open_alerts=len(alerts),
            unmatched_transactions=len([item for item in inflows if item.id not in matched_transaction_ids]),
        ),
        forecast=forecast,
        milestones=milestone_rows,
        alerts=[_enrich_alert(db, item) for item in alerts[:6]],
    )


@router.get("/audit-events", response_model=list[AuditEventOut])
def list_audit_events(
    db: Session = Depends(get_db), tenant_id: str = Depends(get_tenant_id)
) -> list[AuditEvent]:
    return (
        db.query(AuditEvent)
        .filter_by(tenant_id=tenant_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(100)
        .all()
    )
