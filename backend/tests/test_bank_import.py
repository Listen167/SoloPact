from backend.app.models import BankTransaction
from backend.app.services.bank_import import import_bank_transactions
from backend.app.services.seed import DEMO_TENANT_ID


def test_bank_import_maps_chinese_headers_and_skips_duplicates(db) -> None:
    content = ("交易日期,交易金额,对方户名,摘要\n2026-11-03,8888.00,新客户有限公司,咨询服务费\n").encode(
        "utf-8-sig"
    )

    _, imported, duplicates, errors = import_bank_transactions(db, DEMO_TENANT_ID, content, "statement.csv")
    _, imported_again, duplicates_again, _ = import_bank_transactions(
        db, DEMO_TENANT_ID, content, "statement.csv"
    )

    assert imported == 1
    assert duplicates == 0
    assert errors == []
    assert imported_again == 0
    assert duplicates_again == 1
    assert db.query(BankTransaction).filter_by(counterparty="新客户有限公司").count() == 1
