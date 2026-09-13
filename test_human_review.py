from human_review import build_human_review_dispatch, load_responsible_person
from main import DEMO_ADVANCE, DEMO_DOUJIA
from extractor import parse_advance, parse_doujia
from processor import build_result
from validator import validate


def test_human_review_is_required_when_issues_exist():
    doujia_date, doujia_total, _, doujia_records = parse_doujia(DEMO_DOUJIA)
    advance_date, advance_total, advance_count, advance_records = parse_advance(DEMO_ADVANCE)
    issues = validate(
        doujia_date,
        doujia_total,
        doujia_records,
        advance_date,
        advance_total,
        advance_count,
        advance_records,
    )
    result = build_result(
        doujia_date,
        doujia_total,
        doujia_records,
        advance_date,
        advance_total,
        advance_count,
        advance_records,
        issues,
    )
    dispatch = build_human_review_dispatch(result, "test-job")
    assert dispatch.required is True
    assert dispatch.status == "needs_review"
    assert dispatch.issue_count == len(issues)
    assert "待人工确认" in dispatch.notice
    assert dispatch.assignee.name == load_responsible_person().name
    assert dispatch.delivery["channel"] == "manual"


def test_human_review_not_required_when_clean():
    text = """【抖加金额统计】今日已支付：￥100（2026-09-20）

明细如下：
歌名：《测试》- 博主名：初秋 - 金额：￥100

今日共 1 笔支付申请，合并同博主后为 1 笔。

抖加支付人：爆火音乐
"""
    advance = """【垫付统计】今日已垫付：￥100（2026-09-20）

明细如下：
申请为【达人：初秋】垫付 ￥100（歌曲《测试》）

今日共 1 笔垫付申请。

打款人：林老师
预计打款日期：26/09/25
"""
    doujia_date, doujia_total, _, doujia_records = parse_doujia(text)
    advance_date, advance_total, advance_count, advance_records = parse_advance(advance)
    issues = validate(
        doujia_date,
        doujia_total,
        doujia_records,
        advance_date,
        advance_total,
        advance_count,
        advance_records,
    )
    result = build_result(
        doujia_date,
        doujia_total,
        doujia_records,
        advance_date,
        advance_total,
        advance_count,
        advance_records,
        issues,
    )
    dispatch = build_human_review_dispatch(result, "clean-job")
    assert dispatch.required is False
    assert dispatch.status == "auto_ok"


def test_unmatched_account_triggers_human_review():
    from models import AdvanceRecord
    from validator import validate_unmatched_accounts

    issues = validate_unmatched_accounts(
        [],
        [
            AdvanceRecord(
                account="不存在账号",
                advance_amount=100,
                song="测试",
                source_line="test",
            )
        ],
        {"初秋", "艳红"},
    )
    assert len(issues) == 1
    assert issues[0].code == "unmatched_account"
