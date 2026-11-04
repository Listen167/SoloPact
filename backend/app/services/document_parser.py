from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import fitz
from dateutil.parser import parse as parse_date

from .providers import HuaweiOcrProvider


@dataclass
class ExtractedPage:
    page: int
    text: str


@dataclass
class ExtractedMilestone:
    label: str
    amount: Decimal
    due_date: date
    condition: str
    invoice_required: bool
    confidence: Decimal
    evidence_page: int
    evidence_quote: str


@dataclass
class ExtractedContract:
    contract_number: str
    title: str
    client_name: str
    provider_name: str
    total_amount: Decimal
    effective_date: date | None
    end_date: date | None
    confidence: Decimal
    evidence: dict
    milestones: list[ExtractedMilestone]


def extract_pages(content: bytes, filename: str, ocr: HuaweiOcrProvider) -> list[ExtractedPage]:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                return [ExtractedPage(page=1, text=content.decode(encoding))]
            except UnicodeDecodeError:
                continue
        raise ValueError("文本文件编码无法识别")
    if suffix != ".pdf":
        raise ValueError("合同当前仅支持 PDF、TXT 或 Markdown 文件")

    document = fitz.open(stream=content, filetype="pdf")
    pages: list[ExtractedPage] = []
    for index, page in enumerate(document):
        text = page.get_text("text").strip()
        if not text and ocr.configured:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            text = ocr.extract_image(pixmap.tobytes("png")).strip()
        pages.append(ExtractedPage(page=index + 1, text=text))
    return pages


def _first_match(patterns: list[str], text: str, default: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" ：:，,。")
    return default


def _parse_amount(value: str) -> Decimal:
    cleaned = value.replace(",", "").replace("，", "").replace(" ", "")
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")


def _parse_cn_date(text: str) -> date | None:
    match = re.search(r"(20\d{2})[年\-/\.](\d{1,2})[月\-/\.](\d{1,2})日?", text)
    if match:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    try:
        parsed = parse_date(text, fuzzy=True, dayfirst=False)
        return parsed.date() if parsed.year >= 2000 else None
    except (ValueError, OverflowError):
        return None


def extract_contract(pages: list[ExtractedPage], filename: str) -> ExtractedContract:
    joined = "\n".join(page.text for page in pages)
    lines = [line.strip() for line in joined.splitlines() if line.strip()]
    title = next((line[:120] for line in lines if "合同" in line and len(line) <= 120), Path(filename).stem)
    contract_number = _first_match(
        [r"(?:合同编号|合同号|编号)\s*[:：]\s*([A-Za-z0-9\-_]+)"], joined, f"AUTO-{Path(filename).stem[:24]}"
    )
    client_name = _first_match(
        [r"(?:甲方|委托方|客户名称?)\s*[:：]\s*([^\n，,]{2,60})"], joined, "待确认客户"
    )
    provider_name = _first_match([r"(?:乙方|受托方|服务方)\s*[:：]\s*([^\n，,]{2,60})"], joined, "独立顾问")
    total_text = _first_match(
        [
            r"(?:合同总金额|合同金额|总价款|服务费用)[^\d]{0,12}(?:人民币|RMB|CNY|¥|￥)?\s*([\d,，]+(?:\.\d{1,2})?)",
        ],
        joined,
        "0",
    )
    total_amount = _parse_amount(total_text)
    effective_date = None
    end_date = None
    for line in lines:
        if effective_date is None and any(token in line for token in ("生效日期", "签订日期", "合同日期")):
            effective_date = _parse_cn_date(line)
        if end_date is None and any(token in line for token in ("终止日期", "有效期至", "服务期限至")):
            end_date = _parse_cn_date(line)

    milestones: list[ExtractedMilestone] = []
    payment_tokens = ("支付", "付款", "应付", "款项")
    for page in pages:
        for line in (item.strip() for item in page.text.splitlines() if item.strip()):
            if not any(token in line for token in payment_tokens):
                continue
            amount_match = re.search(r"(?:人民币|RMB|CNY|¥|￥)?\s*([\d,，]+(?:\.\d{1,2})?)\s*元", line)
            due_date = _parse_cn_date(line)
            if not amount_match or not due_date:
                continue
            amount = _parse_amount(amount_match.group(1))
            if amount <= 0:
                continue
            sequence = len(milestones) + 1
            label_match = re.search(r"第([一二三四五六七八九十\d]+)[期笔阶段]", line)
            label = f"第{label_match.group(1)}期款" if label_match else f"第{sequence}期款"
            milestones.append(
                ExtractedMilestone(
                    label=label,
                    amount=amount,
                    due_date=due_date,
                    condition=line[:300],
                    invoice_required="发票" in line,
                    confidence=Decimal("0.92"),
                    evidence_page=page.page,
                    evidence_quote=line[:500],
                )
            )

    if not milestones and total_amount > 0:
        fallback_due = end_date or effective_date or date(2026, 12, 31)
        milestones.append(
            ExtractedMilestone(
                label="合同款（待拆分）",
                amount=total_amount,
                due_date=fallback_due,
                condition="未识别到明确付款节点，请人工核对合同原文。",
                invoice_required=False,
                confidence=Decimal("0.35"),
                evidence_page=1,
                evidence_quote=(pages[0].text[:300] if pages else "未提取到文本"),
            )
        )
    if total_amount <= 0 and milestones:
        total_amount = sum((item.amount for item in milestones), Decimal("0"))

    known_fields = sum(
        [client_name != "待确认客户", total_amount > 0, bool(milestones), effective_date is not None]
    )
    confidence = Decimal(str(0.45 + known_fields * 0.12)).quantize(Decimal("0.01"))
    return ExtractedContract(
        contract_number=contract_number,
        title=title,
        client_name=client_name,
        provider_name=provider_name,
        total_amount=total_amount,
        effective_date=effective_date,
        end_date=end_date,
        confidence=min(confidence, Decimal("0.93")),
        evidence={"page": 1, "quote": (lines[0][:300] if lines else "未提取到文本")},
        milestones=milestones,
    )
