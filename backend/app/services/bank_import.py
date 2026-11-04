from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from ..models import AuditEvent, BankTransaction

COLUMN_ALIASES = {
    "date": ["date", "transaction_date", "交易日期", "交易时间", "记账日期", "日期"],
    "amount": ["amount", "交易金额", "金额", "收入金额", "发生额"],
    "counterparty": ["counterparty", "对方户名", "对方名称", "交易对手", "付款方", "对方"],
    "memo": ["memo", "摘要", "备注", "用途", "附言"],
    "direction": ["direction", "收支方向", "借贷标志", "类型"],
}


def _rows_from_file(content: bytes, filename: str) -> list[dict[str, object]]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        decoded = None
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                decoded = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if decoded is None:
            raise ValueError("CSV 编码无法识别")
        return list(csv.DictReader(io.StringIO(decoded)))
    if suffix in {".xlsx", ".xlsm"}:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        values = list(sheet.iter_rows(values_only=True))
        if not values:
            return []
        headers = [str(value or "").strip() for value in values[0]]
        return [dict(zip(headers, row, strict=False)) for row in values[1:]]
    raise ValueError("银行流水仅支持 CSV 或 XLSX 文件")


def _resolve_mapping(headers: list[str], supplied: dict[str, str] | None) -> dict[str, str]:
    mapping = dict(supplied or {})
    normalized = {header.strip().lower(): header for header in headers}
    for target, aliases in COLUMN_ALIASES.items():
        if target in mapping:
            continue
        for alias in aliases:
            if alias.lower() in normalized:
                mapping[target] = normalized[alias.lower()]
                break
    missing = [field for field in ("date", "amount", "counterparty") if field not in mapping]
    if missing:
        raise ValueError(f"缺少必要列映射：{', '.join(missing)}")
    return mapping


def _to_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法识别日期：{text}")


def _to_amount(value: object) -> Decimal:
    text = str(value or "0").replace(",", "").replace("￥", "").replace("¥", "").strip()
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"无法识别金额：{value}") from exc


def import_bank_transactions(
    db: Session,
    tenant_id: str,
    content: bytes,
    filename: str,
    supplied_mapping: dict[str, str] | None = None,
) -> tuple[str, int, int, list[str]]:
    rows = _rows_from_file(content, filename)
    if not rows:
        return str(uuid.uuid4()), 0, 0, []
    headers = [str(key) for key in rows[0].keys()]
    mapping = _resolve_mapping(headers, supplied_mapping)
    batch_id = str(uuid.uuid4())
    imported = 0
    duplicates = 0
    errors: list[str] = []

    for index, row in enumerate(rows, start=2):
        try:
            transaction_date = _to_date(row.get(mapping["date"]))
            raw_amount = _to_amount(row.get(mapping["amount"]))
            raw_direction = str(row.get(mapping.get("direction", ""), "")).strip().lower()
            direction = (
                "outflow"
                if raw_amount < 0 or raw_direction in {"支出", "借", "debit", "outflow"}
                else "inflow"
            )
            amount = abs(raw_amount)
            counterparty = str(row.get(mapping["counterparty"], "")).strip()
            memo = str(row.get(mapping.get("memo", ""), "")).strip()
            canonical = json.dumps(
                [transaction_date.isoformat(), str(amount), direction, counterparty, memo], ensure_ascii=False
            )
            source_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            exists = db.query(BankTransaction).filter_by(tenant_id=tenant_id, source_hash=source_hash).first()
            if exists:
                duplicates += 1
                continue
            db.add(
                BankTransaction(
                    tenant_id=tenant_id,
                    transaction_date=transaction_date,
                    amount=amount,
                    direction=direction,
                    counterparty=counterparty or "未知交易对手",
                    memo=memo,
                    source_hash=source_hash,
                    import_batch=batch_id,
                )
            )
            imported += 1
        except ValueError as exc:
            errors.append(f"第{index}行：{exc}")
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            event_type="bank_statement_imported",
            entity_type="bank_import",
            entity_id=batch_id,
            detail={
                "filename": filename,
                "imported": imported,
                "duplicates": duplicates,
                "errors": len(errors),
            },
        )
    )
    db.commit()
    return batch_id, imported, duplicates, errors
