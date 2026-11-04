from decimal import Decimal

from backend.app.services.document_parser import ExtractedPage, extract_contract


def test_extract_contract_with_cited_milestones() -> None:
    pages = [
        ExtractedPage(
            page=1,
            text=(
                "品牌顾问服务合同\n"
                "合同编号：TEST-2026-001\n"
                "甲方：南方创新有限公司\n"
                "乙方：独立顾问工作室\n"
                "签订日期：2026年10月1日\n"
                "合同总金额为人民币100,000元\n"
                "第一期款人民币40,000元，应于2026年10月10日前支付。\n"
                "第二期款人民币60,000元，应于2026年11月10日前支付，并开具发票。"
            ),
        )
    ]

    result = extract_contract(pages, "contract.txt")

    assert result.contract_number == "TEST-2026-001"
    assert result.client_name == "南方创新有限公司"
    assert result.total_amount == Decimal("100000.00")
    assert len(result.milestones) == 2
    assert result.milestones[1].invoice_required is True
    assert result.milestones[1].evidence_page == 1
    assert "60,000" in result.milestones[1].evidence_quote


def test_extract_contract_requires_review_when_no_payment_clause() -> None:
    pages = [ExtractedPage(page=1, text="咨询服务合同\n甲方：示例客户\n合同金额：20,000元")]

    result = extract_contract(pages, "minimal.txt")

    assert len(result.milestones) == 1
    assert result.milestones[0].confidence == Decimal("0.35")
    assert "人工核对" in result.milestones[0].condition
