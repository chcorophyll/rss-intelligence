# RSS Intelligence 重构与优化实施计划 (Plan V2)

> **版本**：v2.0  
> **依据**：`project_refactor_spec_v2.md`  
> **核心原则**：小步快跑、测试驱动、全量回归验证

---

## 阶段 1：基础设施与数据安全重构 (Infrastructure & Data Safety)

### Task 1.1: 基础设施日志系统化 (`logger.py`)
- [x] 创建 `src/utils/logger.py`，配置 `rss_logger` 单例（包含控制台 Handler 与标准日志格式）。
- [x] 全量替换 `main.py`, `src/parser.py`, `src/ai_hub.py`, `src/notifier.py` 中的 `print()` 为 `logger.info() / logger.warning() / logger.error()`。
- [x] 经验证：`python3 -c "from src.utils.logger import logger; logger.info('Test')"` 正常输出。

### Task 1.2: 持久化原子写入与队列控爆 (`save_history`)
- [x] 重构 `src/parser.py` 中的 `save_history`：使用 `tempfile.NamedTemporaryFile` + `os.replace` 实现原子文件写入。
- [x] 在 `save_and_clean` 中新增 pending 队列 `Max 50` 截断逻辑，防止死链堆积。
- [x] 经验证：编写单元测试模拟写入中断，确保 `history.json` 不损坏。

### Task 1.3: PEP 8 导包治理
- [x] 将 `src/parser.py` 中局部 `from bs4 import BeautifulSoup` 提升至文件头部。
- [x] 经验证：静态检查无 PEP 8 导包警告。

---

## 阶段 2：领域建模与 HTML 工具库抽取 (Domain Modeling & Utilities)

### Task 2.1: 强类型 `Article` 建模 (`models.py`)
- [ ] 创建 `src/models.py`，定义 `Article` 数据类（包含 `title`, `link`, `source`, `content`, `hash`, `ai_html`）。
- [ ] 重构 `src/parser.py`, `src/ai_hub.py`, `src/notifier.py` 的函数签名与数据流，全量收敛至 `Article` 对象。
- [ ] 经验证：数据流转过程具备强类型推断。

### Task 2.2: 抽离 `html_cleaner.py` 共享组件
- [ ] 创建 `src/utils/html_cleaner.py`，收拢 `bs4` 标签剥离逻辑。
- [ ] 提供 `clean_to_text()` 和 `sanitize_telegram_html()` 规范化函数。
- [ ] 经验证：Telegram 不再因非法 AI 标签产生 400 异常。

---

## 阶段 3：并发调度与 429 级联取消 (Scheduler & 429 Resilience)

### Task 3.1: AI Hub 429 任务快速取消
- [ ] 在 `src/ai_hub.py` 中加入 `quota_exhausted_event`。
- [ ] 当任一 Worker 触发 429 时，立刻 `cancel()` 其余仍挂载在 asyncio 队列上的 Tasks。
- [ ] 经验证：429 触发后剩余任务秒级取消，无无效挂起。

---

## 阶段 4：全量测试回归与交付 (Testing & Verification)

### Task 4.1: 测试用例全面重构与覆盖
- [ ] 更新 `tests/test_parser.py`, `tests/test_ai_hub.py`, `tests/test_notifier.py` 适配 `Article` 强类型。
- [ ] 运行 `./.venv/bin/pytest -v` 确保所有 26+ 项测试用例 **100% PASSED**。

### Task 4.2: Git 提交与发布
- [ ] 提交代码变更至 git，打上 `refactor(v2): complete architecture & safety refactoring` 标签。
