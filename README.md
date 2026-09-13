# 推广申请处理 Agent

处理每日「抖加申请」与「垫付申请」文本，自动核对金额与异常，写入推广账号表测试副本；发现异常时转人工确认，不自动放行。

仓库地址：https://github.com/ginny-pjj/promotion-agent

---

## 演示

**演示视频**（仓库 `demos/` 目录）：

- [示例 A：笔数与日期异常 → 转人工确认](./demos/demo-A-笔数与日期异常.mp4)
- [示例 B：无异常的正常流程](./demos/demo-B-正常版本.mp4)

**本地运行：**

```powershell
pip install -r requirements.txt
python -m uvicorn web_app:app --reload
```

浏览器打开 http://127.0.0.1:8000 ，将 `demos/sample-A-doujia.txt` 与 `demos/sample-A-advance.txt` 粘贴到对应输入框，点击「开始处理」。

---

## 项目说明

### 输入与输出

| 输入 | 说明 |
|---|---|
| 抖加申请总结 | 博主、金额、支付人等 |
| 垫付申请总结 | 达人、金额、打款人、预计打款日期等 |
| 推广账号表 | Excel 主表，用于账号匹配与结果写入 |

| 输出 | 说明 |
|---|---|
| 负责人汇报 | 金额汇总、明细条数、异常清单、处理结论 |
| 推广账号表测试副本 | 在原表结构上填入当天数据，原表不被修改 |
| 人工确认单 | 存在异常时生成，指派负责人处理 |

### 处理流程

```text
抖加文本 + 垫付文本
        ↓
字段抽取（extractor）
        ↓
规则校验（validator）
        ↓
有异常 → 人工确认单 + Excel 备注「待人工确认」
无异常 → 负责人汇报 + 测试表副本
```

金额核对、笔数校验、日期与重复检测由代码完成；系统只发现问题与整理结果，最终是否放行由负责人决定。

---

## 项目结构

```text
promotion-agent/
├── web_app.py / main.py      # 网页与命令行入口
├── extractor.py              # 文本抽取
├── validator.py              # 规则校验
├── human_review.py           # 人工确认
├── excel_writer.py           # Excel 副本写入
├── report.py / processor.py / models.py
├── wecom.py                  # 企业微信推送（可选）
├── config/                   # 负责人配置
├── data/                     # 推广账号表模板
├── demos/                    # 演示视频与示例文本
├── docs/实现说明.md          # 设计说明与问题记录
└── tests/                    # 单元测试
```

---

## 使用说明

### 网页

```powershell
python -m uvicorn web_app:app --reload
```

### 命令行

```powershell
python main.py --demo --template data/promotion_accounts_template.xlsx --output output_test
```

### 负责人配置

编辑 `config/responsible.json` 中的 `name`，用于人工确认单指派。

### Excel 模板

模板路径：`data/promotion_accounts_template.xlsx`（只读）。

需包含列：抖音昵称、抖加、抖加支付人、打款人、打款日期；备注列可选。  
「预计打款日期」不会写入「打款日期」列，而是记入备注，避免与实付日期混淆。

### 输出

网页处理结果写在 `web_output/<处理编号>/`：

| 文件 | 说明 |
|---|---|
| 负责人汇报.md | 汇总与结论 |
| 人工确认单.md | 有异常时生成 |
| 处理结果.json | 结构化结果 |
| 推广账号表_测试副本.xlsx | 填写后的测试表 |

---

## 异常与人工确认

| 类型 | 说明 |
|---|---|
| 声明总额与明细合计不一致 | 金额核对失败 |
| 声明笔数与识别条数不一致 | 如声明 7 笔、实际 5 条 |
| 预计打款日期早于申请日期 | 日期异常 |
| 重复申请 | 同账号同歌曲同金额出现多次 |
| 缺少必要字段 | 如缺打款人、缺日期 |
| 账号未匹配 | 文本昵称与表中「抖音昵称」不一致 |

触发后：生成人工确认单、Excel 相关行备注「待人工确认」，处理结论为暂不视为最终确认结果。

---

## 测试

```powershell
python -m pytest -q
```

---

## 后续规划

- 企业微信自建应用：处理完成后将汇报与确认单推送给指定负责人  
- 文本格式不固定时，可在抽取层接入大模型；金额校验与放行逻辑仍由代码负责  

更完整的设计取舍与开发中修正的问题，见 [docs/实现说明.md](./docs/实现说明.md)。
