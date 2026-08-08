# Specification: RSS Intelligence System Optimization & Hardening (GitHub Actions Optimized)

## 1. Objective
Refactor and optimize the `rss-intelligence` automated pipeline specifically for **GitHub Actions stateless CI/CD environments**. 

Key Shift based on Infrastructure Constraints:
- Retain the **Git-friendly JSON file format** (`history.json`) for seamless Git-commit state persistence across Actions runs.
- Solve the 21.6MB memory/disk bloat by eliminating **Article Content Hoarding** (2588 unprocessed entries currently storing full HTML body in JSON).
- Reduce `history.json` payload by **99% (from 21.6MB to < 200KB)** without adding database binaries to Git.

---

## 2. Infrastructure & Environment
- **Execution Platform**: GitHub Actions Cron / Manual Trigger
- **State Persistence**: Git commit & push of `history.json` back to repository
- **Runtime**: Python 3.10+
- **Core Dependencies**: `asyncio`, `aiohttp`, `google-genai`

---

## 3. Core Architectural Modules

```
┌─────────────────────────────────────────────────────────┐
│              GitHub Actions Stateless Runner            │
└────────────────────────────┬────────────────────────────┘
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
        ┌──────────────────┐  ┌───────────────────┐
        │  RSS Manager     │  │ Intelligence Hub  │
        │  (Slim In-Memory)│  │ (genai.aio)       │
        └─────────┬────────┘  └─────────┬─────────┘
                  │                     │
                  └──────────┬──────────┘
                             ▼
     ┌───────────────────────────────────────────────┐
     │  Slim JSON Storage Ledger (<200KB)             │
     │  - Processed: {hash: timestamp}               │
     │  - Pending Queue: max 50 entries (no HTML)    │
     └───────────────────────┬───────────────────────┘
                             │
                             ▼
            ┌──────────────────────────────────┐
            │ Git Commit & Push (history.json) │
            └──────────────────────────────────┘
```

### Module 1: JSON Payload Slimming & Queue Pruning (GitOps Friendly)
- **Target File**: [src/parser.py](file:///Users/kexin2050/rss-intelligence/src/parser.py#L9)
- **Design Requirement**:
  - **No Heavy Content Storage**: When a new RSS entry is fetched, do NOT store full HTML `content` inside `history.json`. Store only essential lightweight metadata: `{hash, link, title, ts, source}`.
  - **Pending Queue Throttling**: Cap the pending unprocessed queue length (e.g. max 50 recent articles). Drop older un-processed items beyond the window to prevent backlog accumulation due to Gemini API daily quota limits.
  - **Processed Entry Minimization**: Once processed, shrink the entry in JSON to `hash: {ts: timestamp, processed: true}` (or compact flat dict), discarding all metadata.
  - **Target Payload Size**: < 200 KB for 30-day retention window (Git diff friendly).

### Module 2: Strict Exception Boundaries & State Protection
- **Target File**: [src/parser.py](file:///Users/kexin2050/rss-intelligence/src/parser.py#L18)
- **Design Requirement**:
  - Eliminate bare `except:` statements completely.
  - Catch explicit exceptions (`json.JSONDecodeError`, `OSError`).
  - Safe Fallback: If `history.json` is corrupted, backup damaged file (`history.json.bak`) and log warning instead of silently returning an empty dict `{}` that would trigger immediate API quota exhaustion.

### Module 3: Thread-Isolated Mail & Async Security
- **Target Files**: [src/notifier.py](file:///Users/kexin2050/rss-intelligence/src/notifier.py#L7), [src/parser.py](file:///Users/kexin2050/rss-intelligence/src/parser.py#L122)
- **Design Requirement**:
  - Wrap synchronous `smtplib.SMTP` calls in `asyncio.to_thread` to ensure zero blocking on main event loop.
  - Re-enable SSL verification in `_fetch_one` (`ssl=True`). Provide configuration option for specific feed certificate bypasses.

### Module 4: Native Async Gemini Client
- **Target File**: [src/ai_hub.py](file:///Users/kexin2050/rss-intelligence/src/ai_hub.py#L6)
- **Design Requirement**:
  - Upgrade to `await self.client.aio.models.generate_content(...)`.
  - Isolate worker state and concurrency control cleanly.

### Module 5: Safe HTML Escaping for Telegram Notifications
- **Target File**: [src/notifier.py](file:///Users/kexin2050/rss-intelligence/src/notifier.py#L82)
- **Design Requirement**:
  - Apply `html.escape` on dynamic titles, sources, and summaries to prevent unclosed tag malformation errors (`400 Bad Request`) on Telegram.

---

## 4. Success Criteria & Verification

| Dimension | Success Criteria | Verification Method |
| :--- | :--- | :--- |
| **Git & JSON Size** | `history.json` file size reduced from **21.6MB to < 200KB** | Run script & inspect `ls -lh history.json` |
| **CI/CD Compatibility** | Clean Git diffs; zero binary conflicts in GitHub Actions | Inspect git diff output |
| **Resilience** | JSON syntax errors produce backup & abort safely without clearing state | Unit test with malformed JSON |
| **Async Performance** | All unit tests in `pytest` pass cleanly with zero main thread freezes | `.venv/bin/pytest` |
