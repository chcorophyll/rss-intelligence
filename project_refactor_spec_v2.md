# RSS Intelligence Optimization Specification V2 / 代码重构与优化技术规范 (Spec V2)

> **Version / 版本**: v2.0  
> **Basis / 依据**: `code_review_20260808.md`  
> **Goal / 目标**: Enhance persistence safety, introduce typed domain models, standardize logging, and strengthen concurrency resilience. / 提升持久化安全性、建立强类型模型、规范日志监控并强化并发容错。

---

## 1. Atomic Persistence & Queue Safety Spec / 持久化安全规范

### 1.1 Atomic File I/O Contract / 原子性落盘契约
- **Requirement / 强制机制**: Direct `open(filepath, 'w')` for `history.json` is strictly forbidden.
- **Protocol / 规范标准**:
  1. Write serialized JSON payload into a temporary file (`history.json.tmp`) in the same directory.
  2. Invoke `file.flush()` and `os.fsync()` to flush content to physical disk.
  3. Perform `os.replace(tmp_path, final_path)` for POSIX-guaranteed atomic file replacement.

### 1.2 Pending Queue Overflow Prevention / 历史队列容量硬防爆
- **Retention Limit / 队列上限**: Maintain up to 1000 processed hashes in `history.json`. Enforce a strict `Max 50` hard limit on the pending backlog queue, discarding stale items by timestamp.

---

## 2. Typed Domain Model Contract / 领域模型与强类型契约

### 2.1 Domain Data Model / 数据结构标准
Replace untyped `dict` payloads across modules with `@dataclass Article` in `src/models.py`:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Article:
    title: str
    link: str
    source: str
    content: str = ""
    hash: str = ""
    ai_html: Optional[str] = None
```

### 2.2 Pipeline Contract / 管道流转契约
- **Parser Stage / Parser 阶段**: Emits `list[Article]` instances.
- **AI Hub Stage / AI Hub 阶段**: Consumes `list[Article]` and populates `ai_html` in place or returns updated instances.
- **Notifier Stage / Notifier 阶段**: Reads strongly-typed properties from `Article` objects without dict key access.

---

## 3. Standard Logging & Observability Spec / 标准日志与监控体系规范

### 3.1 Prohibition of Bare `print()` / 废除 `print` 机制
- **Zero-Print Rule / 零 print 禁令**: Bare `print()` statements are prohibited in production source (`src/*.py`, `main.py`).
- **Unified Logger Factory / 统一 Logger 工厂**: Configure `rss_logger` in `src/utils/logger.py`:
  - Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`

### 3.2 Log Level Conventions / 异常分类日志规范
- **ERROR**: Network outages, SMTP auth failures, Telegram API non-200 errors (`logger.exception()`).
- **WARNING**: Gemini 429 quota exhaustion, schema fallback events.
- **INFO**: Fetch completion metrics, notification delivery counts.

---

## 4. Task Cancellation & 429 Resilience Spec / 任务调度与 429 快速取消规范

### 4.1 Quota Exhaustion Cascade Cancel / 429 额度耗尽级联取消
- When an AI Hub worker encounters a `429 RESOURCE_EXHAUSTED` error:
  1. Trigger `self.quota_exhausted_event.set()`.
  2. Immediately cancel (`task.cancel()`) remaining pending or running asyncio worker tasks.
  3. Return partial results instantly without hanging on quota limits.

---

## 5. HTML Sanitization Spec / HTML 工具库抽离与清洗规范

### 5.1 Shared Utility `src/utils/html_cleaner.py` / 共享清洗模块
- Consolidate `BeautifulSoup` dependencies into `src/utils/html_cleaner.py`:
  - `clean_to_text(raw_html: str) -> str`: Extracts plain text for AI processing.
  - `sanitize_telegram_html(raw_html: str) -> str`: Rebuilds Telegram-compliant HTML tags safely without fragile regexes.
