# 推广申请处理 Agent

> 自动处理「抖加申请」与「垫付申请」，核对金额与异常，生成推广账号表测试副本；**有异常时转人工负责人，系统不会自动放行。**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-web_app-green.svg)](web_app.py)

---

## 目录

- [项目背景](#项目背景)
- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [项目结构](#项目结构)
- [环境要求与安装](#环境要求与安装)
- [快速开始（网页演示）](#快速开始网页演示)
- [命令行使用](#命令行使用)
- [演示视频与示例数据](#演示视频与示例数据)
- [异常类型说明](#异常类型说明)
- [人工确认流程](#人工确认流程)
- [Excel 模板要求](#excel-模板要求)
- [配置说明](#配置说明)
- [输出文件说明](#输出文件说明)
- [测试](#测试)
- [大模型边界（后续规划）](#大模型边界后续规划)
- [常见问题](#常见问题)
- [交付物](#交付物)

---

## 项目背景

推广运营每天会收到两类汇总文本：

1. **抖加申请总结** — 哪些博主投了抖加、金额多少、谁付的  
2. **垫付申请总结** — 哪些达人需要垫付、金额、打款人与日期  

人工核对容易漏项、算错、账号名对不上。本项目用 **规则引擎 + 结构化输出** 自动完成：

- 字段抽取 → 金额/笔数/日期校验 → 写入推广账号表**测试副本**  
- 发现异常 → 生成**人工确认单**，指派负责人，**不自动通过**

当前 MVP **不依赖大模型 API**，本地即可完整演示。

---

## 功能特性

| 模块 | 能力 |
|---|---|
| 文本抽取 | 从抖加/垫付文本提取账号、金额、支付人、打款日期 |
| 规则校验 | 总额、笔数、日期、重复申请、账号是否在表中 |
| Excel 副本 | 只读原表，按「抖音昵称」匹配写入，原表不被修改 |
| 人工确认 | 有异常 → 人工确认单 + 指派负责人 + Excel 备注「待人工确认」 |
| 网页演示 | 粘贴文本 → 一键处理 → 下载结果 / 复制确认单 |
| 企业微信（可选） | 配置 Webhook 后可推送（当前演示可不启用） |

---

## 系统架构

```text
┌─────────────────────────────────────────────────────────┐
│  输入：抖加申请文本 + 垫付申请文本                        │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  抽取层  extractor.py                                    │
│  · 正则解析账号、金额、日期（后续可换大模型 fallback）     │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  规则层  validator.py                                    │
│  · 声明总额 vs 明细合计                                   │
│  · 声明笔数 vs 识别条数                                   │
│  · 日期异常、重复申请、未匹配账号                          │
└────────────────────────┬────────────────────────────────┘
                         ↓
                   有异常？
              ┌───────┴───────┐
             是               否
              ↓                ↓
┌─────────────────────┐  ┌─────────────────────┐
│ human_review.py     │  │ 常规抽查流程         │
│ · 人工确认单        │  │ · 负责人汇报         │
│ · 指派负责人        │  │ · 测试表副本         │
│ · 不自动放行        │  └─────────────────────┘
└──────────┬──────────┘
           ↓
┌─────────────────────────────────────────────────────────┐
│  输出层  excel_writer.py + report.py                     │
│  · 推广账号表_测试副本.xlsx                               │
│  · 负责人汇报.md / 人工确认单.md / 处理结果.json          │
└─────────────────────────────────────────────────────────┘
```

**设计原则：规则发现问题，负责人做最终决定；AI 不能代替人工放行。**

---

## 项目结构

```text
promotion-agent/
│
├── README.md                 # 本文件（项目总说明）
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量示例（企业微信 Webhook 等）
├── .gitignore
│
├── main.py                   # 命令行入口 + 内置 demo
├── web_app.py                # FastAPI 网页服务
├── extractor.py              # 文本抽取
├── validator.py              # 规则校验
├── human_review.py           # 异常 → 人工确认
├── excel_writer.py           # Excel 测试副本写入
├── report.py                 # 负责人汇报生成
├── processor.py              # 结果组装
├── models.py                 # 数据模型
├── wecom.py                  # 企业微信推送（可选）
│
├── config/
│   ├── responsible.json      # 负责人配置（演示用）
│   └── responsible.json.example
│
├── data/
│   └── promotion_accounts_template.xlsx   # 推广账号表模板（只读）
│
├── demos/                    # ★ 演示视频 + 示例文本放这里
│   ├── demo-A-笔数与日期异常.mp4
│   ├── demo-B-正常版本.mp4          # 可选：无异常对照
│   ├── sample-A-doujia.txt
│   ├── sample-A-advance.txt
│   ├── sample-C-doujia.txt          # 账号名不匹配示例
│   └── sample-C-advance.txt
│
├── docs/
│   └── 实现说明.md            # 设计取舍、已修正的问题、验证方式
│
└── tests/
    ├── conftest.py
    ├── test_promotion_agent.py
    └── test_human_review.py
```

### 哪些文件夹「看起来乱」但可以忽略？

| 类型 | 文件夹 | 说明 |
|---|---|---|
| 运行产生 | `web_output/`、`output/` | 每次处理自动生成，已在 `.gitignore` 忽略，可随时删除 |
| Python 缓存 | `__pycache__/`、`.pytest_cache/` | 自动产生，不必提交 |

根目录放核心 `.py` 是 **有意保持扁平**，方便快速定位核心逻辑，不是结构错误。

---

## 环境要求与安装

- **Python** 3.10 或以上  
- **pip** 包管理器  
- **Excel / WPS**（查看输出的 `.xlsx`，不要用 VS Code 打开）

```powershell
cd C:\Users\裴瑾洁\Desktop\MyProjects\promotion-agent
pip install -r requirements.txt
```

依赖：`fastapi`、`uvicorn`、`pydantic`、`openpyxl`、`pytest`

---

## 快速开始（网页演示）

### 1. 启动服务

```powershell
python -m uvicorn web_app:app --reload
```

### 2. 打开浏览器

http://127.0.0.1:8000

### 3. 粘贴示例并处理

1. 打开 `demos/sample-A-doujia.txt` → 粘贴到左侧「抖加申请」  
2. 打开 `demos/sample-A-advance.txt` → 粘贴到右侧「垫付申请」  
3. 点击 **「开始处理」**

### 4. 查看结果

- 顶部汇总：抖加/垫付合计、明细条数  
- 有异常时：黄色 **「已转人工确认」** 横幅  
- **人工确认单**：可复制或下载  
- **推广账号表测试副本**：用 Excel 打开，异常行备注为「待人工确认」

---

## 命令行使用

内置 demo（与网页「加载示例」相同数据）：

```powershell
python main.py --demo --template data/promotion_accounts_template.xlsx --output output_test
```

指定自己的文本文件：

```powershell
python main.py ^
  --doujia demos/sample-A-doujia.txt ^
  --advance demos/sample-A-advance.txt ^
  --template data/promotion_accounts_template.xlsx ^
  --output output_test
```

输出目录 `output_test/`：

| 文件 | 说明 |
|---|---|
| `review.md` | 负责人汇报 |
| `人工确认单.md` | 有异常时生成 |
| `summary.json` | 结构化 JSON |
| `promotion_accounts_checked.xlsx` | 测试表副本 |

---

## 演示视频与示例数据

### 视频放哪里？

**路径：** `promotion-agent/demos/`

| 文件（当前已有） | 内容 |
|---|---|
| `demo-A-笔数与日期异常.mp4` | 示例 A：笔数不一致 + 日期异常 → 转人工 |
| `demo-B-正常版本.mp4` | 无异常对照（可选展示） |

若补充录制示例 C（账号名不匹配），建议命名：`demo-C-账号名不匹配.mp4`

> **GitHub 提示：** 单个文件建议小于 100MB。`demo-A` 约 90MB，接近上限；若推送失败，可压缩视频或在 README 里放网盘链接。

### 推荐演示组合：示例 A + 示例 C

| 示例 | 错误类型 | 预期结果 |
|---|---|---|
| **A** | 笔数 / 日期对不上 | 「已转人工确认」；声明 7 笔实际 5 条；打款日早于申请日 |
| **C** | 账号名写错 | 「渠工」vs 表里「泵工」→ `unmatched_account` |

- **A 不是单纯「金额算错」**，而是流程/笔数/日期规则不通过。  
- **C 是主数据匹配问题**，和金额无关。

配套文本：`demos/sample-A-*.txt`、`demos/sample-C-*.txt`

---

## 异常类型说明

| 代码 | 含义 | 示例 |
|---|---|---|
| `declared_total_mismatch` | 声明总额 ≠ 明细合计 | 声明 500，明细加总 350 |
| `declared_count_mismatch` | 声明笔数 ≠ 识别条数 | 声明 7 笔，识别 5 条 |
| `date_anomaly` | 预计打款日期早于申请日期 | 申请 9/3，打款 8/31 |
| `duplicate_application` | 同账号同歌曲同金额重复 | 两条完全相同的垫付 |
| `missing_field` | 缺少必要字段 | 无打款人、无日期等 |
| `unmatched_account` | 文本账号在 Excel 中不存在 | 渠工 vs 泵工 |

任一异常触发 → **人工确认**，系统结论为「暂不视为最终确认结果」。

---

## 人工确认流程

```text
规则发现异常
    ↓
生成《人工确认单》（human_review.py）
    ↓
指派 config/responsible.json 中的负责人
    ↓
网页：复制确认单 / 下载 .md → 手动发给负责人
    ↓
负责人核对 Excel 测试副本（备注「待人工确认」）
    ↓
确认无误 → 进入正式业务流程
驳回     → 联系提交人修正
```

**系统不会自动标记「已通过」。**

---

## Excel 模板要求

文件位置：`data/promotion_accounts_template.xlsx`（**只读，程序不会修改**）

必需列（表头行可不在第 1 行，程序会自动查找）：

| 列名 | 用途 |
|---|---|
| 抖音昵称 | 与文本中博主名/达人名匹配 |
| 抖加 | 写入抖加金额 |
| 抖加支付人 | 写入支付人 |
| 打款人 | 写入垫付打款人 |
| 打款日期 | 写入预计打款日期 |
| 备注（可选） | 异常账号写入「待人工确认」 |

**注意：** 文本里的名称必须与「抖音昵称」**完全一致**（差一个字就无法匹配）。

---

## 配置说明

### 负责人 `config/responsible.json`

```json
{
  "default": {
    "name": "林老师",
    "role": "推广负责人",
    "mobile": "",
    "wecom_userid": ""
  }
}
```

- `name`：人工确认单上显示的负责人  
- `mobile` / `wecom_userid`：可选，配置企业微信 Webhook 后用于 @ 提醒  

### 企业微信（可选，演示可不配）

```powershell
$env:WECOM_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key"
python wecom.py   # 测试连通
```

未配置时，页面提示：**手动将人工确认单发给负责人**。

---

## 输出文件说明

网页每次处理在 `web_output/<12位编号>/` 生成（该目录可随时删除）：

| 文件 | 何时生成 |
|---|---|
| `负责人汇报.md` | 每次都有 |
| `人工确认单.md` | **仅有异常时** |
| `处理结果.json` | 每次都有 |
| `推广账号表_测试副本.xlsx` | 模板存在且写入成功时 |

---

## 测试

```powershell
python -m pytest -q
```

覆盖：文本抽取、规则校验、人工确认单生成、未匹配账号等。

---

## 大模型边界（后续规划）

| 适合大模型 | 必须用代码 |
|---|---|
| 非固定格式文本抽取 | 金额加总、总额/笔数核对 |
| 汇报文案润色 | 日期/重复异常判定 |
| 账号模糊匹配候选 | 写 Excel、业务放行裁决 |

接入 DeepSeek / 阿里云时，**只替换 `extractor.py` 抽取层**，校验与人工确认逻辑不变。

---

## 常见问题

**Q：Excel 在 VS Code 里打开是乱码？**  
A：`.xlsx` 是二进制，请用 Excel 或 WPS 打开。

**Q：为什么没有「下载测试副本」？**  
A：检查 `data/promotion_accounts_template.xlsx` 是否存在且表头列齐全。

**Q：账号明明有，为什么没写入？**  
A：名称必须完全一致，例如「唐山第一女渠工」≠「唐山第一女泵工」。

**Q：文件夹里多了 web_output、__pycache__？**  
A：正常运行产生，可删除；Git 已忽略。

---

## 交付物

| 材料 | 位置 |
|---|---|
| 可运行代码 + 网页 | 本仓库 |
| 演示视频 | `demos/*.mp4` |
| 示例文本 | `demos/sample-*.txt` |
| 实现说明（设计取舍、已修正问题、验证方式） | [docs/实现说明.md](./docs/实现说明.md) |

### 演示路径

1. 启动网页，跑 **示例 A** → 观察「已转人工确认」
2. （可选）跑 **示例 C** → 观察账号名不匹配的处理方式
3. 下载 Excel 副本，查看「备注」列中的待确认标记
4. 阅读 `human_review.py` 或 `validator.py`：规则负责发现问题，最终是否放行由负责人决定

---

## 作者

GitHub: [ginny-pjj](https://github.com/ginny-pjj)
