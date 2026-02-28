# TG Monitor Upgrade Progress

## Current Objective
Working on Phase 1 from `TODO.md`: Link Aggregation Engine Deepening (深度解析与智能分类).

## Tasks

### Phase 2: 🧠 全局知识库化与 RAG 问答式检索
- [x] **群聊语料的 Embedding 向量化**: Integrated ChromaDB `chromadb` via `pip`. Created `src/rag.py` to index messages intelligently. Modified `summarizer.py` to upsert messages array when producing daily recaps.
- [x] **智囊问答接口 (RAG Chat API)**: Enabled `/api/chat/ask` API Endpoint to handle frontend Q&A via `gpt-4o`. Automatically maps found citations as well.
- [x] **问答对话面板 (RAG Chatbot UI)**: Developed fully-featured `Chatbot.tsx` simulating a ChatGPT flow, with reference links mapping directly to original telegram group contexts formatted beautifully.

### Phase 3: 面向多端订阅的 SaaS 化重构 (UserBot Multi-tenant)
**状态**: ✅ 完成
**成果**:
- **数据库隔离**: 修改 `src/db/core.py` (MIGRATION v6)，引入 `tenants` 表，所有核心表 (`messages`, `groups`, `links`, `summaries`, `summary_jobs`) 挂载 `tenant_id` 外键。新增 `TenantsDAO` (`src/db/tenants.py`) 负责租户表读写。
- **并发工作池**: 新增 `SessionPool` (`src/session_pool.py`) 和对应的 CLI 命令 `python -m src.cli pool-start`，从数据库读取租户记录，利用异步任务和隔离的 SQLiteSession 进行多账号并行接管，互不干扰！
- **登录管理大盘 (Auth Portal)**: 在 Web Dashboard 新增了 `/api/tenants` 系列端点；在前端 `App.tsx` 加入了「账号管理 (TenantsPage)」页面，通过界面能够发起 `send_code_request`、接收验证码、完成 `sign_in` 并动态挂载至监控任务！
- **无缝结合**: 之前修改的 RAG, Summary 也能兼容这种并发池，系统正式步入多用户体系的平台形态。

### Phase 1: 🔗 链接聚合引擎深化 (深度解析与智能分类)
- [x] **Meta Parser (网页元数据抓取)**: Asynchronously fetch `<title>`, `<meta description>`, and images for links (in `src/db/messages.py`). Handled User-Agent and added async queue to prevent blocking the message stream.

... (Phase 1 tasks below)

## Issues Encountered & Resolved
- **ChromaDB C/C++ compilation overhead**: Solved by making `chromadb` optional (`try...except ImportError`) and warning the user instead of outright application crashes upon load. Handled seamless fallback.
- `react-hooks/set-state-in-effect` rule violation in `StatCards.tsx` leading to cascading renders or infinite loops. **Fix**: Added logical guard `if (count !== targetValue)` and proper `eslint-disable-next-line` directive where the intentional direct target sync is needed.
- SQLite concurrent write issues while testing API changes. **Fix**: Evaluated that `core.py` properly sets `PRAGMA busy_timeout=60000` and `PRAGMA journal_mode=WAL`, making writes less prone to `database is locked` issues.
- Missing `target="_blank"` and `loading="lazy"` on new `<img />` tags which may impact frontend performance. **Fix**: Added `loading="lazy"` and structured `<a ... rel="noopener noreferrer">`.

## Achievements
- Successfully built an AI metadata pipeline connected seamlessly into `MessagesDAO` insertion without blocking core Telethon collection.
- Enriched `/api/links` returning cleanly grouped `LinkItem`s containing occurrences of `total_count` and unified text, making data substantially tidier for rendering on the front-end.
- Constructed a complete local RAG search system mapping Telegram chat history over time to an interactive Chat interface with live sources.
