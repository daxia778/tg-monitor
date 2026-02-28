"""
Telegram Bot 交互界面
通过 TG 机器人菜单与监控系统交互
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from telegram import BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)
from telegram.constants import ParseMode

from .config import load_config
from .database import Database
from .summarizer import Summarizer
from .bot_handlers import BotUtilsMixin, BotActionsMixin, BotCommandsMixin, BotCallbacksMixin

logger = logging.getLogger("tg-monitor.bot")


class MonitorBot(BotUtilsMixin, BotActionsMixin, BotCommandsMixin, BotCallbacksMixin):
    """TG 监控机器人 (核心逻辑整合版)"""

    def __init__(self, config: dict, owner_id: Optional[int] = None):
        self.config = config
        self.bot_token = config.get("bot", {}).get("token", "")
        self.owner_id = owner_id or config.get("bot", {}).get("owner_id")
        self.db: Optional[Database] = None
        self.summarizer: Optional[Summarizer] = None

    async def _ensure_db(self):
        """确保数据库连接"""
        if self.db is None:
            self.db = Database(self.config["database"]["path"])
            await self.db.connect()
            self.summarizer = Summarizer(self.config, self.db)

    def _is_owner(self, user_id: int) -> bool:
        """检查是否为机器人所有者"""
        if self.owner_id is None:
            logger.warning("⚠️ 未配置 owner_id，拒绝所有访问请求")
            return False  # 未配置则拒绝所有人，避免安全漏洞
        return user_id == self.owner_id

    # ═══════════════════════════════════════════
    # 启动与路由注册
    # ═══════════════════════════════════════════

    def run(self):
        """启动机器人"""
        if not self.bot_token:
            logger.error("❌ 未配置 bot.token，请在 config.yaml 中设置")
            return

        app = Application.builder().token(self.bot_token).build()

        # 注册命令
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("summary", self.cmd_summary))
        app.add_handler(CommandHandler("stats", self.cmd_stats))
        app.add_handler(CommandHandler("links", self.cmd_links))
        app.add_handler(CommandHandler("search", self.cmd_search))

        # 注册回调
        app.add_handler(CallbackQueryHandler(self.handle_callback))

        # 注册文本处理（搜索）
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_text
        ))

        # 设置菜单命令
        async def post_init(application):
            await application.bot.set_my_commands([
                BotCommand("start", "🏠 主菜单"),
                BotCommand("summary", "📝 AI 智能摘要"),
                BotCommand("stats", "📊 群组统计"),
                BotCommand("links", "🔗 最新链接"),
                BotCommand("search", "🔍 搜索消息"),
            ])
            me = await application.bot.get_me()
            logger.info(f"🤖 机器人已启动: @{me.username}")

        app.post_init = post_init

        # P1#4 修复：Bot 退出时优雅关闭数据库连接，防止资源泄漏
        async def post_shutdown(application):
            if self.db:
                await self.db.close()
                logger.info("🔌 数据库连接已关闭")

        app.post_shutdown = post_shutdown

        # ─── 定时推送摘要 ───
        push_cfg = self.config.get("scheduled_push", {})
        if push_cfg.get("enabled") and self.owner_id:
            from apscheduler.triggers.cron import CronTrigger
            cron_str = push_cfg.get("cron", "0 9,21 * * *")
            push_hours = push_cfg.get("hours", 12)

            async def scheduled_push(context: ContextTypes.DEFAULT_TYPE):
                try:
                    logger.info(f"⏰ 定时推送触发 (最近 {push_hours}h)")
                    await self._ensure_db()
                    summary = await self.summarizer.summarize_per_group(
                        hours=push_hours, save=True
                    )
                    # 分段发送（避免超长消息截断）
                    full_text = f"⏰ *定时摘要推送*\n\n{summary}"
                    await self._send_long_message(
                        context.bot, self.owner_id, full_text, ParseMode.MARKDOWN
                    )
                    logger.info("✅ 定时推送完成")
                except Exception as e:
                    logger.error(f"❌ 定时推送失败: {e}", exc_info=True)
                    # 当定时推送失败时，主动向 owner 发送错误通知，不再只写日志
                    try:
                        await context.bot.send_message(
                            chat_id=self.owner_id,
                            text=f"❌ 定时摘要推送失败\n\n`{type(e).__name__}: {str(e)[:200]}`",
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    except Exception:
                        pass  # 发送失败就放弃，不归递

            # 解析 cron 表达式，显式指定 Asia/Shanghai 时区确保 9:00/21:00 是北京时间
            parts = cron_str.split()
            trigger = CronTrigger(
                minute=parts[0], hour=parts[1],
                day=parts[2], month=parts[3], day_of_week=parts[4],
                timezone="Asia/Shanghai",
            )
            app.job_queue.run_custom(scheduled_push, job_kwargs={"trigger": trigger})
            logger.info(f"⏰ 定时推送已注册: {cron_str} (Asia/Shanghai)")

        logger.info("🚀 启动 TG 机器人...")
        app.run_polling(drop_pending_updates=True)


def run_bot(config_path=None):
    """启动机器人入口"""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    config = load_config(config_path)
    bot = MonitorBot(config)
    bot.run()


if __name__ == "__main__":
    run_bot()
