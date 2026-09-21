# 🤖 RSS Intelligence Bot / RSS 智能情报局

[English]  
RSS Intelligence Bot is an automated intelligence retrieval and knowledge ingestion system designed around minimalist engineering principles. It concurrently fetches RSS/OPML feeds, compresses semantics and aligns cross-language insights using Google Gemini AI, and delivers daily executive briefs via Email (SMTP) and Telegram.

[中文]  
RSS Intelligence Bot 是一款遵循“极简主义”工程哲学设计的全自动情报获取与知识内化系统。它能够并发抓取 RSS/OPML 订阅源，利用 Google Gemini AI 进行语义压缩与跨语言对齐，并通过邮件及 Telegram 为您定时交付深度总结。

---

## ✨ Key Features / 核心特性

- **Atomic Persistence & File Safety / 持久化落盘与文件安全 (V2)**: 
  - *EN*: Employs POSIX-guaranteed atomic file I/O (`tempfile.NamedTemporaryFile` + `fsync` + `os.replace`) to eliminate file corruption risks during history saving.
  - *ZH*: 采用 POSIX 级原子落地机制（`tempfile.NamedTemporaryFile` + `fsync` + `os.replace`），彻底杜绝因意外中断导致 `history.json` 损坏的风险。
- **Backlog Overflow Prevention / 待处理队列硬防爆**: 
  - *EN*: Enforces a strict `Max 50` hard cap on pending items and retains up to 1000 processed records, preventing backlog inflation.
  - *ZH*: 对待处理队列设置 `Max 50` 篇硬上限，并最多保留 1000 条历史纪录，防止死链与超期文章无限积压。
- **Standardized Observability & Logging / 基础设施日志系统化**: 
  - *EN*: Replaces bare `print()` with a unified `rss_logger` singleton (`src/utils/logger.py`) featuring structured ISO timestamps and severity levels (`INFO`, `WARNING`, `ERROR`).
  - *ZH*: 全量引入单例日志服务（`src/utils/logger.py`），以结构化时间戳与日志级别 (`INFO`, `WARNING`, `ERROR`) 替代原生 `print()` 语句。
- **High-Performance Async Pipeline / 高性能异步架构**: 
  - *EN*: Leverages `asyncio` and `Semaphore` for fine-grained concurrency control across feed parsing, HTML fallback, and AI synthesis.
  - *ZH*: 基于 `asyncio` 与 `Semaphore` 的双层并发控制，分别在网络抓取、HTML 补偿与 AI 推理中实现精准资源管理。
- **Semantic Intelligence / 智能语义压缩**: 
  - *EN*: Powered by Google Gemini AI, generating concise 3-bullet summaries paired with bilingual English-Chinese key insight comparison tables.
  - *ZH*: 集成 Gemini AI 模型，自动过滤网页杂质，产出“三句要点速览 + 分段中英对照”的高质量情报战报。
- **Multi-Channel Delivery / 多渠道精准交付**: 
  - *EN*: Dual-channel delivery via SMTP Email and Telegram Bot with anti-rate-limit pacing.
  - *ZH*: 支持 SMTP 邮件与 Telegram Bot 双渠道稳定推送，保障情报按序无痛触达。
- **Zero-Maintenance Ops / 零成本自动化运维**: 
  - *EN*: 100% compatible with GitHub Actions workflows and `uv` dependency management for reliable, zero-cost 24/7 automated runs.
  - *ZH*: 全流程适配 GitHub Actions 自动化流水线，配合 `uv` 极速依赖管理，实现零成本、高可靠的 7x24 小时监控。

---

## 📂 Project Structure / 目录结构

