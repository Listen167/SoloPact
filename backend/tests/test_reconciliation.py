from datetime import date

from backend.app.models import ReconciliationMatch, RiskAlert
from backend.app.services.reconciliation import run_reconciliation
from backend.app.services.risks import refresh_risk_alerts
from backend.app.services.seed import DEMO_TENANT_ID


def test_reconciliation_never_auto_confirms_amount_mismatch(db) -> None:
    auto, review, unmatched, matches = run_reconciliation(db, DEMO_TENANT_ID)

    assert auto == 2
    assert review == 1
    assert unmatched == 1
    review_match = next(item for item in matches if item.status == "needs_review")
    assert review_match.amount_difference > 0
    assert review_match.confirmed is False
    assert float(review_match.score) < 0.8


def test_reconciliation_is_idempotent_and_does_not_reuse_paid_transactions(db) -> None:
    first = run_reconciliation(db, DEMO_TENANT_ID)
    second = run_reconciliation(db, DEMO_TENANT_ID)

    assert first[:3] == second[:3] == (2, 1, 1)
    confirmed_transaction_ids = {
        item.transaction_id
        for item in db.query(ReconciliationMatch).filter_by(tenant_id=DEMO_TENANT_ID, confirmed=True).all()
    }
    assert len(confirmed_transaction_ids) == 2


def test_risk_engine_keeps_contract_evidence(db) -> None:
    run_reconciliation(db, DEMO_TENANT_ID)
    alerts = refresh_risk_alerts(db, DEMO_TENANT_ID, date(2026, 11, 4))

    assert any(item.alert_type == "overdue" for item in alerts)
    mismatch = next(item for item in alerts if item.alert_type == "amount_mismatch")
    assert mismatch.evidence["page"] == 4
    assert "48,000" in mismatch.evidence["quote"]
    assert db.query(ReconciliationMatch).filter_by(tenant_id=DEMO_TENANT_ID).count() == 3
    assert db.query(RiskAlert).filter_by(tenant_id=DEMO_TENANT_ID, status="open").count() == 5
