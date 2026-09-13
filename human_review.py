from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from models import Issue, ProcessingResult
from wecom import available as wecom_available
from wecom import send_text, send_text_with_mention


BASE_DIR = Path(__file__).parent
RESPONSIBLE_CONFIG = BASE_DIR / "config" / "responsible.json"


class ResponsiblePerson(BaseModel):
    name: str
    role: str = "推广负责人"
    mobile: str = ""
    wecom_userid: str = ""


class HumanReviewDispatch(BaseModel):
    required: bool
    status: Literal["needs_review", "auto_ok"]
    assignee: ResponsiblePerson
    issue_count: int = 0
    affected_accounts: list[str] = Field(default_factory=list)
    notice: str = ""
    delivery: dict[str, str | bool] = Field(default_factory=dict)


def load_responsible_person() -> ResponsiblePerson:
    if RESPONSIBLE_CONFIG.exists():
        data = json.loads(RESPONSIBLE_CONFIG.read_text(encoding="utf-8"))
        person = data.get("default") or data
        return ResponsiblePerson.model_validate(person)
    return ResponsiblePerson(name="推广负责人", role="推广负责人")


def collect_affected_accounts(issues: list[Issue]) -> list[str]:
    accounts: list[str] = []
    seen: set[str] = set()
    for issue in issues:
        for account in issue.accounts:
            if account and account not in seen:
                seen.add(account)
                accounts.append(account)
    return accounts


def render_human_review_notice(
    result: ProcessingResult,
    job_id: str,
    assignee: ResponsiblePerson,
) -> str:
    issue_lines = "\n".join(f"- [{issue.code}] {issue.message}" for issue in result.issues)
    accounts = collect_affected_accounts(result.issues)
    account_text = "、".join(accounts) if accounts else "见下方异常清单（含全局异常）"
    return f"""# 人工确认单

> 处理编号：{job_id}
> 状态：**待人工确认**（系统不会自动放行）

## 指派负责人

- 姓名：{assignee.name}
- 职责：{assignee.role}

## 待确认账号

{account_text}

## 异常清单（共 {len(result.issues)} 项）

{issue_lines}

## 负责人需要做什么

1. 核对上方异常是否属实
2. 打开测试表副本，检查备注为「待人工确认」的行
3. 确认无误后，再进入正式业务流程
4. 如有问题，请驳回并联系提交人修正

## 系统说明

- 以下结果 **不是最终确认结果**
- AI/规则只负责发现问题，**不能代替负责人做通过决定**
"""


def deliver_human_review(
    notice: str,
    assignee: ResponsiblePerson,
    issue_count: int,
) -> dict[str, str | bool]:
    summary = (
        f"【待人工确认】推广申请处理发现 {issue_count} 项异常，"
        f"请负责人 {assignee.name} 处理。系统未自动放行。"
    )
    if not wecom_available():
        return {
            "channel": "manual",
            "ok": True,
            "message": f"未配置企业微信，请手动将《人工确认单》发送给 {assignee.name}",
        }

    if assignee.mobile or assignee.wecom_userid:
        ok, msg = send_text_with_mention(
            summary + "\n\n" + notice[:1800],
            mentioned_mobile_list=[assignee.mobile] if assignee.mobile else [],
            mentioned_userid_list=[assignee.wecom_userid] if assignee.wecom_userid else [],
        )
    else:
        ok, msg = send_text(summary + "\n\n" + notice[:1800])

    if ok:
        return {
            "channel": "wecom",
            "ok": True,
            "message": f"人工确认单已推送给负责人 {assignee.name}",
        }
    return {
        "channel": "wecom",
        "ok": False,
        "message": f"人工确认单推送失败: {msg}，请手动发送给 {assignee.name}",
    }


def build_human_review_dispatch(result: ProcessingResult, job_id: str) -> HumanReviewDispatch:
    assignee = load_responsible_person()
    if not result.issues:
        return HumanReviewDispatch(
            required=False,
            status="auto_ok",
            assignee=assignee,
            notice="",
            delivery={
                "channel": "none",
                "ok": True,
                "message": "未发现异常，可按常规流程进入负责人抽查",
            },
        )

    notice = render_human_review_notice(result, job_id, assignee)
    delivery = deliver_human_review(notice, assignee, len(result.issues))
    return HumanReviewDispatch(
        required=True,
        status="needs_review",
        assignee=assignee,
        issue_count=len(result.issues),
        affected_accounts=collect_affected_accounts(result.issues),
        notice=notice,
        delivery=delivery,
    )
