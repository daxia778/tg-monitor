# 参与贡献指南 (Contributing to TG Monitor)

首先，感谢你抽出宝贵的时间为 **TG Monitor** 贡献代码或提出建议！本项目致力于为 Telegram 社区提供高效、轻量的群组监控方案。我们非常欢迎各种形式的贡献，包括但不限于：

- 🐛 Bug 报告与修复
- ✨ 新功能提案与实现
- 📝 文档改进与补充
- 🎨 UI/UX 优化
- 💡 代码重构与性能提升

这篇指南将帮助你快速了解本项目的开发流程与规范。

---

## 🐞 提交 Bug 报告

1. 在提交之前，请先检查 [Issues 页面](https://github.com/YOUR_USERNAME/tg-monitor/issues) 是否已经有相同或类似的问题。
2. 点击 **New Issue**，选择 **Bug Report** 模板。
3. 请尽可能详细地填写模板中的信息，包括**清晰的复现步骤**、**完整的报错日志**（脱敏后）以及**运行环境信息**（OS、Docker/本地、Python 版本等）。
4. ⚠️ **安全警告**：在任何时候提交日志或截图，请务必隐去你的 `API_ID`, `API_HASH`, `BOT_TOKEN`, `AI_API_KEY` 以及真实的群组 ID 标识！

## 💡 提出功能增强建议

我们非常乐意听取你的新点子！
1. 选择 **Feature Request** 模板。
2. 解释你为何需要这个功能（遇到了什么痛点）。
3. 如果可能，提供一个你设想的实现方案草图，或者类似的参考项目。

---

## 🛠️ 本地开发环境搭建

在向我们提交 Pull Request 之前，你需要配置好本地环境。

### 1. 克隆基础设施

```bash
git clone https://github.com/YOUR_USERNAME/tg-monitor.git
cd tg-monitor

# 建议使用虚拟环境隔离依赖
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .venv\Scripts\activate   # Windows

# 安装项目包和开发信赖
pip install -e ".[dev]"
```

### 2. 准备敏感配置

```bash
cp .env.example .env
cp config.example.yaml config.yaml
```
根据注释，填入必要的 API 凭证。不用担心，`.env` 和定制的 `config.yaml` 已被 `.gitignore` 包含，不会被提交。

---

## 🔀 提交 Pull Request (PR) 流程

1. **Fork 本仓库** 并通过命令或界面创建一个有意义的分支名称：
   ```bash
   git checkout -b feature/awesome-new-feature   # 新功能
   git checkout -b fix/issue-123                 # Bug 修复
   ```
2. **遵守架构规范**（参阅下方的[项目架构规范](#-项目架构规范)），进行开发。
3. 在提交代码前，**在本地进行基准测试**。确保你的修改没有引入语法错误，并且 `bot`, `collector` 和 `dashboard` 可以正常启动。
4. **提交代码**：请遵循规范的 Commit 格式（详见下方）。
5. **发起 PR**：推送到你的 Fork 仓库并拉起 PR，记得填写提供的 PR 模板。

---

## 📐 代码规范与准则

- **开发语言**：使用标准的 Python 3.9+ 语法。
- **并发要求**：本项目高度依赖 `asyncio`。请避免使用任何会造成事件循环阻塞的同步调用（如 `time.sleep`, `requests`）。统一使用 `asyncio.sleep`, `httpx` 等异步库。
- **配置与魔术变量**：所有外部调用的私钥必须通过 `.env` 注入，业务逻辑阈值应尽可能放在 `config.yaml` 中，**禁止硬编码**。
- **日志标准**：使用标准的 `logging` 模块输出（`logger.info/warning/error`）。请勿保留 `print()` 语句在生产代码中。
- **异常捕获**：凡是涉及外部网络（Telethon API、OpenAI API 等）或数据库读写的代码块，必须妥善地使用 `try/except` 进行包裹处理，确保主进程不因偶发网络波动崩溃。

## 🏗️ 项目架构规范

TG Monitor 经历了深度的 P3 模块化重构。请务必遵守这些界限：

```text
src/
├── bot.py             # <- 门面：仅组装 Mixins，不写具体业务逻辑
├── bot_handlers/      # <- 实装：Bot 逻辑必须分散到这里的 actions, commands, utils 去
├── collector.py       # <- 采集器引擎
├── dashboard.py       # <- FastAPI 路由层
├── database.py        # <- 门面：组合所有的 DB DAO，禁止直接写 SQL
└── db/                # <- 实装：具体的数据库表操作在此处 (core, messages, groups 等)
```
> [!IMPORTANT]
> - 如果修改了数据库表结构，请在 `src/db/core.py` 内部建立安全的迁移（Migration）逻辑。
> - 不要使 `database.py` 发生膨胀，遵守 Facade 模式。

---

## 📜 Commit 提交信息规范

强烈建议使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范，这能帮助我们快速了解历史变更：

- `feat:` 新增特性 (例如: `feat(db): 增加群组活跃度统计接口`)
- `fix:` 修复 Bug (例如: `fix(bot): 处理无法识别的命令回调`)
- `docs:` 仅文档修改 (例如: `docs: 完善部署指南`)
- `style:` 不影响代码逻辑的风格修改（空格、缩进格式化）
- `refactor:` 代码重构 (既不是新增特性也不是修改 Bug)
- `perf:` 提升性能的代码修改
- `test:` 添加或修改测试用例
- `chore:` 构建过程或辅助工具的变动

---

## 🤝 行为准则与文明社区

最后，请确保你的交流保持善意与专业：
- 尊重每一位开发与使用者。
- 把焦点放在代码和技术讨论上。
- 我们欢迎新手！不要在 Pull Request 审查过程中带有负面情绪，共同进步最重要。

🎉 再次感谢你的贡献，祝 Coding 愉快！
