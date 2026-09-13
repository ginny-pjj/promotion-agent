# 推广申请处理 Agent MVP

这个 MVP 处理两类申请文本，并把结果写入推广账号表的副本：

- 抖加申请总结
- 付款（垫付）申请总结
- 推广账号表 Excel 模板

大模型适合做自然语言字段抽取；金额计算、缺失字段、数量矛盾、重复申请和日期检查由 Python 规则完成。

## 一、最快演示方式

进入目录并安装依赖：

```powershell
cd C:\Users\裴瑾洁\Desktop\MyProjects\WIFI-Autoglm-Mobile-Copilot\promotion-agent
pip install -r requirements.txt
```

运行内置样例：

```powershell
python main.py --demo
```

## 二、网页使用方式

先由管理员把公司提供的原始测试表复制到：

```text
data/promotion_accounts_template.xlsx
```

需要先创建 `data` 文件夹。不要把原始文件直接作为输出文件，程序只读取它并生成副本。

启动网页：

```powershell
python -m uvicorn web_app:app --reload
```

浏览器打开：

```text
http://127.0.0.1:8000
```

使用者每天只需要：

1. 粘贴当天的抖加申请总结
2. 粘贴当天的付款（垫付）申请总结
3. 点击“开始处理”
4. 在页面查看金额和人工确认清单
5. 复制负责人汇报内容到企业微信
6. 下载 `推广账号表_测试副本.xlsx`

网页不会修改 `data/promotion_accounts_template.xlsx`。每次处理都会在 `web_output/<处理编号>/` 中生成新的结果。

## 三、指定文件运行

不使用网页时，也可以直接传入文件：

```powershell
python main.py --doujia data/doujia.txt --advance data/advance.txt --template data/promotion_accounts_template.xlsx --output output
```

输出目录包含：

- `summary.json`：结构化处理结果
- `review.md`：负责人汇报和人工确认清单
- `promotion_accounts_checked.xlsx`：填写后的测试表副本

## 四、为什么需要测试表副本

推广账号表是业务结果的统一载体，负责人需要在原来的账号、报价、接单和审核信息旁边看到当天新增的抖加、抖加支付人、打款人和打款日期。它不是给大模型看的，也不是调用大模型的必需参数。

程序的安全流程是：

```text
原始推广账号表
    ↓ 只读加载
按账号匹配申请文本中的记录
    ↓
写入新的测试副本
    ↓
负责人检查副本，确认后再进入正式业务流程
```

当前 Excel 写入器会自动寻找包含“抖音昵称”和“抖加”的表头行，尽量适配截图中表头不在第一行的情况。真实 `.xlsx` 文件仍应在提交前实际测试。

## 五、当前版本边界

当前示例解析器支持题目截图中的文本格式，保证没有 API Key 时也能演示。后续若接入大模型，只替换抽取层；金额汇总、规则校验、Excel 副本和人工确认机制继续由代码负责。

## 六、异常转人工确认

当规则校验发现异常时，系统 **不会自动放行**，而是生成《人工确认单》并指派负责人处理。

### 负责人配置

编辑：

```text
config/responsible.json
```

示例：

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

把 `name` 改成实际负责人姓名。若以后接入企业微信，可填写 `mobile` 或 `wecom_userid` 用于 @负责人。

### 有异常时会怎样

1. 网页顶部显示 **「已转人工确认」**
2. 生成 `人工确认单.md`，可下载或一键复制
3. Excel 测试副本里，相关账号备注写 **「待人工确认」**
4. 若配置了企业微信 Webhook，会推送人工确认单；否则提示手动发给负责人

### 没有异常时

显示「可按常规流程进入负责人抽查」，不阻断流程。

## 七、企业微信群机器人推送（私网可用）

处理完成后，可自动把汇报和测试表副本推送到企业微信群。你的电脑只需要**能访问外网**，不需要公网 IP。

### 第一步：在企业微信里创建测试群

1. 打开 **企业微信** App（不是个人微信）
2. 底部点 **消息** → 右上角 **＋** → **发起群聊**
3. 至少选 1 个其他成员（同事、小号、家人有企业微信的账号都行）
4. 给群起名，例如「推广申请测试群」

> 群机器人只能加在 **企业微信群** 里，个人微信群里没有这个功能。

### 第二步：添加群机器人

1. 进入刚创建的群
2. 点右上角 **⋯** → **群机器人**（或 **添加群机器人**）
3. 点 **添加** → 给机器人起名，例如「推广申请助手」
4. 复制页面上的 **Webhook 地址**，格式类似：

```text
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

5. **妥善保存这个地址**，不要发到公开群或 GitHub

### 第三步：把 Webhook 配到项目里

在 VS Code 终端里（PowerShell）：

```powershell
cd C:\Users\裴瑾洁\Desktop\MyProjects\WIFI-Autoglm-Mobile-Copilot\promotion-agent
$env:WECOM_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key"
```

先测连通性：

```powershell
python wecom.py
```

企业微信群里应收到：**「推广申请 Agent 测试消息：企业微信 Webhook 已连通。」**

### 第四步：启动网页并处理

```powershell
python -m uvicorn web_app:app --reload
```

打开 `http://127.0.0.1:8000`，粘贴申请内容，点 **开始处理**。

成功后：
- 网页会显示「汇报和测试表副本已推送到企业微信群」
- 群里会收到 Markdown 汇报
- 若已配置 Excel 模板，还会收到 **推广账号表_测试副本.xlsx** 文件

### 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 群里没消息 | Webhook 没配对 / 终端关了变量丢失 | 重新设置 `$env:WECOM_WEBHOOK_URL` 后再跑 |
| 提示 invalid webhook url | key 复制不完整 | 重新复制完整 URL |
| 只有汇报没有 Excel | 模板文件缺失或生成失败 | 检查 `data/promotion_accounts_template.xlsx` |
| 个人微信看不到 | 机器人在企业微信 | 用企业微信 App 打开该群 |

### 安全提醒

- Webhook 地址相当于群里的「发消息密码」，泄露后别人也能往群里发消息
- 建议只用测试群，正式群单独建机器人
