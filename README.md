# TG Monitor 💬

**Telegram 群聊实时监控 & AI 智能汇总系统**

> **AI 助手阅读指南 (For AI Assistants & Developers):**
> 这是一个基于 Python (FastAPI/Telethon) + React (Vite/TailwindCSS) + SQLite 构建的全栈监控项目。
> 在对本仓库进行任何修改前，请务必完整阅读本 README 中关于项目结构、CPA(LLM) 代理链路以及启动逻辑的说明。

---

## 📈 项目架构解读

本系统分为四个核心组件，以及一个独立的高性能代理（CPA）：

1. **Collector (`src/collector.py`)**
   - **职责**: 基于 `Telethon` 运行的无头客户端。
   - **机制**: 登录用户的 Telegram 账号（`tg_monitor.session`），监听 `config.yaml` 中配置的指定 Target Groups，并将消息实时落盘。支持断线重连后的历史缺口自动拉取机制。
2. **Dashboard Backend (`src/dashboard.py`)**
   - **职责**: 提供前端数据支撑与 AI 摘要触发 API。
   - **堆栈**: `FastAPI` (Port Default: 8501)。
   - **核心接口**: `/api/overview`, `/api/groups`, `/api/recent_messages`, `/api/summary/generate`。
3. **Frontend UI (`frontend/`)**
   - **职责**: 面向用户的现代化监控面板。
   - **堆栈**: `React` + `Vite` + `TailwindCSS v4`。
   - **代理**: 在 `vite.config.ts` 中配置了对 `:8501/api` 的本地转发。
   - **构建**: 编译产物位于 `frontend/dist`，但在本地我们通常通过 `npm run dev` (Port: 2280) 运行热更新服务。
4. **Telegram Bot (`src/bot.py`)**
   - **职责**: 作为内联键盘机器人（Inline Keyboard Bot），向 `BOT_OWNER_ID` 推送警报和定时摘要（通过 `python-telegram-bot` 库实现）。
5. **CLI Proxy API (CPA)**
   - **说明点**: 这是一个由 Go 编写的极速代理服务，路径通常位于 `/opt/homebrew/opt/cliproxyapi/bin/cliproxyapi`。
   - **职责**: 负责聚合多个 `Codex/Claude/Gemini` 等厂商的 LLM API Keys 并提供统一的 OpenAI 兼容端点（`http://127.0.0.1:8317`）。
   - **配置**: 读取 `/opt/homebrew/etc/cliproxyapi.conf`，将请求自动均衡。TG Monitor 的 `src/summarizer.py` 会直接请求此本地端点以避免直连厂商带来的网络/封控问题。

---

## 📂 核心文件目录

```text
tg-monitor/
├── .env                  # 系统核心密文（TG_API_ID, BOT_TOKEN 都在此，严禁外传）
├── config.yaml           # 项目配置（包含受监控群组清单 groups, 以及基础代理端口）
├── TG Monitor 启动器.command # macOS 桌面一键启动脚本（核心流程串联者，包含守护进程与进程管理）
├── data/
│   └── tg_monitor.sqlite # 主数据库文件（WAL 模式 + FTS5），请注意数据库读写锁
├── frontend/             # 全新 React 端代码 (TypeScript)
│   ├── vite.config.ts    # 代理与端口配置 (port: 2280)
│   └── src/              # 组件化源码 (Sidebar, Topbar, GroupList 等)
└── src/
    ├── cli.py            # Click 命令行入口 (负责启动 dashboard/bot/collector)
    ├── collector.py      # Telethon 消息捕获模块
    ├── dashboard.py      # FastAPI 路由逻辑
    ├── database.py       # SQL DAO 层 (aiosqlite)
    ├── summarizer.py     # AI 摘要逻辑，负责调用本地 8317 端口
    └── bot.py            # Telegram Bot 交互
```

---

## 🚀 启动与部署说明

### 一键启动机制 (macOS 专属)

本项目高度依赖位于桌面的 **`TG Monitor 启动器.command`** 进行统一部署。
如果你（AI）需要调整启动参数，请**优先修改该 `.command` 文件**。

**它的标准唤起顺序如下：**
1. 校验、停止并重新拉起 **CPA 进程**，参数为 `-config /opt/homebrew/etc/cliproxyapi.conf`。
2. 通过 `.venv/bin/python` 后台启动 **Collector** (守护在 `data/tg_monitor.sqlite`)。
3. 通过 `.venv/bin/python` 后台启动 **Bot**。
4. 后台启动 **Dashboard Backend** (端口 `8501`)。
5. 进入 `frontend/` 目录运行 `npm run dev` 启动 **Vite** (端口 `2280`)。
6. 等待端口响应后，自动使用 `open` 唤起默认浏览器访问 `http://localhost:2280`。

*所有日志均会重定向至 `/tmp/` 目录：*
- `/tmp/cpa.log`
- `/tmp/tg_collector.log`
- `/tmp/tg_bot.log`
- `/tmp/tg_dashboard.log`
- `/tmp/tg_frontend.log`

### 手动调试命令

**1. 唤起后端 API**
```bash
cd /Users/admin/Desktop/chaos/tg-monitor
.venv/bin/python -m src.cli dashboard -p 8501
```

**2. 唤起 React 面板（热修）**
```bash
cd frontend
npm run dev
```
*(注意：如遇前端白屏，检查 `vite.config.ts` 中的 proxy 配置是否正确指向后端对应端口，以及 `App.tsx` 中的类型是否与 `/api/groups` payload 一致)*

---

## 🛡️ 已知采坑提示（给 AI）

1. **`Math.max` 的隐患**：在图表绘制（如 GroupList 的进度条）处理 `[].map` 时，必定要增加针对空数组的防护 (`groups.length > 0 ? ... : 1`)，否则 Vite 在 HMR 加载时会立刻抛出白屏崩溃。
2. **CPA 的 CLI 参数更迭**：系统上的 `cliproxyapi` 已为 v6.8.x，启动指定配置文件**必须**使用 `-config` 而非缩写的 `-c`。
3. **NPM 权限毒瘤**：该电脑的 `/Users/admin/.npm` 缓存所有权存在错乱，导致全局 `npm install` 极易报 `EACCES` 卡死。如需新增前端依赖，请切记使用项目目录下的 `.npmrc`（已配置为隔离缓存 `cache=.npm_cache`）。
4. **Typescript 与 Vite**：`frontend` 应用了 `verbatimModuleSyntax`。当从模块中引用 `Type` 时，请务必拆分 `import type { XX } from '...'`。
5. **AI 摘要长轮询**：点击“AI智能摘要”按钮，前端将向 `POST /api/summary/generate` 拿取一个 `task_id`，并使用 `/api/summary/status/{task_id}` 轮询进度更新和报错。摘要操作是在 Fastapi 的 `asyncio.create_task` 中后台运作的。

---
`TG_Monitor_Dev_Env_v2_React_Integrated`
