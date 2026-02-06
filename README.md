# 🤖 RSS Intelligence Bot

RSS Intelligence Bot 是一款遵循“极简主义”哲学设计的全自动情报获取与知识内化系统。它能够并发抓取 RSS/OPML 订阅源，利用 Google Gemini AI 进行语义压缩与跨语言对齐，并通过邮件及 Telegram 为您定时交付深度总结。

---

## ✨ 核心特性

- **高性能异步架构 (V2)**：基于 `asyncio` 与 `Semaphore` 的双层控制，分别在资源调度与 AI 调用中实现精准并发管理。
- **智能语义压缩**：集成最新 Gemini 2.0 Flash (Lite) 模型，自动过滤网页杂质，产出“三句要点总结 + 分段中英对照”的高质量内容。
- **状态感知历史管理**：支持“待处理文章”持久化。即使 AI 配额耗尽，未处理的文章也会在历史中保留，并在下次运行时优先处理。
- **多渠道交付**：支持 **SMTP 邮件** 与 **Telegram Bot** 双渠道推送，确保情报实时触达。
- **自平衡 TTL 逻辑**：内置 Time-To-Live 逻辑，自动剔除过时记录，确保 `history.json` 始终轻量高效，同时优化存储空间。
- **零成本运维**：全流程适配 GitHub Actions 自动化流水线，配合 `uv` 的极速依赖管理，实现零成本、高可靠的 7x24 小时监控。

---

## 📂 目录结构

```text
rss-intelligence/
├── .github/workflows/
│   └── rss_bot.yml       # GitHub Actions 自动化流水线配置
├── config/
│   └── config.ini        # 非敏感运行配置（并发控制、TTL、模型参数、通知开关）
├── src/                  # 核心模块代码目录
│   ├── ai_hub.py         # AI 处理核心逻辑（Gemini SDK 封装）
│   ├── notifier.py       # 通知渠道聚合（Email & Telegram 发送逻辑）
│   └── parser.py         # RSS 解析、网络请求、V2 历史管理
├── tests/                # 自动化测试套件
│   ├── test_ai_hub.py    # AI 并发与配额异常处理测试
│   ├── test_notifier.py  # 邮件/Telegram 模板与发送测试
│   ├── test_parser.py    # V1->V2 历史迁移、TTL 逻辑测试
│   └── test_telegram_manual.py # Telegram 功能性手动验证脚本
├── reports/              # 测试报告输出目录
├── main.py               # 生产环境入口：全量全自动调度
├── debug_workflow.py     # 调试环境入口：支持单 RSS 地址定向调试
├── pyproject.toml        # 项目元数据、依赖管理（uv 驱动）
└── README.md             # 本文档
```

---

## 🛠️ 快速开始

### 1. 环境准备

确保您的本地环境已安装高性能包管理工具 `uv`：

```bash
# macOS/Linux 安装命令
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 订阅配置

在项目根目录下放置您的订阅源：

- **方式 A (推荐)**：导出阅读器的 `subscriptions.opml` 文件。
- **方式 B**：创建 `feeds.txt`，每行填写一个 RSS URL (需符合 parser.py 逻辑)。

### 3. 本地测试

1. 开启秘钥（本地测试环境）：
   ```bash
   export GEMINI_API_KEY="您的_Gemini_Key"
   # 邮件配置
   export SMTP_PASSWORD="您的邮箱应用专用密码(授权码)"
   export SENDER_EMAIL="您的发件邮箱"
   export RECEIVER_EMAIL="您的收件邮箱"
   # Telegram 配置
   export TELEGRAM_BOT_TOKEN="您的_Telegram_Bot_Token"
   export TELEGRAM_CHAT_ID="您的_Telegram_Chat_ID"
   ```

2. 同步依赖并启动：
   ```bash
   uv sync
   uv run main.py
   ```

---

## 🔍 测试与调试

### 单步调试 (推荐)

如果您发现某个网址无法抓取或 AI 处理异常，可以使用单步调试工具：
```bash
uv run debug_workflow.py
```

### 🤖 Telegram 机器人验证

在正式运行前，可以使用脚本验证 Telegram 机器人配置是否正确：
```bash
uv run tests/test_telegram_manual.py
```

---

## 🚀 云端部署 (GitHub Actions)

1. **私有仓库**：将本项目推送到您的 GitHub Private Repository。
2. **配置加密秘钥**：在仓库设置 `Settings -> Secrets and variables -> Actions` 中添加：
   - `GEMINI_API_KEY`: Google AI Studio 申请的 API 密钥。
   - `SENDER_EMAIL`: 用于发送邮件的邮箱。
   - `SMTP_PASSWORD`: 邮箱生成的 App Password (授权码)。
   - `RECEIVER_EMAIL`: 接收情报的邮箱。
   - `TELEGRAM_BOT_TOKEN`: (可选) Telegram 机器人 Token。
   - `TELEGRAM_CHAT_ID`: (可选) 您的 Telegram 聊天 ID。
3. **开启 GitHub Actions 写入权限**：在 **Workflow permissions** 处勾选 **"Read and write permissions"**。
4. **手动触发测试**：在 Actions 标签页手动运行一次 `RSS Intelligence Daily`。

---

## ⚙️ 详细配置说明 (`config/config.ini`)

| 模块 | 配置项 | 说明 | 默认值 |
| :--- | :--- | :--- | :--- |
| **SYSTEM** | `MaxConcurrency` | 最大网络并发连接数 | `10` |
| | `RetentionDays` | 历史记录在 JSON 中保留的天数 | `30` |
| **AI** | `ModelName` | 使用的 Gemini 模型版本 | `gemini-2.5-flash-lite...` |
| | `RequestDelay` | 两次 AI 请求间的间隔（秒） | `4` |
| **SMTP** | `Server` | 发件服务器 SMTP 地址 | `smtp.qq.com` |
| | `Port` | 发件服务器端口 | `465` |
| **TELEGRAM** | `Enabled` | 是否启用 Telegram 通知 | `true` |

---

## ⚖️ 许可证

本项目基于 **MIT License** 开源。仅供个人学习、研究情报及效率提升使用。