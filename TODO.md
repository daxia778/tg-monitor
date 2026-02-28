# TG Monitor - Future Roadmap & TODOs

> 记录针对项目核心能力扩写的高优先级目标，以为后续系统迭代（AI 问答、SaaS 化、高阶链接聚合）提供清晰的发展脉络与开发计划。

## 📍 核心演进方向

### Phase 1: 🔗 链接聚合引擎深化 (深度解析与智能分类)
当前系统已能准确实时提取群聊中的 URL。下一步的核心是将纯文本链接转化为高价值的情报元数据。

- [x] **网页元数据抓取 (Meta Parser)**
  - 在 `src/db/messages.py` 中引入异步队列，剥离主聊天流程。
  - 使用 `BeautifulSoup` 或 `httpx` 轻量级获取链接的 `<title>`, `<meta description>` 以及主要封面图。
  - **难点规避**: 配置 User-Agent 伪装，对境外受限网站（Twitter/YouTube）设置超时跳过机制。
- [x] **AI 智能标注与清洗 (Link Scorer)**
  - 将捕获并解析后的链接元数据，送入本地 CPA (LLM) 进行二次打标。
  - **标签化**: 识别该链接是否属于 "干货评测"、"促销/羊毛"、"文档资源" 抑或是 "无价值广告"。
  - **去重算法**: 基于 URL normalized_hash (去除各种追踪参数 `?utm_source=...`) 合并重复分享，统计"群内热度被分享次数"。
- [x] **前端 UI 升级 (Rich Link Cards)**
  - 在 React 面板的 `LinksPage.tsx` 中，废弃传统的纯文本列表。
  - 设计类似 Twitter / Telegram Native 的富文本卡片瀑布流，支持按标签（如：🔥高热度、💰线报）快速过滤。

### Phase 2: 🧠 全局知识库化与 RAG 问答式检索
将系统从"记录与定期汇总工具"突破为"懂群聊上下文的私有 AI 智库"。

- [x] **群聊语料的 Embedding 向量化**
  - 在 `src/summarizer.py` 的处理流程中，顺带将每日数以万计的消息通过轻量级模型（如 `text-embedding-3-small` 或本地 `BGE-m3`）进行文本切割和向量化。
  - 引入轻量并适合 Python 的本地向量库（推荐：`ChromaDB` 或 `Qdrant` SQLite 版本）。
- [x] **智囊问答接口 (RAG Chat API)**
  - 在 `src/dashboard.py` 新增 `/api/chat/ask` API Endpoint。
  - **执行逻辑**: 接收用户自然语言提问 -> 转换为向量相似度检索 -> 从 SQLite/Chroma 提取相关性最高的 N 条聊天片段 -> 注入给 CPA 基座大模型 -> 回答用户提问并附带相关消息引用（Citations）。
- [x] **问答对话面板 (RAG Chatbot UI)**
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

### Phase 4: 📊 群社交关系图谱与 KOL 挖掘 (Network Intelligence)
对已积累的海量消息数据进行深度社会网络分析，帮助自己一眼看清每个群的"权力结构"与"信息流向"。

- [ ] **后端数据聚合 API (Graph Data Layer)**
  - 在 `src/dashboard.py` 新增 `/api/graph/nodes` 和 `/api/graph/edges` 两个接口。
  - **节点数据**: 按 `sender_id` 聚合，返回每个用户的 `发言量`、`被回复次数`、`转发他人次数`、`被转发次数`，据此计算 KOL 综合得分。
  - **边数据**: 基于 `reply_to_id` 反查来源 `sender_id`，构成有向加权边（A→B 代表 A 回复 B，权重=回复次数），同时提取 `forward_from` 字段为影响力传播边。
  - **活跃热力矩阵**: 按 `(weekday, hour)` 分组统计消息数，返回 7×24 的热力矩阵数据供前端 Heatmap 渲染。

- [ ] **力导向社交关系图 (Force Graph UI)**
  - 在 React 侧边栏新增「🕸️ 关系图谱」Tab，引入轻量的 `d3-force` 或者 `@nivo/network` 渲染力导向图。
  - 节点大小和亮度代表**综合影响力**（发言多 + 被回复多 + 被转发多 = 节点越大越亮）。
  - 悬停节点时，浮窗展示该用户的详细数据卡片（出现群组、发言量、Top 话题词云）。
  - 支持按**群组过滤**，隔离查看单群内部还是跨群全局的关系网络。

- [ ] **KOL 排行榜看板 (KOL Leaderboard Panel)**
  - 在图谱旁边提供一个侧边排行榜，综合得分 Top-N 的账号按卡片形式排列。
  - 每个 KOL 卡片显示：头像占位符、昵称、综合影响力分、活跃群组 Tag、以及"最近热门发言"预览。
  - 特别标注通过 `forward_from` 检测出的**高频信息源**（消息被大量转发的外部账号/频道）。

- [ ] **活跃时区热力图 (Activity Heatmap)**
  - 仿 Github Contribution Graph 风格，用极光蓝/紫光色带展示每日/每时的群消息密度。
  - 一眼看出：这个群在几点最活跃？周末还是工作日流量更大？什么时间段是"发公告"的最佳时机？

### Phase 5: 🛡️ 数据自动截断与瘦身 (Data Retention & Pruning)
为实现“无人值守、永久运行”的环境要求，防止数据库因常年积累导致体积失控和性能暴跌。

- [ ] **灵活配置的清理策略 (Retention Policies)**
  - 在前端设置中新增“数据保留策略”卡片，允许自定诸如“保留最近 30 天消息，超期物理删除”等规则。
  - 利用 `SettingsDAO`，将设置值如 `retention_days=30` 持久化入库。
- [ ] **自动化垃圾回收执行层 (Automated Garbage Collection)**
  - 后端接入轻量级清理任务（可挂靠至 Collector 进程并利用 asyncio 离线循环）。
  - 执行操作注重不锁库与平滑：利用 `DELETE FROM ... LIMIT X` 配合周期性的 `VACUUM` 来腾出 SQLite 的实际磁盘空间。
- [ ] **高价值数据隔离保护 (Preserve Meta Intelligence)**
  - 将海量且低价值的明细记录 (`messages`) 丢弃。
  - 将具有长效价值沉淀的精华内容分离，如压缩归纳好的 `summaries`、人工二次打标过的 `links` 设置不同的长期乃至永久的生命周期。
