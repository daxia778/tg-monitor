# TG Monitor 🔍

> Telegram 群聊实时监控 & AI 智能汇总系统

轻量级 Telegram 群组监控工具，支持多群实时采集、AI 摘要、链接聚合、关键词告警，并提供 Web 控制台和 Bot 交互界面。

## ✨ 特性

- **实时采集**：基于 Telethon (MTProto) 监听多群消息，断线自动重连并回填缺口
- **AI 摘要**：调用 LLM API 生成结构化群聊摘要，支持多 key 轮询负载均衡和并发处理
- **Bot 控制**：通过 Telegram Bot 菜单交互，支持按需摘要 / 每日报告 / 统计 / 搜索 / 链接
- **Web 控制台**：FastAPI + 纯 JS 构建，提供消息趋势、热力图、导出等功能
- **链接追踪**：自动提取并聚合 URL，跨群广告链接高亮提示
- **数据安全**：WAL 模式 SQLite，FTS5 全文搜索，所有密钥通过 `.env` 注入

## 📁 项目结构

```
tg-monitor/
├── src/
│   ├── bot.py          # Telegram Bot 交互界面
│   ├── collector.py    # 消息实时采集（Telethon）
│   ├── dashboard.py    # FastAPI Web 控制台后端
│   ├── database.py     # SQLite 数据层
│   ├── summarizer.py   # AI 摘要模块
│   ├── config.py       # 配置加载
│   └── cli.py          # CLI 入口
├── config.example.yaml # 配置示例（安全版本）
├── .env.example        # 环境变量示例
└── pyproject.toml      # 项目依赖
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/tg-monitor.git
cd tg-monitor
```

### 2. 安装依赖

```bash
pip install -e .
```

### 3. 配置

```bash
# 复制配置模板
cp .env.example .env
cp config.example.yaml config.yaml

# 编辑 .env 填入你的 Telegram API ID/Hash、Bot Token、AI API Key
# 编辑 config.yaml 填入需要监控的群组 ID
```

### 4. 启动

```bash
# 启动采集器（实时监听）
tg-monitor start collector

# 启动 Bot
tg-monitor start bot

# 启动 Web 控制台（默认 http://localhost:8050）
tg-monitor start dashboard

# 拉取历史消息
tg-monitor fetch-history --limit 1000
```

## ⚙️ 环境变量（.env）

| 变量 | 说明 |
|------|------|
| `TG_API_ID` | Telegram API ID（my.telegram.org 获取） |
| `TG_API_HASH` | Telegram API Hash |
| `TG_PHONE` | 登录手机号（含国家代码） |
| `BOT_TOKEN` | Bot Token（@BotFather 创建） |
| `BOT_OWNER_ID` | Bot 所有者的 Telegram User ID |
| `AI_API_URL` | LLM API 地址 |
| `AI_API_KEY` | LLM API Key（或用 `AI_API_KEY_1`、`AI_API_KEY_2` 实现多 key 轮询） |

## 📦 依赖

- Python >= 3.9
- telethon、aiosqlite、httpx、fastapi、uvicorn、python-dotenv、click、rich、pyyaml

## 📄 License

MIT
