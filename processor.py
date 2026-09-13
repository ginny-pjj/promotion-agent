from models import ProcessingResult


def build_result(
    doujia_date,
    doujia_total,
    doujia_records,
    advance_date,
    advance_total,
    advance_count,
    advance_records,
    issues,
) -> ProcessingResult:
    return ProcessingResult(
        doujia_date=doujia_date,
        doujia_declared_total=doujia_total,
        doujia_records=doujia_records,
        advance_date=advance_date,
        advance_declared_total=advance_total,
        advance_declared_count=advance_count,
        advance_records=advance_records,
        issues=issues,
        totals={
            "doujia_detail_total": sum(item.doujia_amount for item in doujia_records),
            "advance_detail_total": sum(item.advance_amount for item in advance_records),
        },
    )
