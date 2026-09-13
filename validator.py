from collections import defaultdict
from datetime import date

from models import AdvanceRecord, DoujiaRecord, Issue


def validate(
    doujia_date: date | None,
    doujia_total: int | None,
    doujia_records: list[DoujiaRecord],
    advance_date: date | None,
    advance_total: int | None,
    advance_count: int | None,
    advance_records: list[AdvanceRecord],
) -> list[Issue]:
    issues: list[Issue] = []
    doujia_sum = sum(item.doujia_amount for item in doujia_records)
    advance_sum = sum(item.advance_amount for item in advance_records)

    if doujia_total is None:
        issues.append(Issue(code="missing_field", message="抖加申请缺少声明总额", source="doujia"))
    elif doujia_total != doujia_sum:
        issues.append(Issue(
            code="declared_total_mismatch",
            message=f"抖加声明总额 {doujia_total} 元，但明细合计 {doujia_sum} 元",
            source="doujia",
        ))
    if doujia_date is None:
        issues.append(Issue(code="missing_field", message="抖加申请缺少有效日期", source="doujia"))

    if advance_total is None:
        issues.append(Issue(code="missing_field", message="垫付申请缺少声明总额", source="advance"))
    elif advance_total != advance_sum:
        issues.append(Issue(
            code="declared_total_mismatch",
            message=f"垫付声明总额 {advance_total} 元，但明细合计 {advance_sum} 元",
            source="advance",
        ))
    if advance_count is None:
        issues.append(Issue(code="missing_field", message="垫付申请缺少声明笔数", source="advance"))
    elif advance_count != len(advance_records):
        issues.append(Issue(
            code="declared_count_mismatch",
            message=f"垫付声明 {advance_count} 笔，但识别到 {len(advance_records)} 条明细",
            source="advance",
        ))
    if advance_date is None:
        issues.append(Issue(code="missing_field", message="垫付申请缺少有效日期", source="advance"))

    for item in advance_records:
        if item.expected_payment_date and advance_date and item.expected_payment_date < advance_date:
            issues.append(Issue(
                code="date_anomaly",
                message=f"账号 {item.account} 的预计打款日期 {item.expected_payment_date} 早于申请日期 {advance_date}",
                source="advance",
                accounts=[item.account],
            ))
        if not item.payer:
            issues.append(Issue(
                code="missing_field",
                message=f"账号 {item.account} 缺少打款人",
                source="advance",
                accounts=[item.account],
            ))

    seen: dict[tuple[str, str, int], int] = defaultdict(int)
    for item in advance_records:
        seen[(item.account, item.song, item.advance_amount)] += 1
    for (account, song, amount), count in seen.items():
        if count > 1:
            issues.append(Issue(
                code="duplicate_application",
                message=f"账号 {account} 的歌曲 {song} 存在 {count} 条相同垫付申请（{amount} 元）",
                source="advance",
                accounts=[account],
            ))
    return issues


def validate_unmatched_accounts(
    doujia_records: list[DoujiaRecord],
    advance_records: list[AdvanceRecord],
    template_accounts: set[str],
) -> list[Issue]:
    if not template_accounts:
        return []

    issues: list[Issue] = []
    seen: set[str] = set()
    for item in [*doujia_records, *advance_records]:
        if item.account in seen or item.account in template_accounts:
            seen.add(item.account)
            continue
        seen.add(item.account)
        issues.append(Issue(
            code="unmatched_account",
            message=f"账号 {item.account} 在推广账号表中未找到，需人工核对",
            source="template",
            accounts=[item.account],
        ))
    return issues
