from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.app.models import Contract, Tenant


def test_dashboard_exposes_expected_demo_metrics(client) -> None:
    response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["as_of"] == "2026-11-04"
    assert Decimal(payload["metrics"]["paid_amount"]) == Decimal("65000.00")
    assert Decimal(payload["metrics"]["overdue_amount"]) == Decimal("74000.00")
    assert payload["metrics"]["open_alerts"] == 5


def test_contract_upload_review_and_audit(client) -> None:
    content = (
        "数据分析服务合同\n合同编号：UPLOAD-001\n甲方：测试客户有限公司\n乙方：极光工作室\n"
        "合同金额：30,000元\n签订日期：2026年11月1日\n"
        "第一期款人民币30,000元，应于2026年11月20日前支付。"
    ).encode()
    response = client.post(
        "/api/documents",
        data={"document_type": "contract"},
        files={"file": ("upload.txt", content, "text/plain")},
    )

    assert response.status_code == 201
    contract = response.json()["contract"]
    assert contract["status"] == "needs_review"
    assert contract["milestones"][0]["evidence_page"] == 1

    review = client.patch(
        f"/api/contracts/{contract['id']}/review",
        json={
            "confirmed": True,
            "milestones": [
                {
                    "id": contract["milestones"][0]["id"],
                    "amount": 30000,
                    "due_date": "2026-11-20",
                    "confirmed": True,
                }
            ],
        },
    )
    assert review.status_code == 200
    assert review.json()["status"] == "confirmed"
    assert review.json()["milestones"][0]["confirmed"] is True

    events = client.get("/api/audit-events").json()
    event_types = {item["event_type"] for item in events}
    assert "document_uploaded" in event_types
    assert "contract_reviewed" in event_types


def test_generate_draft_requires_human_review(client) -> None:
    alerts = client.get("/api/alerts").json()
    overdue = next(item for item in alerts if item["alert_type"] == "overdue")

    response = client.post(
        f"/api/alerts/{overdue['id']}/draft",
        json={"tone": "firm", "channel": "email"},
    )

    assert response.status_code == 201
    draft = response.json()
    assert draft["reviewed"] is False
    assert "合同第" in draft["evidence_summary"]
    assert "不会自动发送" not in draft["body"]

    reviewed = client.patch(f"/api/drafts/{draft['id']}", json={"reviewed": True})
    assert reviewed.status_code == 200
    assert reviewed.json()["reviewed"] is True


def test_tenant_cannot_read_another_tenants_contract(db, client) -> None:
    db.add(Tenant(id="other", name="另一个租户"))
    db.add(
        Contract(
            tenant_id="other",
            contract_number="OTHER-001",
            title="隔离合同",
            client_name="其他客户",
            total_amount=100,
            effective_date=date(2026, 1, 1),
            status="confirmed",
        )
    )
    db.commit()
    demo_contract_id = client.get("/api/contracts").json()[0]["id"]

    response = client.get(
        f"/api/contracts/{demo_contract_id}/review",
        headers={"X-Tenant-ID": "other"},
    )

    assert response.status_code == 404
