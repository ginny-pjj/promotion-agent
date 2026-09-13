from main import DEMO_ADVANCE, DEMO_DOUJIA
from extractor import parse_advance, parse_doujia
from validator import validate


def test_demo_doujia_is_extracted_and_total_is_checked():
    current_date, declared_total, payer, records = parse_doujia(DEMO_DOUJIA)
    assert str(current_date) == "2026-09-02"
    assert declared_total == 700
    assert payer == "爆火音乐"
    assert len(records) == 4
    assert sum(item.doujia_amount for item in records) == 700


def test_demo_advance_flags_count_total_and_date_anomalies():
    current_date, declared_total, declared_count, records = parse_advance(DEMO_ADVANCE)
    assert str(current_date) == "2026-09-03"
    assert declared_total == 2250
    assert declared_count == 7
    assert len(records) == 5
    issues = validate(
        None,
        None,
        [],
        current_date,
        declared_total,
        declared_count,
        records,
    )
    codes = [issue.code for issue in issues]
    assert codes.count("declared_count_mismatch") == 1
    assert codes.count("date_anomaly") == 5
