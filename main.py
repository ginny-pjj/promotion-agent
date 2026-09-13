import argparse
import json
from pathlib import Path

from excel_writer import load_template_accounts, update_workbook
from extractor import parse_advance, parse_doujia
from human_review import build_human_review_dispatch
from processor import build_result
from report import render_report
from validator import validate, validate_unmatched_accounts

DEMO_DOUJIA = """【抖加金额统计】今日已支付：￥700（2026-09-02）

明细如下：
歌名：《你是我的仰望》- 博主名：初秋 - 金额：￥300（分 3 笔）
歌名：《你是我的仰望》- 博主名：艳红 - 金额：￥200（分 2 笔）
歌名：《你是我的仰望》- 博主名：唐山第一女渠工 - 金额：￥100
歌名：《你是我的仰望》- 博主名：戎大姨 - 金额：￥100

今日共 7 笔支付申请，合并同博主后为 4 笔。

抖加支付人：爆火音乐
"""

DEMO_ADVANCE = """【垫付统计】今日已垫付：￥2250（2026-09-03）

明细如下：
申请为【达人：初秋】垫付 ￥950（歌曲《你是我的仰望》）
申请为【达人：艳红】垫付 ￥300（歌曲《你是我的仰望》）
申请为【达人：戎大姨】垫付 ￥300（歌曲《你是我的仰望》）
申请为【达人：高高】垫付 ￥200（歌曲《你是我的仰望》）
申请为【达人：葵花夫妇】垫付 ￥500（歌曲《你是我的仰望》）

今日共 7 笔垫付申请。

打款人：林老师
预计打款日期：26/08/31
"""


def read_input(path: str | None, demo: str) -> str:
    return Path(path).read_text(encoding="utf-8") if path else demo


def main() -> None:
    parser = argparse.ArgumentParser(description="推广申请处理 Agent MVP")
    parser.add_argument("--doujia")
    parser.add_argument("--advance")
    parser.add_argument("--template")
    parser.add_argument("--output", default="output")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    doujia_text = read_input(args.doujia, DEMO_DOUJIA)
    advance_text = read_input(args.advance, DEMO_ADVANCE)
    doujia_date, doujia_total, _, doujia_records = parse_doujia(doujia_text)
    advance_date, advance_total, advance_count, advance_records = parse_advance(advance_text)
    issues = validate(
        doujia_date,
        doujia_total,
        doujia_records,
        advance_date,
        advance_total,
        advance_count,
        advance_records,
    )
    if args.template and Path(args.template).exists():
        issues.extend(
            validate_unmatched_accounts(
                doujia_records,
                advance_records,
                load_template_accounts(Path(args.template)),
            )
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

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output / "review.md").write_text(render_report(result), encoding="utf-8")
    human_review = build_human_review_dispatch(result, output.name)
    if human_review.required:
        (output / "人工确认单.md").write_text(human_review.notice, encoding="utf-8")
    if args.template:
        update_workbook(
            Path(args.template),
            output / "promotion_accounts_checked.xlsx",
            doujia_records,
            advance_records,
            issues,
        )

    print(render_report(result))
    if human_review.required:
        print("\n" + human_review.notice)
        print(f"\n人工确认单已生成，请发送给负责人 {human_review.assignee.name}")
        print(human_review.delivery["message"])
    print(f"\n输出目录：{output.resolve()}")


if __name__ == "__main__":
    main()
