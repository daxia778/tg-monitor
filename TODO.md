# TG Monitor - Future Roadmap & TODOs

> 记录针对项目核心能力扩写的高优先级目标，以为后续系统迭代（AI 问答、SaaS 化、高阶链接聚合）提供清晰的发展脉络与开发计划。

## 📍 核心演进方向

### Phase 1: 🔗 链接聚合引擎深化 (深度解析与智能分类)
当前系统已能准确实时提取群聊中的 URL。下一步的核心是将纯文本链接转化为高价值的情报元数据。

- [ ] **网页元数据抓取 (Meta Parser)**
  - 在 `src/db/messages.py` 中引入异步队列，剥离主聊天流程。
  - 使用 `BeautifulSoup` 或 `httpx` 轻量级获取链接的 `<title>`, `<meta description>` 以及主要封面图。
  - **难点规避**: 配置 User-Agent 伪装，对境外受限网站（Twitter/YouTube）设置超时跳过机制。
- [ ] **AI 智能标注与清洗 (Link Scorer)**
  - 将捕获并解析后的链接元数据，送入本地 CPA (LLM) 进行二次打标。
  - **标签化**: 识别该链接是否属于 "干货评测"、"促销/羊毛"、"文档资源" 抑或是 "无价值广告"。
  - **去重算法**: 基于 URL normalized_hash (去除各种追踪参数 `?utm_source=...`) 合并重复分享，统计"群内热度被分享次数"。
- [ ] **前端 UI 升级 (Rich Link Cards)**
  - 在 React 面板的 `LinksPage.tsx` 中，废弃传统的纯文本列表。
  - 设计类似 Twitter / Telegram Native 的富文本卡片瀑布流，支持按标签（如：🔥高热度、💰线报）快速过滤。

### Phase 2: 🧠 全局知识库化与 RAG 问答式检索
将系统从"记录与定期汇总工具"突破为"懂群聊上下文的私有 AI 智库"。

- [ ] **群聊语料的 Embedding 向量化**
  - 在 `src/summarizer.py` 的处理流程中，顺带将每日数以万计的消息通过轻量级模型（如 `text-embedding-3-small` 或本地 `BGE-m3`）进行文本切割和向量化。
  - 引入轻量并适合 Python 的本地向量库（推荐：`ChromaDB` 或 `Qdrant` SQLite 版本）。
- [ ] **智囊问答接口 (RAG Chat API)**
  - 在 `src/dashboard.py` 新增 `/api/chat/ask` API Endpoint。
  - **执行逻辑**: 接收用户自然语言提问 -> 转换为向量相似度检索 -> 从 SQLite/Chroma 提取相关性最高的 N 条聊天片段 -> 注入给 CPA 基座大模型 -> 回答用户提问并附带相关消息引用（Citations）。
- [ ] **问答对话面板 (RAG Chatbot UI)**
  - 在 React 前端侧边栏新增「🤖 私人智库」Tab。
  - 提供类似 ChatGPT 的交互流，让用户可以直接提问："过去三天群里大家对 XYZ 产品的评价如何？"，并能展示大模型推理及溯源引用。

### Phase 3: 🏢 多端订阅与 SaaS 化重构 (UserBot Multi-tenant)
打破现有的单环境、单账号壁垒，允许多个物理用户独立使用或接入服务。

- [x] **数据库底层租户隔离 (Tenant Isolation)**
  - 修改 `tg_monitor.sqlite` 的 schema 结构设计。
  - 核心表（`messages`, `groups_monitor`, `summary_jobs`）全部强制增加 `tenant_id` 和 `owner_id` 外键，从 DAO 层根绝越权查询问题。
- [x] **Web 端扫码登录/凭证注入 (Auth Portal)**
  - 开发多用户生命周期管理。不再局限于配置文件中死磕 `api_id` 和 `api_hash`。
  - 利用 Telethon 的 `send_code_request`，在前端新增一套完整的 Web-login 界面，允许最终用户输入手机号和验证码登入自己的 UserBot。
- [x] **多任务并行调度池 (Multi-Session Worker Pool)**
  - 重写 `src/collector.py`。从单点阻塞监听改造为 `asyncio` Task Group Manager。
  - 支持动态拉起、暂停、销毁不同租户对应的 Telethon Client Session，做到互不干扰、内存复用，支撑商业化灰产/量化群体的并发监控需求。
