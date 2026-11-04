from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..models import Contract, PaymentMilestone, ReconciliationMatch, RiskAlert


def refresh_risk_alerts(db: Session, tenant_id: str, as_of: date) -> list[RiskAlert]:
    milestones = (
        db.query(PaymentMilestone)
        .join(Contract)
        .filter(PaymentMilestone.tenant_id == tenant_id, PaymentMilestone.status != "paid")
        .all()
    )
    wanted: set[tuple[str, str]] = set()
    for milestone in milestones:
        contract = db.get(Contract, milestone.contract_id)
        days = (milestone.due_date - as_of).days
        if days < 0:
            alert_type = "overdue"
            severity = "high" if days <= -14 else "medium"
            title = f"{contract.client_name} · {milestone.label}已逾期{-days}天"
            explanation = f"应于{milestone.due_date.isoformat()}前回款，当前仍未确认到账。"
        elif days <= 14:
            alert_type = "due_soon"
            severity = "medium" if days <= 7 else "low"
            title = f"{contract.client_name} · {milestone.label}{days}天后到期"
            explanation = f"付款节点将在{milestone.due_date.isoformat()}到期，建议提前确认开票与付款安排。"
        else:
            continue
        wanted.add((milestone.id, alert_type))
        existing = (
            db.query(RiskAlert)
            .filter_by(tenant_id=tenant_id, milestone_id=milestone.id, alert_type=alert_type)
            .first()
        )
        values = {
            "severity": severity,
            "title": title,
            "explanation": explanation,
            "evidence": {"page": milestone.evidence_page, "quote": milestone.evidence_quote},
        }
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
        else:
            db.add(
                RiskAlert(
                    tenant_id=tenant_id,
                    milestone_id=milestone.id,
                    alert_type=alert_type,
                    **values,
                )
            )

        review_match = (
            db.query(ReconciliationMatch)
            .filter_by(tenant_id=tenant_id, milestone_id=milestone.id, status="needs_review")
            .first()
        )
        if review_match:
            mismatch_type = "amount_mismatch"
            wanted.add((milestone.id, mismatch_type))
            mismatch = (
                db.query(RiskAlert)
                .filter_by(tenant_id=tenant_id, milestone_id=milestone.id, alert_type=mismatch_type)
                .first()
            )
            mismatch_values = {
                "severity": "medium",
                "title": f"{contract.client_name} · 疑似回款金额不一致",
                "explanation": f"发现候选流水，但与应收金额相差¥{review_match.amount_difference:,.2f}，需要人工确认。",
                "evidence": {"page": milestone.evidence_page, "quote": milestone.evidence_quote},
            }
            if mismatch:
                for key, value in mismatch_values.items():
                    setattr(mismatch, key, value)
            else:
                db.add(
                    RiskAlert(
                        tenant_id=tenant_id,
                        milestone_id=milestone.id,
                        alert_type=mismatch_type,
                        **mismatch_values,
                    )
                )

    existing_alerts = db.query(RiskAlert).filter_by(tenant_id=tenant_id, status="open").all()
    for alert in existing_alerts:
        if (alert.milestone_id, alert.alert_type) not in wanted:
            alert.status = "resolved"
    db.commit()
    return db.query(RiskAlert).filter_by(tenant_id=tenant_id, status="open").all()
