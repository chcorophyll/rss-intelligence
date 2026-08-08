# RSS Intelligence Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor and optimize the `rss-intelligence` pipeline for GitHub Actions compatibility—slimming `history.json` by 99% (from 21.6MB to <200KB), securing SSL transport, ensuring exception safety, and eliminating main-thread blocking.

**Architecture:** Maintain a lightweight JSON storage ledger (`history.json`) optimized for Git-commit persistence in GitHub Actions. Strip HTML bodies from saved history, enforce queue caps, isolate synchronous `smtplib` via `asyncio.to_thread`, and adopt native `client.aio` for Gemini API calls.

**Tech Stack:** Python 3.10+, `asyncio`, `aiohttp`, `google-genai`, `pytest`, `pytest-asyncio`.

---

## Global Constraints

- **Python Floor**: Python 3.10+
- **Persistence Target**: `history.json` size < 200KB under 30-day retention
- **Test Runner**: `.venv/bin/pytest`
- **Zero Bare Excepts**: All `except:` must catch explicit exception types
- **Zero Global Thread Blocks**: Network/SMTP blocking calls isolated or async

---

## Plan Overview & Task Decomposition

```
Task 1: JSON Payload Slimming & Queue Pruning
        │ (Removes HTML body, caps pending queue at 50)
        ▼
Task 2: Exception Hardening & Corruption Fallback
        │ (Replaces bare excepts, adds backup on corrupted JSON)
        ▼
Task 3: Thread-Isolated Mail & SSL Security
        │ (asyncio.to_thread for SMTP, re-enables SSL)
        ▼
Task 4: Native Async Gemini API Integration
        │ (Switches to client.aio.models.generate_content)
        ▼
Task 5: Safe HTML Escaping for Telegram
        │ (Applies html.escape to title/source)
        ▼
Task 6: History Migration & Size Verification
        │ (Migrates existing 21.6MB history.json to slim schema)
        ▼
End: Full Test & Build Verification
```

---

### Task 1: JSON Payload Slimming & Queue Pruning

