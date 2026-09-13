from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from excel_writer import load_template_accounts, update_workbook
from extractor import parse_advance, parse_doujia
from main import DEMO_ADVANCE, DEMO_DOUJIA
from processor import build_result
from human_review import build_human_review_dispatch
from report import render_report
from validator import validate, validate_unmatched_accounts
from wecom import notify_process_result

BASE_DIR = Path(__file__).parent
TEMPLATE_PATH = BASE_DIR / "data" / "promotion_accounts_template.xlsx"
OUTPUT_DIR = BASE_DIR / "web_output"

app = FastAPI(title="推广申请处理 Agent")


class ProcessRequest(BaseModel):
    doujia_text: str = Field(..., min_length=1)
    advance_text: str = Field(..., min_length=1)


def process_texts(doujia_text: str, advance_text: str):
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
    if TEMPLATE_PATH.exists():
        issues.extend(
            validate_unmatched_accounts(
                doujia_records,
                advance_records,
                load_template_accounts(TEMPLATE_PATH),
            )
        )
    return build_result(
        doujia_date,
        doujia_total,
        doujia_records,
        advance_date,
        advance_total,
        advance_count,
        advance_records,
        issues,
    )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML_PAGE


@app.post("/api/process")
def process(request: ProcessRequest):
    result = process_texts(request.doujia_text, request.advance_text)
    job_id = uuid.uuid4().hex[:12]
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    report = render_report(result)
    report_path = job_dir / "负责人汇报.md"
    json_path = job_dir / "处理结果.json"
    report_path.write_text(report, encoding="utf-8")
    json_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    workbook_url = None
    workbook_error = None
    workbook_path = job_dir / "推广账号表_测试副本.xlsx"
    if TEMPLATE_PATH.exists():
        try:
            update_workbook(
                TEMPLATE_PATH,
                workbook_path,
                result.doujia_records,
                result.advance_records,
                result.issues,
            )
            workbook_url = f"/api/download/{job_id}/推广账号表_测试副本.xlsx"
        except ValueError as exc:
            workbook_error = str(exc)
    else:
        workbook_error = "尚未配置推广账号表模板，请管理员将原始表复制为 data/promotion_accounts_template.xlsx"

    human_review = build_human_review_dispatch(result, job_id)
    human_review_url = None
    if human_review.required:
        human_review_path = job_dir / "人工确认单.md"
        human_review_path.write_text(human_review.notice, encoding="utf-8")
        human_review_url = f"/api/download/{job_id}/人工确认单.md"
        notify_status = human_review.delivery
    else:
        notify_status = notify_process_result(
            report,
            job_id,
            workbook_path if workbook_url else None,
        )

    return {
        "job_id": job_id,
        "summary": result.model_dump(mode="json"),
        "report": report,
        "report_url": f"/api/download/{job_id}/负责人汇报.md",
        "json_url": f"/api/download/{job_id}/处理结果.json",
        "workbook_url": workbook_url,
        "workbook_error": workbook_error,
        "human_review": human_review.model_dump(mode="json"),
        "human_review_url": human_review_url,
        "notify_status": notify_status,
    }


@app.post("/api/demo")
def demo():
    return process(ProcessRequest(doujia_text=DEMO_DOUJIA, advance_text=DEMO_ADVANCE))


@app.get("/api/download/{job_id}/{filename}")
def download(job_id: str, filename: str):
    allowed = {"负责人汇报.md", "处理结果.json", "推广账号表_测试副本.xlsx", "人工确认单.md"}
    if not job_id.isalnum() or filename not in allowed:
        raise HTTPException(status_code=400, detail="无效的下载地址")
    path = OUTPUT_DIR / job_id / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path, filename=filename)


