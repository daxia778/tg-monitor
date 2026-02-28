from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

class BotCallbacksMixin:
    """提供内联键盘回调按钮处理"""

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if not self._is_owner(query.from_user.id):
            await query.edit_message_text("⛔ 你没有权限。")
            return

        data = query.data

        if data == "menu_summary":
            await self._show_time_picker_edit(query.message, "summary")
        elif data == "menu_stats":
            await self._show_time_picker_edit(query.message, "stats")
        elif data == "menu_links":
            await self._show_links_picker(query.message)
        elif data == "menu_search":
            await query.edit_message_text(
                "🔍 请直接发送搜索关键词，或使用命令：\n"
                "`/search 关键词`",
                parse_mode=ParseMode.MARKDOWN,
            )
            context.user_data["waiting_search"] = True

        elif data.startswith("summary_"):
            hours = int(data.rsplit("_", 1)[-1])
            await query.edit_message_text(f"⏳ 正在生成最近 {hours} 小时的摘要...")
            await self._do_summary(query.message, hours)

        elif data.startswith("stats_"):
            hours = int(data.rsplit("_", 1)[-1])
            await query.edit_message_text(f"⏳ 正在统计最近 {hours} 小时的数据...")
            await self._do_stats(query.message, hours)

        elif data.startswith("links_"):
            count = int(data.rsplit("_", 1)[-1])
            await query.edit_message_text(f"⏳ 正在获取最近 {count} 条链接...")
            await self._do_links(query.message, count)

        elif data == "action_report":
            await query.edit_message_text("⏳ 正在生成每日报告...")
            await self._do_report(query.message)
        elif data == "action_history":
            await self._do_history(query.message)
        elif data == "action_status":
            await self._do_status(query.message)

        elif data == "back_main":
            await self._show_main_menu_edit(query.message)

        elif data.startswith("search_page_"):
            page = int(data.rsplit("_", 1)[-1])
            keyword = context.user_data.get("last_search_keyword", "")
            if keyword:
                await self._do_search(query.message, keyword, page=page, edit=True)
            else:
                await query.edit_message_text("⚠️ 搜索关键词已过期，请重新搜索。")
