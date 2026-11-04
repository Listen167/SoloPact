from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import (
    AuditEvent,
    BankTransaction,
    Contract,
    PaymentMilestone,
    ReconciliationMatch,
)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", value.lower())


def score_candidate(
    milestone: PaymentMilestone, contract: Contract, transaction: BankTransaction
) -> tuple[Decimal, list[str], Decimal]:
    score = Decimal("0")
    reasons: list[str] = []
    difference = (transaction.amount - milestone.amount).copy_abs()
    exact_amount = difference <= Decimal("0.01")
    ratio = difference / milestone.amount if milestone.amount else Decimal("1")
    if exact_amount:
        score += Decimal("0.55")
        reasons.append("金额完全一致")
    elif ratio <= Decimal("0.02"):
        score += Decimal("0.30")
        reasons.append("金额差异不超过2%")

    client = _normalize(contract.client_name)
    counterparty = _normalize(transaction.counterparty)
    if client and counterparty and (client in counterparty or counterparty in client):
        score += Decimal("0.25")
        reasons.append("交易对手与客户名称一致")

    day_gap = abs((transaction.transaction_date - milestone.due_date).days)
    if day_gap <= 7:
        score += Decimal("0.15")
        reasons.append("交易日期在到期日前后7天内")
    elif day_gap <= 30:
        score += Decimal("0.08")
        reasons.append("交易日期在到期日前后30天内")

    if contract.contract_number and _normalize(contract.contract_number) in _normalize(transaction.memo):
        score += Decimal("0.05")
        reasons.append("摘要包含合同编号")

    if not exact_amount:
        score = min(score, Decimal("0.79"))
    return min(score, Decimal("1")), reasons, difference


def run_reconciliation(db: Session, tenant_id: str) -> tuple[int, int, int, list[ReconciliationMatch]]:
    confirmed_matches = db.query(ReconciliationMatch).filter_by(tenant_id=tenant_id, confirmed=True).all()
    db.query(ReconciliationMatch).filter_by(tenant_id=tenant_id, confirmed=False).delete(
        synchronize_session=False
    )
    milestones = (
        db.query(PaymentMilestone)
        .join(Contract)
        .filter(PaymentMilestone.tenant_id == tenant_id, PaymentMilestone.status != "paid")
        .all()
    )
    transactions = (
        db.query(BankTransaction)
        .filter_by(tenant_id=tenant_id, direction="inflow")
        .order_by(BankTransaction.transaction_date)
        .all()
    )
    used_transactions: set[str] = {item.transaction_id for item in confirmed_matches}
    matches: list[ReconciliationMatch] = list(confirmed_matches)
    auto_matched = len(confirmed_matches)
    needs_review = 0

    for milestone in milestones:
        contract = db.get(Contract, milestone.contract_id)
        candidates: list[tuple[Decimal, BankTransaction, list[str], Decimal]] = []
        for transaction in transactions:
            if transaction.id in used_transactions:
                continue
            score, reasons, difference = score_candidate(milestone, contract, transaction)
            if score >= Decimal("0.50"):
                candidates.append((score, transaction, reasons, difference))
        if not candidates:
            continue
        score, transaction, reasons, difference = max(candidates, key=lambda item: item[0])
        status = (
            "auto_matched" if score >= Decimal("0.80") and difference <= Decimal("0.01") else "needs_review"
        )
        match = ReconciliationMatch(
            tenant_id=tenant_id,
            milestone_id=milestone.id,
            transaction_id=transaction.id,
            score=score,
            status=status,
            reasons=reasons,
            amount_difference=difference,
            confirmed=status == "auto_matched",
        )
        db.add(match)
        matches.append(match)
        used_transactions.add(transaction.id)
        if status == "auto_matched":
            auto_matched += 1
            milestone.status = "paid"
            milestone.paid_at = transaction.transaction_date
        else:
            needs_review += 1

    unmatched = len([item for item in transactions if item.id not in used_transactions])
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            event_type="reconciliation_completed",
            entity_type="reconciliation_run",
            entity_id="latest",
            detail={"auto_matched": auto_matched, "needs_review": needs_review, "unmatched": unmatched},
        )
    )
    db.commit()
    for match in matches:
        db.refresh(match)
    return auto_matched, needs_review, unmatched, matches