HTML_PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>推广申请处理 Agent</title>
<style>
:root{font-family:Inter,"Microsoft YaHei",sans-serif;color:#172033;background:#f4f7fb}*{box-sizing:border-box}body{margin:0}.wrap{max-width:1100px;margin:0 auto;padding:42px 22px}.hero{margin-bottom:24px}.eyebrow{color:#2878f0;font-weight:700;letter-spacing:.08em}.hero h1{font-size:34px;margin:8px 0}.hero p{color:#667085}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card{background:#fff;border:1px solid #e5eaf2;border-radius:16px;padding:20px;box-shadow:0 8px 26px #1b355d0d}.card h2{font-size:18px;margin:0 0 12px}textarea{width:100%;min-height:230px;border:1px solid #d7deea;border-radius:10px;padding:13px;resize:vertical;font:14px/1.7 inherit}button{border:0;border-radius:10px;background:#246bdb;color:#fff;padding:12px 22px;font-size:15px;font-weight:700;cursor:pointer}button.secondary{background:#eaf1ff;color:#246bdb}.actions{display:flex;gap:12px;margin:18px 0;flex-wrap:wrap}.hidden{display:none}.metrics{display:flex;gap:12px;flex-wrap:wrap}.metric{background:#f7f9fc;border-radius:10px;padding:14px 18px;min-width:150px}.metric b{display:block;font-size:24px;margin-top:5px}.issue{background:#fff5f2;border-left:4px solid #e34d35;padding:10px 12px;margin:8px 0;border-radius:6px}.warn{background:#fff8eb;border:1px solid #f0c96a;border-radius:12px;padding:16px;margin:0 0 16px}.ok{background:#effaf3;border-left:4px solid #28a56a;padding:12px}.downloads a{display:inline-block;margin:6px 10px 0 0;color:#246bdb}.status{color:#667085;margin-left:8px}@media(max-width:760px){.grid{grid-template-columns:1fr}}
</style></head>
<body><main class="wrap"><section class="hero"><div class="eyebrow">PROMOTION OPS</div><h1>推广申请处理 Agent</h1><p>粘贴当天的抖加申请和垫付申请，自动核对金额、识别异常，并生成测试表副本。</p></section>
<section class="grid"><div class="card"><h2>抖加申请内容</h2><textarea id="doujia" placeholder="粘贴抖加申请总结"></textarea></div><div class="card"><h2>垫付申请内容</h2><textarea id="advance" placeholder="粘贴付款（垫付）申请总结"></textarea></div></section>
<div class="actions"><button onclick="processData()">开始处理</button><button class="secondary" onclick="loadDemo()">加载示例</button><span class="status" id="status"></span></div>
<section id="result" class="card hidden"><h2>处理结果</h2><div id="human-banner"></div><div id="metrics" class="metrics"></div><h3>人工确认清单</h3><div id="issues"></div><h3 id="human-title" class="hidden">人工确认单（发给负责人）</h3><pre id="human-notice" class="hidden" style="white-space:pre-wrap;line-height:1.6;background:#fff8eb;padding:14px;border-radius:10px"></pre><h3>负责人汇报</h3><pre id="report" style="white-space:pre-wrap;line-height:1.6"></pre><div class="downloads" id="downloads"></div></section></main>
<script>
let latest;
async function call(url,body){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok)throw new Error(await r.text());return r.json()}
function render(data){latest=data;const s=data.summary;const hr=data.human_review||{};document.getElementById('result').classList.remove('hidden');document.getElementById('metrics').innerHTML=`<div class="metric">抖加明细合计<b>¥${s.totals.doujia_detail_total}</b></div><div class="metric">垫付明细合计<b>¥${s.totals.advance_detail_total}</b></div><div class="metric">抖加明细<b>${s.doujia_records.length} 条</b></div><div class="metric">垫付明细<b>${s.advance_records.length} 条</b></div>`;document.getElementById('issues').innerHTML=s.issues.length?s.issues.map(x=>`<div class="issue">${x.message}</div>`).join(''):'<div class="ok">规则校验通过，可进入人工抽查。</div>';const needsReview=hr.required;document.getElementById('human-banner').innerHTML=needsReview?`<div class="warn"><b>已转人工确认</b><br>指派给：${hr.assignee.name}（${hr.assignee.role}）<br>共 ${hr.issue_count} 项异常，系统未自动放行，请负责人处理。</div>`:'<div class="ok">未发现异常，可按常规流程进入负责人抽查。</div>';const humanTitle=document.getElementById('human-title');const humanNotice=document.getElementById('human-notice');if(needsReview){humanTitle.classList.remove('hidden');humanNotice.classList.remove('hidden');humanNotice.textContent=hr.notice||''}else{humanTitle.classList.add('hidden');humanNotice.classList.add('hidden');humanNotice.textContent=''}document.getElementById('report').textContent=data.report;const notify=data.notify_status||{};const notifyHtml=notify.channel==='manual'?`<div class="warn">${notify.message}</div>`:notify.channel==='wecom'?(notify.ok?`<div class="ok">${notify.message}</div>`:`<div class="issue">${notify.message}</div>`):notify.channel==='none'?`<div class="status">${notify.message||''}</div>`:`<div class="status">${notify.message||'未配置自动推送'}</div>`;document.getElementById('downloads').innerHTML=notifyHtml+(needsReview?`<button class="secondary" onclick="copyHumanNotice()">复制人工确认单</button>`:'')+(needsReview&&data.human_review_url?`<a href="${data.human_review_url}" download>下载人工确认单</a>`:'')+`<a href="${data.report_url}" download>下载负责人汇报</a><a href="${data.json_url}" download>下载结构化结果</a>`+(data.workbook_url?`<a href="${data.workbook_url}" download>下载推广账号表测试副本</a>`:`<span class="status">${data.workbook_error}</span>`)}
function copyHumanNotice(){if(!latest||!latest.human_review||!latest.human_review.notice){alert('当前没有人工确认单');return}navigator.clipboard.writeText(latest.human_review.notice).then(()=>alert('人工确认单已复制，请发送给负责人')).catch(()=>alert('复制失败，请手动下载人工确认单'))}
async function processData(){const status=document.getElementById('status');status.textContent='处理中...';try{render(await call('/api/process',{doujia_text:document.getElementById('doujia').value,advance_text:document.getElementById('advance').value}));status.textContent='处理完成'}catch(e){status.textContent='处理失败：'+e.message}}
async function loadDemo(){const status=document.getElementById('status');status.textContent='加载中...';try{const d=await call('/api/demo',{});document.getElementById('doujia').value='示例已加载：点击开始处理即可查看完整流程';document.getElementById('advance').value='示例已加载：点击开始处理即可查看完整流程';render(d);status.textContent='示例处理完成'}catch(e){status.textContent='加载失败：'+e.message}}
</script></body></html>"""
