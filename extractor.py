import re
from datetime import date

from models import AdvanceRecord, DoujiaRecord


DATE_PATTERN = r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})日?"


def parse_date(text: str) -> date | None:
    match = re.search(DATE_PATTERN, text)
    if match:
        try:
            return date(*(int(part) for part in match.groups()))
        except ValueError:
            return None

    short_match = re.search(r"(?<!\d)(\d{2})/(\d{1,2})/(\d{1,2})(?!\d)", text)
    if short_match:
        try:
            year, month, day = (int(part) for part in short_match.groups())
            return date(2000 + year, month, day)
        except ValueError:
            return None
    return None


def parse_doujia(text: str) -> tuple[date | None, int | None, str | None, list[DoujiaRecord]]:
    lines = text.splitlines()
    first_line = lines[0] if lines else text
    current_date = parse_date(first_line)
    total_match = re.search(r"今日已支付\s*[：:]\s*[¥￥]?\s*([\d.]+)", first_line)
    declared_total = int(float(total_match.group(1))) if total_match else None
    payer_match = re.search(r"抖加支付人\s*[：:]\s*(.+)", text)
    payer = payer_match.group(1).strip() if payer_match else None

    records: list[DoujiaRecord] = []
    pattern = re.compile(
        r"歌名\s*[：:]\s*[《『‘“](.+?)[》』’”]\s*-\s*博主名\s*[：:]\s*(.+?)\s*-\s*金额\s*[：:]\s*[¥￥]?\s*([\d.]+)"
    )
    for line in lines:
        match = pattern.search(line)
        if not match:
            continue
        records.append(
            DoujiaRecord(
                song=match.group(1).strip(),
                account=match.group(2).strip(),
                doujia_amount=int(float(match.group(3))),
                doujia_payer=payer,
                source_line=line.strip(),
            )
        )
    return current_date, declared_total, payer, records


def parse_advance(text: str) -> tuple[date | None, int | None, int | None, list[AdvanceRecord]]:
    lines = text.splitlines()
    first_line = lines[0] if lines else text
    current_date = parse_date(first_line)
    total_match = re.search(r"今日已垫付\s*[：:]\s*[¥￥]?\s*([\d.]+)", first_line)
    declared_total = int(float(total_match.group(1))) if total_match else None
    count_match = re.search(r"今日共\s*(\d+)\s*笔", text)
    declared_count = int(count_match.group(1)) if count_match else None
    payer_match = re.search(r"打款人\s*[：:]\s*(.+)", text)
    payer = payer_match.group(1).strip() if payer_match else None
    expected_match = re.search(r"预计打款日期\s*[：:]\s*(.+)", text)
    expected_date = parse_date(expected_match.group(1)) if expected_match else None

    records: list[AdvanceRecord] = []
    pattern = re.compile(
        r"申请为\s*[【\[]达人[：:]\s*(.+?)[】\]]\s*垫付\s*[¥￥]?\s*([\d.]+)\s*（歌曲\s*[《『‘“](.+?)[》』’”]\s*）"
    )
    for line in lines:
        match = pattern.search(line)
        if not match:
            continue
        records.append(
            AdvanceRecord(
                account=match.group(1).strip(),
                advance_amount=int(float(match.group(2))),
                song=match.group(3).strip(),
                payer=payer,
                expected_payment_date=expected_date,
                source_line=line.strip(),
            )
        )
    return current_date, declared_total, declared_count, records
