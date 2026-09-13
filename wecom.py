from __future__ import annotations

import json
import mimetypes
import os
import uuid
import urllib.error
import urllib.request
from pathlib import Path


def webhook_url() -> str:
    return os.environ.get("WECOM_WEBHOOK_URL", "").strip()


def available() -> bool:
    return webhook_url().startswith("https://qyapi.weixin.qq.com/cgi-bin/webhook/")


def _webhook_key() -> str:
    url = webhook_url()
    if "key=" not in url:
        return ""
    return url.split("key=", 1)[1].split("&", 1)[0]


def _post_json(url: str, payload: dict) -> tuple[bool, str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        return False, str(exc)
    if body.get("errcode") == 0:
        return True, "ok"
    return False, body.get("errmsg", str(body))


def send_text(content: str) -> tuple[bool, str]:
    if not available():
        return False, "未配置 WECOM_WEBHOOK_URL"
    return _post_json(
        webhook_url(),
        {"msgtype": "text", "text": {"content": content[:2048]}},
    )


def send_text_with_mention(
    content: str,
    mentioned_mobile_list: list[str] | None = None,
    mentioned_userid_list: list[str] | None = None,
) -> tuple[bool, str]:
    if not available():
        return False, "未配置 WECOM_WEBHOOK_URL"
    text_payload: dict[str, object] = {"content": content[:2048]}
    mobiles = [item for item in (mentioned_mobile_list or []) if item]
    userids = [item for item in (mentioned_userid_list or []) if item]
    if mobiles:
        text_payload["mentioned_mobile_list"] = mobiles
    if userids:
        text_payload["mentioned_list"] = userids
    return _post_json(webhook_url(), {"msgtype": "text", "text": text_payload})


def send_markdown(content: str) -> tuple[bool, str]:
    if not available():
        return False, "未配置 WECOM_WEBHOOK_URL"
    return _post_json(
        webhook_url(),
        {"msgtype": "markdown", "markdown": {"content": content[:4096]}},
    )


def upload_file(file_path: Path) -> tuple[bool, str]:
    if not available():
        return False, "未配置 WECOM_WEBHOOK_URL"
    key = _webhook_key()
    if not key:
        return False, "Webhook 地址缺少 key 参数"

    file_path = Path(file_path)
    if not file_path.exists():
        return False, f"文件不存在: {file_path}"

    url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={key}&type=file"
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="media"; filename="{file_path.name}"\r\n'.encode(),
            f"Content-Type: {mime}\r\n\r\n".encode(),
            file_path.read_bytes(),
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        return False, str(exc)
    if payload.get("errcode") != 0:
        return False, payload.get("errmsg", str(payload))
    return True, payload["media_id"]


def send_file(file_path: Path) -> tuple[bool, str]:
    ok, media_id_or_error = upload_file(file_path)
    if not ok:
        return False, media_id_or_error
    return _post_json(
        webhook_url(),
        {"msgtype": "file", "file": {"media_id": media_id_or_error}},
    )


def build_markdown_report(report: str, job_id: str) -> str:
    lines = [
        "## 推广申请处理结果",
        f"> 处理编号：<font color=\"comment\">{job_id}</font>",
        "",
    ]
    for line in report.splitlines():
        if line.startswith("# "):
            continue
        if line.startswith("## 汇总"):
            lines.append("### 汇总")
            continue
        if line.startswith("## 人工确认清单"):
            lines.append("### 人工确认清单")
            continue
        if line.startswith("## 处理结论"):
            lines.append("### 处理结论")
            continue
        if line.startswith("|") or line.strip() == "|---|---:|":
            continue
        if line.startswith("- "):
            lines.append(line)
            continue
        if line.startswith("发现异常") or line.startswith("规则校验通过"):
            lines.append(f"**{line.strip()}**")
    return "\n".join(lines)[:4096]


def notify_process_result(
    report: str,
    job_id: str,
    workbook_path: Path | None = None,
) -> dict[str, str | bool]:
    if not available():
        return {"enabled": False, "message": "未配置 WECOM_WEBHOOK_URL，跳过企业微信推送"}

    markdown_ok, markdown_msg = send_markdown(build_markdown_report(report, job_id))
    if not markdown_ok:
        text_ok, text_msg = send_text(report[:2048])
        if not text_ok:
            return {
                "enabled": True,
                "ok": False,
                "message": f"汇报推送失败: {markdown_msg}; 文本兜底也失败: {text_msg}",
            }

    if workbook_path and Path(workbook_path).exists():
        file_ok, file_msg = send_file(Path(workbook_path))
        if not file_ok:
            return {
                "enabled": True,
                "ok": True,
                "message": f"汇报已推送，但 Excel 发送失败: {file_msg}",
            }
        return {"enabled": True, "ok": True, "message": "汇报和测试表副本已推送到企业微信群"}

    return {"enabled": True, "ok": True, "message": "汇报已推送到企业微信群"}


def main() -> None:
    ok, msg = send_text("推广申请 Agent 测试消息：企业微信 Webhook 已连通。")
    if ok:
        print("推送成功")
    else:
        print(f"推送失败: {msg}")


if __name__ == "__main__":
    main()
