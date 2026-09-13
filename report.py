from datetime import date

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


def render_report(result: ProcessingResult) -> str:
    issue_lines = "\n".join(f"- [{issue.code}] {issue.message}" for issue in result.issues)
    if not issue_lines:
        issue_lines = "- 无，数据可进入下一步人工抽查"
    return f"""# 推广申请处理汇报

## 汇总

| 项目 | 结果 |
|---|---:|
| 抖加明细合计 | ¥{result.totals['doujia_detail_total']} |
| 垫付明细合计 | ¥{result.totals['advance_detail_total']} |
| 抖加声明金额 | ¥{result.doujia_declared_total if result.doujia_declared_total is not None else '未知'} |
| 垫付声明金额 | ¥{result.advance_declared_total if result.advance_declared_total is not None else '未知'} |
| 抖加识别明细 | {len(result.doujia_records)} 条 |
| 垫付识别明细 | {len(result.advance_records)} 条 |

## 人工确认清单

{issue_lines}

## 处理结论

{"发现异常，相关记录暂不视为最终确认结果。" if result.issues else "规则校验通过，可进入人工抽查。"}
"""
