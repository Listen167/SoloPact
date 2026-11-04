from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import AuditEvent, CollectionDraft, Contract, PaymentMilestone, RiskAlert
from .providers import ModelProvider

TONE_OPENERS = {
    "friendly": "您好，想和您确认一下以下款项的付款安排。",
    "firm": "您好，以下合同款项已到约定付款节点，请协助尽快确认付款安排。",
    "formal": "贵方您好，现就下述合同款项的履行情况正式致函确认。",
}


def create_collection_draft(
    db: Session,
    tenant_id: str,
    alert: RiskAlert,
    tone: str,
    channel: str,
    model_provider: ModelProvider,
) -> CollectionDraft:
    milestone = db.get(PaymentMilestone, alert.milestone_id)
    contract = db.get(Contract, milestone.contract_id)
    amount = Decimal(milestone.amount)
    evidence_summary = f"合同第{milestone.evidence_page}页：{milestone.evidence_quote}"
    payload = {
        "client_name": contract.client_name,
        "contract_title": contract.title,
        "contract_number": contract.contract_number,
        "milestone": milestone.label,
        "amount": f"{amount:.2f}",
        "due_date": milestone.due_date.isoformat(),
        "alert_type": alert.alert_type,
        "tone": tone,
        "channel": channel,
        "evidence": evidence_summary,
    }
    generated = None
    try:
        generated = model_provider.generate_collection_draft(payload)
    except Exception:
        generated = None

    subject = f"关于{contract.title}{milestone.label}的付款确认"
    body = (
        f"{contract.client_name}：\n\n"
        f"{TONE_OPENERS[tone]}\n\n"
        f"合同：{contract.title}（{contract.contract_number}）\n"
        f"款项：{milestone.label}，人民币¥{amount:,.2f}\n"
        f"约定日期：{milestone.due_date.isoformat()}\n"
        f"约定依据：{milestone.evidence_quote}\n\n"
        "烦请确认当前付款进度；如已安排付款，也请告知预计到账时间，感谢配合。\n\n"
        "此致\n敬礼"
    )
    if generated:
        subject = generated["subject"][:255]
        body = generated["body"]
    if channel == "wechat":
        subject = "微信付款提醒"
        body = body.replace("\n\n", "\n")

    draft = CollectionDraft(
        tenant_id=tenant_id,
        alert_id=alert.id,
        tone=tone,
        channel=channel,
        subject=subject,
        body=body,
        evidence_summary=evidence_summary,
    )
    db.add(draft)
    db.flush()
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            event_type="collection_draft_created",
            entity_type="collection_draft",
            entity_id=draft.id,
            detail={"alert_id": alert.id, "tone": tone, "channel": channel, "provider": model_provider.name},
        )
    )
    db.commit()
    db.refresh(draft)
    return draft
