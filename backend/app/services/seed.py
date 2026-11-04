from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import (
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
from .reconciliation import run_reconciliation
from .risks import refresh_risk_alerts

DEMO_TENANT_ID = "demo"


def _transaction_hash(*parts: object) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()


def ensure_demo_tenant(db: Session) -> Tenant:
    tenant = db.get(Tenant, DEMO_TENANT_ID)
    if tenant is None:
        tenant = Tenant(id=DEMO_TENANT_ID, name="极光独立顾问工作室")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    return tenant


def reset_demo_data(db: Session, as_of: date) -> None:
    ensure_demo_tenant(db)
    for model in (
        CollectionDraft,
        RiskAlert,
        ReconciliationMatch,
        AuditEvent,
        BankTransaction,
        PaymentMilestone,
        Contract,
        Document,
    ):
        db.query(model).filter_by(tenant_id=DEMO_TENANT_ID).delete(synchronize_session=False)

    contracts = [
        Contract(
            tenant_id=DEMO_TENANT_ID,
            contract_number="RR-2026-017",
            title="品牌战略与内容咨询服务合同",
            client_name="岭南智造有限公司",
            provider_name="极光独立顾问工作室",
            total_amount=Decimal("120000"),
            effective_date=date(2026, 9, 20),
            end_date=date(2026, 12, 20),
            status="confirmed",
            extraction_confidence=Decimal("0.96"),
            source_evidence={"page": 1, "quote": "甲方：岭南智造有限公司；合同总金额人民币120,000元。"},
            milestones=[
                PaymentMilestone(
                    tenant_id=DEMO_TENANT_ID,
                    sequence=1,
                    label="第一期款",
                    amount=Decimal("36000"),
                    due_date=date(2026, 9, 28),
                    condition="合同签署并收到发票后支付",
                    invoice_required=True,
                    status="pending",
                    confidence=Decimal("0.97"),
                    evidence_page=4,
                    evidence_quote="第一期款人民币36,000元，应于2026年9月28日前支付。",
                    confirmed=True,
                ),
                PaymentMilestone(
                    tenant_id=DEMO_TENANT_ID,
                    sequence=2,
                    label="第二期款",
                    amount=Decimal("48000"),
                    due_date=date(2026, 10, 28),
                    condition="中期成果确认后支付",
                    invoice_required=True,
                    status="pending",
                    confidence=Decimal("0.95"),
                    evidence_page=4,
                    evidence_quote="第二期款人民币48,000元，应于2026年10月28日前完成支付。",
                    confirmed=True,
                ),
                PaymentMilestone(
                    tenant_id=DEMO_TENANT_ID,
                    sequence=3,
                    label="尾款",
                    amount=Decimal("36000"),
                    due_date=date(2026, 11, 18),
                    condition="最终成果验收后支付",
                    invoice_required=True,
                    status="pending",
                    confidence=Decimal("0.94"),
                    evidence_page=4,
                    evidence_quote="尾款人民币36,000元，应于2026年11月18日前支付。",
                    confirmed=True,
                ),
            ],
        ),
        Contract(
            tenant_id=DEMO_TENANT_ID,
            contract_number="RR-2026-021",
            title="年度经营顾问服务合同",
            client_name="北辰科技（深圳）有限公司",
            provider_name="极光独立顾问工作室",
            total_amount=Decimal("58000"),
            effective_date=date(2026, 10, 1),
            end_date=date(2027, 3, 31),
            status="confirmed",
            extraction_confidence=Decimal("0.93"),
            source_evidence={"page": 1, "quote": "本合同顾问服务费总额为人民币58,000元。"},
            milestones=[
                PaymentMilestone(
                    tenant_id=DEMO_TENANT_ID,
                    sequence=1,
                    label="启动款",
                    amount=Decimal("29000"),
                    due_date=date(2026, 10, 5),
                    condition="项目启动后支付",
                    invoice_required=False,
                    status="pending",
                    confidence=Decimal("0.93"),
                    evidence_page=3,
                    evidence_quote="启动款29,000元，于2026年10月5日前支付。",
                    confirmed=True,
                ),
                PaymentMilestone(
                    tenant_id=DEMO_TENANT_ID,
                    sequence=2,
                    label="阶段款",
                    amount=Decimal("29000"),
                    due_date=date(2026, 11, 10),
                    condition="首轮经营复盘完成后支付",
                    invoice_required=False,
                    status="pending",
                    confidence=Decimal("0.91"),
                    evidence_page=3,
                    evidence_quote="阶段款29,000元，于2026年11月10日前支付。",
                    confirmed=True,
                ),
            ],
        ),
        Contract(
            tenant_id=DEMO_TENANT_ID,
            contract_number="RR-2026-025",
            title="产品上市策略咨询合同",
            client_name="云帆创意工作室",
            provider_name="极光独立顾问工作室",
            total_amount=Decimal("26000"),
            effective_date=date(2026, 10, 12),
            end_date=date(2026, 11, 30),
            status="confirmed",
            extraction_confidence=Decimal("0.90"),
            source_evidence={"page": 1, "quote": "产品上市策略咨询服务费用为人民币26,000元。"},
            milestones=[
                PaymentMilestone(
                    tenant_id=DEMO_TENANT_ID,
                    sequence=1,
                    label="全款",
                    amount=Decimal("26000"),
                    due_date=date(2026, 11, 2),
                    condition="策略初稿交付后支付",
                    invoice_required=True,
                    status="pending",
                    confidence=Decimal("0.89"),
                    evidence_page=2,
                    evidence_quote="甲方应于2026年11月2日前一次性支付咨询费26,000元。",
                    confirmed=True,
                )
            ],
        ),
    ]
    db.add_all(contracts)
    db.flush()

    transaction_data = [
        (date(2026, 9, 27), Decimal("36000"), "岭南智造有限公司", "RR-2026-017 第一期咨询费"),
        (date(2026, 10, 5), Decimal("29000"), "北辰科技（深圳）有限公司", "RR-2026-021 启动款"),
        (date(2026, 10, 30), Decimal("47500"), "岭南智造有限公司", "RR-2026-017 项目款"),
        (date(2026, 11, 1), Decimal("5600"), "某某网络科技", "服务费入账"),
    ]
    for item in transaction_data:
        db.add(
            BankTransaction(
                tenant_id=DEMO_TENANT_ID,
                transaction_date=item[0],
                amount=item[1],
                direction="inflow",
                counterparty=item[2],
                memo=item[3],
                source_hash=_transaction_hash(*item),
                import_batch="demo-seed",
            )
        )
    db.add(
        AuditEvent(
            tenant_id=DEMO_TENANT_ID,
            event_type="demo_data_loaded",
            entity_type="tenant",
            entity_id=DEMO_TENANT_ID,
            detail={"as_of": as_of.isoformat(), "synthetic": True},
        )
    )
    db.commit()
    run_reconciliation(db, DEMO_TENANT_ID)
    refresh_risk_alerts(db, DEMO_TENANT_ID, as_of)


def seed_if_empty(db: Session, as_of: date) -> None:
    ensure_demo_tenant(db)
    exists = db.query(Contract).filter_by(tenant_id=DEMO_TENANT_ID).first()
    if exists is None:
        reset_demo_data(db, as_of)
