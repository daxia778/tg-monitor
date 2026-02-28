<h1 align="center">
  <br>
  <img src="https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/Resources/art/icon256.png" alt="TG Monitor" width="120">
  <br>
  TG Monitor 💬
  <br>
</h1>

<h4 align="center">Telegram 群聊实时监控 & AI 智能汇总系统</h4>

<p align="center">
  <a href="https://github.com/YOUR_USERNAME/tg-monitor/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/YOUR_USERNAME/tg-monitor/docker-publish.yml?branch=main&style=flat-square&logo=github" alt="Build Status">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.9+-blue.svg?style=flat-square&logo=python&logoColor=white" alt="Python 3.9+">
  </a>
  <a href="https://github.com/YOUR_USERNAME/tg-monitor/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/YOUR_USERNAME/tg-monitor?style=flat-square" alt="License MIT">
  </a>
  <a href="https://hub.docker.com/r/YOUR_USERNAME/tg-monitor">
    <img src="https://img.shields.io/badge/docker-ready-2496ED.svg?style=flat-square&logo=docker&logoColor=white" alt="Docker Ready">
  </a>
</p>

<p align="center">
  <strong>轻量级 Telegram 群组监控工具</strong><br>
  支持多群实时采集、AI 摘要、链接聚合、关键词告警，并提供 Web 控制台和 Bot 交互界面。
</p>

<p align="center">
  <a href="#-特性">特性</a> •
  <a href="#-架构设计">架构设计</a> •
  <a href="#-快速部署">快速部署</a> •
  <a href="#-本地开发">本地开发</a> •
  <a href="#%EF%B8%8F-配置说明">配置说明</a>
</p>

---

## ✨ 特性

- ⚡ **实时稳定的采集机制**
  - 基于 Telethon (MTProto) 原生协议监听多群消息，确保低延迟。
  - 内置智能断线自动重连策略，重启后自动回填历史缺口。
- 🧠 **AI 驱动的智能汇总**
  - 无缝接入各大 LLM API 生成结构化的高质量群聊摘要。
  - 支持多 API Key 轮询与并发处理，有效应对限流策略，实现负载均衡。
- 🤖 **便捷的 Bot 交互中枢**
  - 深度的 Telegram Bot 集成，提供图形化的 Inline Keyboard 菜单交互。
  - 支持按需生成摘要、获取每日数据报告、动态统计分析、全局消息检索与链接追踪。
- 📊 **现代化的 Web 控制台**
  - 基于 FastAPI 构建的极速后端接口，结合原生 JavaScript/CSS 开发的纯净流畅前端。
  - 提供消息活跃度趋势图、分发热力图及定制化数据导出功能。
- 🛡️ **高并发与数据安全**
  - 核心架构深度解耦为 DAO 层组合（Mixins 与 Facade 模式）。
  - 数据库采用配置了 WAL 模式的异步 SQLite，并开启 FTS5 全文检索引擎，辅以触发器级的分批清理策略，彻底告别写锁阻塞现象。

## 📁 架构设计

代码采用模块化架构设计，通过解耦的数据访问层和处理器混合类提高维护性：

```text
tg-monitor/
├── src/
│   ├── bot.py                # 组合 Mixins 的终端 Bot 实例
│   ├── bot_handlers/         # Bot 逻辑拆分 (commands, callbacks, actions)
│   ├── collector.py          # 负责 MTProto 实时抓取的核心引擎
│   ├── dashboard.py          # FastAPI 服务后端
│   ├── database.py           # 数据库门面模式 (Facade)
│   ├── db/                   # 数据库核心 DAO 层 (连接、消息、链接、分析、群组)
│   ├── summarizer.py         # AI 模型对接模块
│   └── cli.py                # 全局命令行入口
├── workflows/                # Agent 自动化工作流域配置
├── config.example.yaml       # 监控策略模板
├── .env.example              # 机密凭据模板
├── docker-compose.yml        # 容器编排配置
├── Dockerfile                # 标准镜像构建脚本
└── pyproject.toml            # 现代化的依赖与构建配置
```

## 🐳 快速部署 (Docker)

本项目的镜像由 GitHub Actions 自动化构建管线编译，并直接推送至 GitHub Container Registry (GHCR)。这是推荐在生产环境上使用的部署方案。

> [!CAUTION]
> **首次运行认证**
> 首次启动需要完成 Telethon 会话认证（交互式登录验证码），建议先以非 Docker 的本地方式运行 `tg-monitor start collector` 完成认证，再将生成的 `tg_monitor.session` 文件映射进容器。

**1. 准备配置文件**
```bash
cp .env.example .env                # 填入 API Key 与 Token
cp config.example.yaml config.yaml  # 配置需要监听的群组
```

**2. 启动服务矩阵**
```bash
# 一键拉起系统：抓取引擎 + 交互机器人 + Web 数据大屏
docker compose up -d

# 实时追踪运行态日志
docker compose logs -f
```

## 🚀 本地开发

### 1. 检出与安装

```bash
git clone https://github.com/YOUR_USERNAME/tg-monitor.git
cd tg-monitor

# 推荐在虚拟环境 (venv) 中使用可编辑模式安装
pip install -e .
```

### 2. 初始化凭据

需要前往相应的平台获取凭据并填入基础配置中：
- API ID/Hash: [my.telegram.org](https://my.telegram.org)
- Bot Token: [@BotFather](https://t.me/BotFather)

```bash
cp .env.example .env
cp config.example.yaml config.yaml
```

### 3. 操作集指令

项目内置了易用的 CLI 命令行工具集 `tg-monitor`：

```bash
# 核心服务组
tg-monitor start collector      # 启动协议底层的实时监听进程
tg-monitor start bot            # 启动服务型交互机器人
tg-monitor start dashboard      # 运行可视化控制台 (默认侦听 http://localhost:8050)

# 工具组
tg-monitor fetch-history --limit 1000  # 手动回填历史遗漏消息记录
```

## ⚙️ 环境变量说明

需要在项目根目录下的 `.env` 文件中安全地映射如下凭据：

| 变量键值 | 说明 |
| :--- | :--- |
| `TG_API_ID` | Telegram 应用 API ID |
| `TG_API_HASH` | Telegram 应用 API Hash |
| `TG_PHONE` | 绑定的手机号（必须包含国家代码前缀） |
| `BOT_TOKEN` | 机器人专属访问令牌 |
| `BOT_OWNER_ID` | 机器人的所有者 User ID (用于越权保护) |
| `AI_API_URL` | 与 OpenAI 相兼容的 LLM 接口基地址 |
| `AI_API_KEY` | 主要的鉴权密钥 (也可通过枚举 `AI_API_KEY_1`, `2` 触发轮询机制) |

## 🤝 参与贡献

我们欢迎并鼓励社区通过提交 Issue 或 Pull Request 来共同塑造该项目。
请在提交之前参阅详细的 [贡献指南](CONTRIBUTING.md) 以了解编码规范和审查流程。

## 📄 开源许可证

本项目由 **MIT License** 开放协议提供授权 - 参阅 [LICENSE](LICENSE) 文件以获取相关细节信息。

---
<p align="center">Made with ❤️ for the Telegram Community</p>