**Files:**
- Modify: [src/parser.py](file:///Users/kexin2050/rss-intelligence/src/parser.py:70-120)
- Test: [tests/test_parser.py](file:///Users/kexin2050/rss-intelligence/tests/test_parser.py)

**Interfaces:**
- Consumes: RSS feed entries from `feedparser`
- Produces: `RSSManager.fetch_all()` returning lightweight article data dicts without bloated JSON persistence

- [ ] **Step 1: Write failing test for slim history data storage**

Add test to `tests/test_parser.py`:
```python
@pytest.mark.asyncio
async def test_slim_history_payload(tmp_path):
    config = MagicMock()
    config.config.getint.side_effect = lambda sec, key, fallback=None: 30 if key == 'RetentionDays' else 10
    
    db_file = str(tmp_path / "test_history.json")
    manager = RSSManager(config, db=db_file)
    
    # Simulate adding an entry
    u_hash = "test_hash_1"
    manager.history[u_hash] = {
        "ts": time.time(),
        "processed": False,
        "data": {
            "title": "Test Title",
            "link": "https://example.com/test",
            "source": "Test Source",
            "hash": u_hash
            # NOTE: 'content' should NOT be stored long-term in history dict
        }
    }
    manager.save_and_clean()
    
    with open(db_file, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    assert u_hash in raw
    assert "content" not in raw[u_hash].get("data", {})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_parser.py::test_slim_history_payload -v`  
Expected: FAIL (because `content` is currently stored in `data`)

- [ ] **Step 3: Refactor `RSSManager.fetch_all` to exclude `content` from JSON history**

In [src/parser.py](file:///Users/kexin2050/rss-intelligence/src/parser.py#L80-L91):
Store only essential fields in `self.history[u_hash]['data']`: `title`, `link`, `source`, `hash`. Pass `content` in-memory only for active processing tasks. Enforce pending queue max size (50 items).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_parser.py::test_slim_history_payload -v`  
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/parser.py tests/test_parser.py
git commit -m "refactor(parser): slim history json payload by excluding html content"
```

---

### Task 2: Exception Hardening & Corruption Protection

**Files:**
- Modify: [src/parser.py](file:///Users/kexin2050/rss-intelligence/src/parser.py:18-35)
- Test: [tests/test_parser.py](file:///Users/kexin2050/rss-intelligence/tests/test_parser.py)

**Interfaces:**
- Consumes: Raw `history.json` on disk
- Produces: Robust `_load_history()` with explicit exception handling and corruption backup (`history.json.bak`)

- [ ] **Step 1: Write failing test for corrupted JSON backup protection**

Add test to `tests/test_parser.py`:
```python
def test_load_corrupted_history_creates_backup(tmp_path):
    config = MagicMock()
    config.config.getint.side_effect = lambda sec, key, fallback=None: 30 if key == 'RetentionDays' else 10
    
    db_file = tmp_path / "corrupted_history.json"
    db_file.write_text("INVALID JSON {{{", encoding="utf-8")
    
    manager = RSSManager(config, db=str(db_file))
    
    # Should create backup file and return empty dict without crashing
    assert (tmp_path / "corrupted_history.json.bak").exists()
    assert manager.history == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_parser.py::test_load_corrupted_history_creates_backup -v`  
Expected: FAIL (currently bare `except:` just returns `{}` without backup)

- [ ] **Step 3: Update `_load_history` with explicit exceptions & backup logic**

In [src/parser.py](file:///Users/kexin2050/rss-intelligence/src/parser.py#L18-L34):
Replace `except:` with `except (json.JSONDecodeError, OSError) as e:`. Rename corrupted file to `self.db + ".bak"` and log explicit warning.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_parser.py::test_load_corrupted_history_creates_backup -v`  
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/parser.py tests/test_parser.py
git commit -m "fix(parser): add explicit JSON exception handling and corrupted backup safety"
```

---

### Task 3: Thread-Isolated Mail Dispatch & SSL Transport Security

**Files:**
- Modify: [src/notifier.py](file:///Users/kexin2050/rss-intelligence/src/notifier.py:151-165), [src/parser.py](file:///Users/kexin2050/rss-intelligence/src/parser.py:127)
- Test: [tests/test_notifier.py](file:///Users/kexin2050/rss-intelligence/tests/test_notifier.py)

**Interfaces:**
- Consumes: Config and processed report data
- Produces: Async non-blocking `send_all_reports()` and secure RSS HTTP fetches

- [ ] **Step 1: Write failing test for thread-isolated SMTP sending**

Add test to `tests/test_notifier.py`:
```python
@pytest.mark.asyncio
async def test_send_all_reports_async_execution(mocker):
    cfg = MagicMock()
    cfg.config.getboolean.return_value = False
    
    mock_email = mocker.patch("src.notifier.EmailNotifier.send_report")
    await send_all_reports(cfg, [])
    
    mock_email.assert_called_once()
```

- [ ] **Step 2: Run test to verify it passes/fails baseline**

Run: `.venv/bin/pytest tests/test_notifier.py -v`

- [ ] **Step 3: Wrap `email_notifier.send_report` in `asyncio.to_thread` and re-enable SSL**

In [src/notifier.py](file:///Users/kexin2050/rss-intelligence/src/notifier.py#L156):
```python
await asyncio.to_thread(email_notifier.send_report, processed_articles, warning=warning)
```
In [src/parser.py](file:///Users/kexin2050/rss-intelligence/src/parser.py#L129):
Remove `ssl=False` default from `session.get()`, enabling SSL verification.

- [ ] **Step 4: Run all notifier tests to verify pass**

Run: `.venv/bin/pytest tests/test_notifier.py -v`  
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/notifier.py src/parser.py tests/test_notifier.py
git commit -m "fix(notifier): isolate synchronous SMTP via asyncio.to_thread and re-enable SSL verification"
```

---

### Task 4: Native Async Gemini Client Integration

**Files:**
- Modify: [src/ai_hub.py](file:///Users/kexin2050/rss-intelligence/src/ai_hub.py:70-80)
- Test: [tests/test_ai_hub.py](file:///Users/kexin2050/rss-intelligence/tests/test_ai_hub.py)

**Interfaces:**
- Consumes: Raw article list
- Produces: `(processed_articles, quota_exceeded)` using `self.client.aio`

- [ ] **Step 1: Write test verifying native async client method call**

In `tests/test_ai_hub.py`, update mock setup to mock `client.aio.models.generate_content`.

- [ ] **Step 2: Update `_process_one` in `IntelligenceHub`**

In [src/ai_hub.py](file:///Users/kexin2050/rss-intelligence/src/ai_hub.py#L71-L78):
Replace `loop.run_in_executor(...)` with:
```python
response = await self.client.aio.models.generate_content(
    model=self.model_name,
    contents=prompt
)
```

- [ ] **Step 3: Run AI Hub tests to verify pass**

Run: `.venv/bin/pytest tests/test_ai_hub.py -v`  
Expected: PASS

- [ ] **Step 4: Commit changes**

```bash
git add src/ai_hub.py tests/test_ai_hub.py
git commit -m "refactor(ai_hub): migrate to native client.aio.models.generate_content"
```

---

### Task 5: Telegram Safe HTML Escaping

**Files:**
- Modify: [src/notifier.py](file:///Users/kexin2050/rss-intelligence/src/notifier.py:108-120)
- Test: [tests/test_notifier.py](file:///Users/kexin2050/rss-intelligence/tests/test_notifier.py)

**Interfaces:**
- Consumes: Articles with un-escaped titles/sources
- Produces: Safe Telegram HTML strings free from unclosed `<` parsing errors

- [ ] **Step 1: Write failing test for Telegram HTML escaping with special characters**

Add test to `tests/test_notifier.py`:
```python
@pytest.mark.asyncio
async def test_telegram_html_escaping(mocker):
    cfg = MagicMock()
    cfg.TELEGRAM_BOT_TOKEN = "dummy"
    cfg.TELEGRAM_CHAT_ID = "123"
    
    mock_post = mocker.patch("aiohttp.ClientSession.post")
    notifier = TelegramNotifier(cfg)
    
    articles = [{
        "title": "AT&T <Test> & Danger",
        "link": "https://example.com",
        "source": "News <Source>",
        "ai_html": "<p>Summary text</p>"
    }]
    
    await notifier.send_report(articles)
    
    assert mock_post.called
    sent_payload = mock_post.call_args[1]["json"]
    text = sent_payload["text"]
    assert "AT&amp;T &lt;Test&gt; &amp; Danger" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_notifier.py::test_telegram_html_escaping -v`  
Expected: FAIL (because titles were not html-escaped)

- [ ] **Step 3: Apply `html.escape` to title & source in `TelegramNotifier.send_report`**

In [src/notifier.py](file:///Users/kexin2050/rss-intelligence/src/notifier.py#L115-L120):
Import `html` and wrap `html.escape(art['title'])` and `html.escape(art['source'])`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_notifier.py::test_telegram_html_escaping -v`  
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add src/notifier.py tests/test_notifier.py
git commit -m "fix(notifier): escape HTML entities in Telegram notification titles and sources"
```

---

### Task 6: Existing History Clean Migration

**Files:**
- Modify: [history.json](file:///Users/kexin2050/rss-intelligence/history.json)
- Script: Create temporary migration execution in `main.py` or one-off script

**Interfaces:**
- Consumes: Existing 21.6MB `history.json`
- Produces: Clean < 100KB `history.json` file

- [ ] **Step 1: Run one-off python script to purge `data` and prune stale pending records from `history.json`**

Execute:
```bash
.venv/bin/python -c "
import json, time
with open('history.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)

cutoff = time.time() - (30 * 24 * 3600)
cleaned = {}
for k, v in raw.items():
    if isinstance(v, (int, float)):
        if float(v) > cutoff:
            cleaned[k] = {'ts': float(v), 'processed': True}
    elif isinstance(v, dict):
        ts = v.get('ts', 0)
        if ts > cutoff:
            # Drop heavy data payload to slim JSON down
            cleaned[k] = {'ts': ts, 'processed': v.get('processed', True)}

with open('history.json', 'w', encoding='utf-8') as f:
    json.dump(cleaned, f, ensure_ascii=False, indent=2)
"
```

- [ ] **Step 2: Verify `history.json` file size**

Run: `ls -lh history.json`  
Expected Output: File size reduced to < 200KB (e.g., ~100KB).

- [ ] **Step 3: Run entire test suite**

Run: `.venv/bin/pytest`  
Expected: 100% tests PASS.

- [ ] **Step 4: Commit slimmed history.json**

```bash
git add history.json
git commit -m "chore(history): purge legacy content payloads and slim history.json for GitHub Actions"
```

---

## Execution Handoff

Plan complete and saved to `project_optimization_plan.md`. Two execution options:

1. **Subagent-Driven (recommended)** - Fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks sequentially in this session with verification checkpoints

Which approach would you like to take?
