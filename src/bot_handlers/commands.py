from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

class BotCommandsMixin:
    """提供各种 Telegram 斜杠指令的处理"""

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ 你没有权限使用此机器人。")
            return

        await update.message.reply_text(
            "🔍 *TG Monitor — 群聊监控助手*\n\n"
            "选择你需要的功能：",
            reply_markup=self._build_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )

    async def cmd_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update.effective_user.id):
            return
        await self._show_time_picker(update.message, "summary")

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update.effective_user.id):
            return
        await self._do_stats(update.message, 24)

    async def cmd_links(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update.effective_user.id):
            return
        await self._do_links(update.message, 20)

    async def cmd_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update.effective_user.id):
            return

        if context.args:
            keyword = " ".join(context.args)
            context.user_data["last_search_keyword"] = keyword
            await self._do_search(update.message, keyword)
        else:
            await update.message.reply_text(
                "🔍 请输入搜索关键词：\n\n"
                "用法: `/search 关键词`\n"
                "例如: `/search 购买链接`",
                parse_mode=ParseMode.MARKDOWN,
            )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理文本消息（搜索）"""
        if not self._is_owner(update.effective_user.id):
            return

        if context.user_data.get("waiting_search"):
            context.user_data["waiting_search"] = False
            keyword = update.message.text
            context.user_data["last_search_keyword"] = keyword
            await self._do_search(update.message, keyword)
