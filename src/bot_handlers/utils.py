from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from datetime import datetime, timezone, timedelta
import asyncio
import html

HOURS_OPTIONS = [
    ("最近 3 小时", 3),
    ("最近 6 小时", 6),
    ("最近 12 小时", 12),
    ("最近 24 小时", 24),
    ("最近 3 天", 72),
    ("最近 7 天", 168),
    ("全部消息", 720),
]

class BotUtilsMixin:
    """提供 UI 构建、时间转换、长文本分段等辅助方法"""

    @staticmethod
    def _build_main_keyboard() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📝 智能摘要", callback_data="menu_summary"),
                InlineKeyboardButton("📊 群组统计", callback_data="menu_stats"),
            ],
            [
                InlineKeyboardButton("🔗 最新链接", callback_data="menu_links"),
                InlineKeyboardButton("🔍 搜索消息", callback_data="menu_search"),
            ],
            [
                InlineKeyboardButton("📋 每日报告", callback_data="action_report"),
                InlineKeyboardButton("📜 历史摘要", callback_data="action_history"),
            ],
            [InlineKeyboardButton("ℹ️ 系统状态", callback_data="action_status")],
        ])

    @staticmethod
    def _build_time_keyboard(action: str) -> InlineKeyboardMarkup:
        keyboard = []
        row = []
        for label, hours in HOURS_OPTIONS:
            row.append(InlineKeyboardButton(label, callback_data=f"{action}_{hours}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("◀️ 返回", callback_data="back_main")])
        return InlineKeyboardMarkup(keyboard)

    async def _show_main_menu_edit(self, message):
        await message.edit_text(
            "🔍 *TG Monitor — 群聊监控助手*\n\n选择你需要的功能：",
            reply_markup=self._build_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _show_time_picker(self, message, action: str):
        title = "📝 选择摘要时间范围" if action == "summary" else "📊 选择统计时间范围"
        await message.reply_text(
            f"*{title}：*",
            reply_markup=self._build_time_keyboard(action),
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _show_time_picker_edit(self, message, action: str):
        title = "📝 选择摘要时间范围" if action == "summary" else "📊 选择统计时间范围"
        await message.edit_text(
            f"*{title}：*",
            reply_markup=self._build_time_keyboard(action),
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _show_links_picker(self, message):
        keyboard = [
            [
                InlineKeyboardButton("最近 10 条", callback_data="links_10"),
                InlineKeyboardButton("最近 20 条", callback_data="links_20"),
            ],
            [
                InlineKeyboardButton("最近 50 条", callback_data="links_50"),
                InlineKeyboardButton("最近 100 条", callback_data="links_100"),
            ],
            [InlineKeyboardButton("◀️ 返回", callback_data="back_main")],
        ]
        await message.edit_text(
            "*🔗 选择要查看的链接数量：*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )

    def _fmt_time(self, iso_str: str) -> str:
        if not iso_str:
            return "?"
        try:
            dt = datetime.fromisoformat(iso_str)
            bj_tz = timezone(timedelta(hours=8))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_bj = dt.astimezone(bj_tz)
            return dt_bj.strftime("%m-%d %H:%M")
        except Exception:
            return iso_str[:16].replace("T", " ")

    @staticmethod
    def _esc_html(text: str) -> str:
        return html.escape(str(text)) if text else "?"

    async def _send_long_message(self, bot, chat_id: int, text: str, parse_mode=None):
        MAX_LEN = 4000
        if len(text) <= MAX_LEN:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            return

        parts = []
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > MAX_LEN:
                parts.append(current)
                current = line
            else:
                current += "\n" + line if current else line
        if current:
            parts.append(current)

        for i, part in enumerate(parts):
            if i > 0:
                await asyncio.sleep(0.5)
            await bot.send_message(chat_id=chat_id, text=part, parse_mode=parse_mode)

    def _make_progress_cb(self, progress_msg, msg_count: int):
        _last_edit_time = [0.0]
        _EDIT_INTERVAL = 1.5
        model_name = self.config.get("ai", {}).get("model", "?")

        async def _cb(text: str, current: int, total: int):
            import time
            now_t = time.monotonic()
            if current < total and now_t - _last_edit_time[0] < _EDIT_INTERVAL:
                return
            _last_edit_time[0] = now_t
            try:
                filled = int((current / total) * 10)
                bar = "■" * filled + "□" * (10 - filled)
                status_text = (
                    f"🧠 *AI 摘要任务进行中*\n\n"
                    f"📊 消息数量: {msg_count} 条\n"
                    f"🤖 模型: `{model_name}`\n\n"
                    f"进度: |{bar}| {current * 10}%\n"
                    f"状态: {text}"
                )
                await progress_msg.edit_text(status_text, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                pass

        return _cb
