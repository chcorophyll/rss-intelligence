# 🤖 RSS Intelligence Bot

RSS Intelligence Bot 是一款遵循“极简主义”哲学设计的全自动情报获取与知识内化系统。它能够并发抓取 RSS/OPML 订阅源，利用 Google Gemini AI 进行语义压缩与跨语言对齐，并通过邮件为您定时交付深度总结。

---

## ✨ 核心特性

- **高性能并发**：基于 `asyncio` 与 `Semaphore(10)`，在不冲击目标服务器的前提下实现极速抓取。
- **智能语义压缩**：集成 Gemini 2.5 Flash Lite，自动过滤网页杂质，产出“三句要点总结 + 分段中英对照”的高质量内容。
- **工业级状态管理**：内置 TTL (Time-To-Live) 逻辑，自动剔除 30 天前的过时记录，确保 `history.json` 永远轻量且高效。
- **零成本运维**：全流程适配 GitHub Actions 自动化流水线，无需购买 VPS 即可实现 7x24 小时监控。
- **配置分离**：采用 `uv` 锁定依赖版本，通过 `config.ini` 实现逻辑与运行参数的解耦。

---

## 📂 目录结构

```text
rss-intelligence/
├── .github/workflows/
│   └── rss_bot.yml      # GitHub Actions 自动化流水线配置
├── config/
│   └── config.ini       # 非敏感运行配置（并发控制、TTL、模型参数）
├── src/                 # 核心模块代码目录
├── main.py              # 统一入口文件，负责全流程调度
├── debug_workflow.py    # 单链路调试工具（调试单个 RSS 地址）
├── pyproject.toml       # 项目元数据及 uv 依赖定义
├── uv.lock              # 依赖版本精确锁定文件
├── .gitignore           # Git 忽略配置
└── README.md            # 项目说明文档
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
- **方式 B**：创建 `feeds.txt`，每行填写一个 RSS URL。

### 3. 本地测试

1. 开启秘钥（本地测试环境）：
   ```bash
   export GEMINI_API_KEY="您的_Gemini_Key"
   export SMTP_PASSWORD="您的邮箱应用专用密码(授权码)"
   export SENDER_EMAIL="您的发件邮箱"
   export RECEIVER_EMAIL="您的收件邮箱"
   ```

2. 同步依赖并启动：
   ```bash
   uv sync
   uv run main.py
   ```

### 🔍 单步调试 (推荐)

如果您发现某个网址无法抓取或 AI 处理异常，可以使用单步调试工具：

```bash
uv run debug_workflow.py
```
> [!TIP]
> 您可以直接在脚本中修改 `test_url` 来测试任意 RSS 地址。

---

## 🚀 云端部署 (GitHub Actions)

1. **私有仓库**：将本项目推送到您的 GitHub Private Repository。
2. **配置加密秘钥**：在仓库设置 `Settings -> Secrets and variables -> Actions` 中添加：
   - `GEMINI_API_KEY`: Google AI Studio 申请的 API 密钥。
   - `SENDER_EMAIL`: 用于发送邮件的邮箱。
   - `SMTP_PASSWORD`: 邮箱生成的 App Password (授权码)。
   - `RECEIVER_EMAIL`: 接收情报的邮箱。
3. **开启 GitHub Actions 写入权限**：
   - 路径：`Settings -> Actions -> General`。
   - 在 **Workflow permissions** 处勾选 **"Read and write permissions"**。这是为了让机器人能将更新后的 `history.json` 推送回仓库。
4. **手动触发测试**：在 Actions 标签页手动运行一次 `RSS Intelligence Daily`。

---

## ⚙️ 详细配置说明 (`config/config.ini`)

| 模块 | 配置项 | 说明 | 默认值 |
| :--- | :--- | :--- | :--- |
| **SYSTEM** | `MaxConcurrency` | 最大网络并发连接数 | `10` |
| | `RetentionDays` | 历史记录在 JSON 中保留的天数 | `30` |
| | `MaxArticlesPerRun` | 单次运行 AI 处理的最大文章数 | `5` |
| **AI** | `ModelName` | 使用的 Gemini 模型版本 | `gemini-2.5-flash-lite...` |
| | `RequestDelay` | 两次 AI 请求间的间隔（秒） | `4` |
| **SMTP** | `Server` | 发件服务器 SMTP 地址 | `smtp.qq.com` |
| | `Port` | 发件服务器端口 | `465` |

---

## ⚖️ 许可证

本项目基于 **MIT License** 开源。仅供个人学习、研究情报及效率提升使用。

---

## 📝 开发者备注

如果需要调整 AI 的总结风格（例如要求更硬核的技术分析或更感性的阅读摘录），请直接修改 `main.py` 中的 `IntelligenceHub.process_articles` 函数内的 prompt 内容。