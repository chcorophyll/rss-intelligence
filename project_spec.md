# Specification: Autonomous Bilingual RSS Intelligence System

## 1. Project Goal
Build an automated pipeline that:
1. Parses RSS/OPML feeds concurrently.
2. Filters new content using a self-cleaning local database.
3. Generates bilingual summaries via Gemini AI.
4. Delivers an HTML newsletter via Email.
5. Manages configuration through external files.

## 2. File Structure
- `main.py`: The orchestrated entry point.
- `config.ini`: Non-sensitive settings (Concurrency, TTL, SMTP Server).
- `.env`: Sensitive secrets (Gemini Key, Email Passwords) - *Not committed to Git*.
- `subscriptions.opml` or `feeds.txt`: Source list.
- `history.json`: State persistence.

## 3. Technical Requirements
- **Configuration:** Use `configparser` for `config.ini` and `os.getenv` for secrets.
- **Concurrency:** `asyncio.Semaphore` (default: 10) for network throttling.
- **AI Processing:** Gemini 1.5 Flash with sequential processing (4s delay) to respect Rate Limits.
- **Cleanup:** 30-day TTL (Time-To-Live) for `history.json` entries.
- **Email:** Responsive HTML format with Markdown-to-HTML conversion.

## 4. Automation Flow
1. Load `config.ini` and environment variables.
2. Async fetch all feeds from OPML/TXT.
3. Filter new items via MD5 hashing.
4. Sequence-process new items through Gemini.
5. Send aggregated HTML email.
6. Clean and save `history.json`.