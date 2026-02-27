# 贡献指南

感谢你对 TG Monitor 项目的兴趣！本文件将帮助你快速上手参与贡献。

## 🐛 提交 Bug

1. 前往 [Issues](https://github.com/daxia778/tg-monitor/issues) 页面
2. 点击 **New Issue** → 选择 **Bug Report** 模板
3. 按模板填写：复现步骤、实际 vs 期望行为、日志截图
4. 如涉及敏感信息（API Key、群组 ID），请务必脱敏后再发布

## 💡 提交功能建议

1. 在 Issues 中选择 **Feature Request** 模板
2. 描述使用场景和期望效果
3. 如有参考实现或截图，欢迎附上

## 🛠️ 开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/daxia778/tg-monitor.git
cd tg-monitor

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# 安装依赖（含开发依赖）
pip install -e ".[dev]"

# 复制配置
cp .env.example .env
cp config.example.yaml config.yaml
# 编辑 .env 和 config.yaml 填入你的配置
```

## 🔀 提交 Pull Request

1. Fork 本仓库并创建新分支：
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. 遵循代码规范（见下方）
3. 确保没有引入新的语法错误：
   ```bash
   python -m py_compile src/*.py
   ```
4. 提交信息格式（[Conventional Commits](https://www.conventionalcommits.org/)）：
   ```
   feat(bot): 添加 /export 命令支持 JSON 格式导出
   fix(db): 修复 group_id 为 NULL 时的统计计数错误
   perf(collector): 并发拉取历史消息
   docs: 更新 README 快速开始步骤
   ```
5. 推送并在 GitHub 创建 PR，描述改动目的和测试方法

## 📐 代码规范

- **Python 版本**：3.9+
- **异步**：全面使用 `asyncio`，禁止阻塞调用（如 `time.sleep`）
- **敏感信息**：API Key、Token、用户 ID 一律通过 `.env` 注入，禁止硬编码
- **日志**：使用 `logging` 模块，不要用 `print()`
- **错误处理**：所有外部调用（TG API、LLM API、DB）必须有 try/except

## 📦 项目结构

```
src/
├── bot.py        # Telegram Bot 交互层
├── collector.py  # 消息实时采集（Telethon）
├── dashboard.py  # FastAPI Web 控制台后端
├── database.py   # SQLite 数据层（含 schema 迁移）
├── summarizer.py # AI 摘要模块（多 Key 轮询）
├── config.py     # 配置加载
└── cli.py        # CLI 入口
```

## 🤝 行为准则

- 尊重每一位贡献者
- 讨论技术问题，不进行人身攻击
- 欢迎新手，鼓励提问