```text
rss-intelligence/
├── .github/workflows/
│   └── rss_bot.yml       # GitHub Actions CI/CD workflow / 自动化流水线
├── config/
│   └── config.ini        # Application settings / 非敏感运行配置
├── src/                  # Core modules / 核心模块
│   ├── ai_hub.py         # Gemini AI hub & rate limit handler / AI 处理核心逻辑
│   ├── notifier.py       # Email & Telegram notification engines / 多渠道通知服务
│   ├── parser.py         # Feed fetching, atomic persistence & backlog control / RSS 抓取与原子历史管理
│   └── utils/            # Utilities / 基础工具
│       ├── __init__.py
│       └── logger.py     # Unified rss_logger singleton / 标准化日志系统
├── tests/                # Automated test suite / 自动化测试套件
│   ├── test_ai_hub.py    # AI concurrency & quota test cases / AI 并发与配额异常测试
│   ├── test_notifier.py  # Notification template & error handling / 邮件与 Telegram 推送测试
│   ├── test_parser.py    # Atomic write & pending backlog truncation tests / 原子落盘与队列防爆测试
│   └── test_telegram_manual.py # Manual Telegram verification script / Telegram 手动验证脚本
├── main.py               # Main execution entrypoint / 生产环境主入口
├── debug_workflow.py     # Single RSS debug entrypoint / 定向调试入口
├── pyproject.toml        # Dependency metadata (uv managed) / 依赖与配置元数据
└── README.md             # Project documentation (Bilingual) / 中英文双语文档
```

---

## 🛠️ Quick Start / 快速开始

### 1. Prerequisites / 环境准备

*EN*: Ensure `uv` is installed in your local environment:  
*ZH*: 确保您的本地环境已安装包管理工具 `uv`：

```bash
# macOS / Linux installation
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Subscription Setup / 订阅配置

*EN*: Place your subscription files in the root directory:  
*ZH*: 在项目根目录下配置您的订阅源：

- **Option A (Recommended / 推荐)**: Export `subscriptions.opml` from your RSS reader.
- **Option B**: Create `feeds.txt` with one RSS feed URL per line.

### 3. Local Execution / 本地运行与测试

1. **Configure Environment Variables / 配置环境变量**:
   ```bash
   export GEMINI_API_KEY="your_gemini_api_key"
   # Email Settings / 邮件配置
   export SMTP_PASSWORD="your_smtp_app_password"
   export SENDER_EMAIL="sender@example.com"
   export RECEIVER_EMAIL="receiver@example.com"
   # Telegram Settings (Optional) / Telegram 配置（可选）
   export TELEGRAM_BOT_TOKEN="your_bot_token"
   export TELEGRAM_CHAT_ID="your_chat_id"
   ```

2. **Sync Dependencies & Run / 同步依赖并启动**:
   ```bash
   uv sync
   uv run main.py
   ```

---

## 🔍 Testing & Verification / 测试与验证

*EN*: Run the full pytest suite to verify system integrity:  
*ZH*: 运行全量 pytest 自动化测试套件以验证系统完整性：

```bash
uv run pytest -v
```

---

## 🚀 Cloud Deployment / 云端部署 (GitHub Actions)

1. **Repository Setup / 仓库关联**: Push code to your private GitHub repository.
2. **Secrets Configuration / 配置密钥**: Navigate to `Settings -> Secrets and variables -> Actions`:
   - `GEMINI_API_KEY`: Google AI Studio API key.
   - `SENDER_EMAIL` & `SMTP_PASSWORD` & `RECEIVER_EMAIL`: Email parameters.
   - `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`: (Optional) Telegram bot keys.
3. **Workflow Permissions / 权限设置**: Under **Workflow permissions**, grant **"Read and write permissions"**.
4. **Trigger Execution / 手动触发**: Trigger `RSS Intelligence Daily` manually in the Actions tab.

---

## ⚙️ Configuration Reference / 详细配置项 (`config/config.ini`)

| Module / 模块 | Parameter / 配置项 | Description / 说明 | Default / 默认值 |
| :--- | :--- | :--- | :--- |
| **SYSTEM** | `MaxConcurrency` | Max network connection concurrency / 最大并发抓取数 | `10` |
| | `RetentionDays` | History retention window in days / 历史记录保留天数 | `30` |
| **AI** | `ModelName` | Gemini model identifier / Gemini AI 模型标志 | `gemini-flash-latest` |
| | `RequestDelay` | Pacing delay between requests (sec) / AI 请求间隔时间 | `4` |
| **SMTP** | `Server` | SMTP server endpoint / SMTP 发件服务器地址 | `smtp.qq.com` |
| | `Port` | SMTP SSL/TLS port / SMTP 端口 | `465` |
| **TELEGRAM** | `Enabled` | Toggle Telegram notifications / Telegram 推送开关 | `true` |

---

## ⚖️ License / 许可证

Distributed under the **MIT License**. For personal educational, intelligence retrieval, and research use.