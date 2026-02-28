"""
Telegram Bot 交互界面
通过 TG 机器人菜单与监控系统交互
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand,
)
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)

from .config import load_config
from .database import Database
from .summarizer import Summarizer

logger = logging.getLogger("tg-monitor.bot")

# ─── 常量 ───
HOURS_OPTIONS = [
    ("最近 3 小时", 3),
    ("最近 6 小时", 6),
    ("最近 12 小时", 12),
    ("最近 24 小时", 24),
    ("最近 3 天", 72),
    ("最近 7 天", 168),
    ("全部消息", 720),
]


class MonitorBot:
    """TG 监控机器人"""

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
    # 键盘构建器（共用）
    # ═══════════════════════════════════════════

    @staticmethod
    def _build_main_keyboard() -> InlineKeyboardMarkup:
        """构建主菜单键盘"""
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
        """构建时间选择器键盘"""
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

    # ═══════════════════════════════════════════
    # 命令处理器
    # ═══════════════════════════════════════════

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
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
        """处理 /summary 命令"""
        if not self._is_owner(update.effective_user.id):
            return
        await self._show_time_picker(update.message, "summary")

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /stats 命令"""
        if not self._is_owner(update.effective_user.id):
            return
        await self._do_stats(update.message, 24)

    async def cmd_links(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /links 命令"""
        if not self._is_owner(update.effective_user.id):
            return
        await self._do_links(update.message, 20)

    async def cmd_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /search 命令"""
        if not self._is_owner(update.effective_user.id):
            return

        if context.args:
            keyword = " ".join(context.args)
            # P1#5：存储关键词供翻页回调使用
            context.user_data["last_search_keyword"] = keyword
            await self._do_search(update.message, keyword)
        else:
            await update.message.reply_text(
                "🔍 请输入搜索关键词：\n\n"
                "用法: `/search 关键词`\n"
                "例如: `/search 购买链接`",
                parse_mode=ParseMode.MARKDOWN,
            )

    # ═══════════════════════════════════════════
    # 回调处理器
    # ═══════════════════════════════════════════

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理内联键盘回调"""
        query = update.callback_query
        await query.answer()

        if not self._is_owner(query.from_user.id):
            await query.edit_message_text("⛔ 你没有权限。")
            return

        data = query.data

        # 菜单导航
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
            # 设置等待搜索输入的状态
            context.user_data["waiting_search"] = True

        # 摘要时间选择
        elif data.startswith("summary_"):
            hours = int(data.rsplit("_", 1)[-1])  # B1 修复：rsplit 防止 action 名含下划线时取错
            await query.edit_message_text(f"⏳ 正在生成最近 {hours} 小时的摘要...")
            await self._do_summary(query.message, hours)

        # 统计时间选择
        elif data.startswith("stats_"):
            hours = int(data.rsplit("_", 1)[-1])  # B1 修复
            await query.edit_message_text(f"⏳ 正在统计最近 {hours} 小时的数据...")
            await self._do_stats(query.message, hours)

        # 链接数量选择
        elif data.startswith("links_"):
            count = int(data.rsplit("_", 1)[-1])  # B1 修复
            await query.edit_message_text(f"⏳ 正在获取最近 {count} 条链接...")
            await self._do_links(query.message, count)

        # 直接动作
        elif data == "action_report":
            await query.edit_message_text("⏳ 正在生成每日报告...")
            await self._do_report(query.message)
        elif data == "action_history":
            await self._do_history(query.message)
        elif data == "action_status":
            await self._do_status(query.message)

        # 返回主菜单
        elif data == "back_main":
            await self._show_main_menu_edit(query.message)

        # P1#5：搜索翻页
        elif data.startswith("search_page_"):
            page = int(data.rsplit("_", 1)[-1])
            keyword = context.user_data.get("last_search_keyword", "")
            if keyword:
                await self._do_search(query.message, keyword, page=page, edit=True)
            else:
                await query.edit_message_text("⚠️ 搜索关键词已过期，请重新搜索。")

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理文本消息（搜索）"""
        if not self._is_owner(update.effective_user.id):
            return

        if context.user_data.get("waiting_search"):
            context.user_data["waiting_search"] = False
            keyword = update.message.text
            # P1#5：存储关键词供翻页回调使用
            context.user_data["last_search_keyword"] = keyword
            await self._do_search(update.message, keyword)

    # ═══════════════════════════════════════════
    # UI 辅助方法
    # ═══════════════════════════════════════════

    async def _show_main_menu_edit(self, message):
        """编辑消息为主菜单"""
        await message.edit_text(
            "🔍 *TG Monitor — 群聊监控助手*\n\n选择你需要的功能：",
            reply_markup=self._build_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _show_time_picker(self, message, action: str):
        """发送时间选择器"""
        title = "📝 选择摘要时间范围" if action == "summary" else "📊 选择统计时间范围"
        await message.reply_text(
            f"*{title}：*",
            reply_markup=self._build_time_keyboard(action),
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _show_time_picker_edit(self, message, action: str):
        """编辑消息为时间选择器"""
        title = "📝 选择摘要时间范围" if action == "summary" else "📊 选择统计时间范围"
        await message.edit_text(
            f"*{title}：*",
            reply_markup=self._build_time_keyboard(action),
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _show_links_picker(self, message):
        """链接数量选择"""
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

    # ═══════════════════════════════════════════
    # 核心功能
    # ═══════════════════════════════════════════

    def _make_progress_cb(self, progress_msg, msg_count: int):
        """工厂方法：生成限速进度回调，消除 _do_summary / _do_report 中的重复代码。
        最多每 1.5s 刷新一次消息，最后一步（current==total）强制刷新。
        """
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

    def _fmt_time(self, iso_str: str) -> str:
        """格式化 ISO 时间为北京时间 (UTC+8) 可读格式"""
        if not iso_str:
            return "?"
        try:
            # 解析 ISO 时间并正确转换为北京时间
            dt = datetime.fromisoformat(iso_str)
            bj_tz = timezone(timedelta(hours=8))
            # 如果没有时区信息，假定为 UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_bj = dt.astimezone(bj_tz)
            return dt_bj.strftime("%m-%d %H:%M")
        except Exception:
            return iso_str[:16].replace("T", " ")

    async def _do_summary(self, message, hours: int):
        """生成并发送 AI 摘要"""
        await self._ensure_db()
        chat_id = message.chat_id
        bot = message.get_bot()

        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')
        until = now.isoformat(timespec='seconds')
        msg_count = await self.db.get_message_count(since=since)
        date_range = await self.db.get_date_range(since=since)

        if msg_count == 0:
            await bot.send_message(
                chat_id=chat_id,
                text=f"📭 最近 {hours} 小时内没有消息记录。",
            )
            return

        actual_first = self._fmt_time(date_range.get("first_msg", ""))
        actual_last = self._fmt_time(date_range.get("last_msg", ""))

        # 发送初始进度消息
        progress_msg = await bot.send_message(
            chat_id=chat_id,
            text=(
                f"🧠 *AI 摘要任务已启动*\n\n"
                f"📊 消息数量: {msg_count} 条\n"
                f"⏰ 时间范围: {actual_first} → {actual_last}\n"
                f"🤖 模型: `{self.config.get('ai', {}).get('model', '?')}`\n\n"
                f"进度: |□□□□□□□□□□| 0%\n"
                f"状态: 正在初始化..."
            ),
            parse_mode=ParseMode.MARKDOWN,
        )

        # 使用工厂方法生成限速进度回调（P0#3 修复：消除重复代码）
        progress_cb = self._make_progress_cb(progress_msg, msg_count)

        # 保持 typing 动作（防止 TG 认为 bot 已停止响应）
        async def keep_typing():
            while True:
                try:
                    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                    await asyncio.sleep(4)
                except Exception:
                    break

        typing_task = asyncio.create_task(keep_typing())

        try:
            result = await self.summarizer.summarize(hours=hours, save=True, progress_cb=progress_cb)

            try:
                await progress_msg.delete()
            except Exception:
                pass

            header = (
                f"📝 群聊摘要\n\n"
                f"📊 分析了 {msg_count} 条消息\n"
                f"⏰ 时间范围: {actual_first} → {actual_last}\n"
                f"🕐 查询跨度: 最近 {hours} 小时\n"
                f"{'─'*20}\n\n"
            )

            full_text = header + result
            await self._send_long_message(bot, chat_id, full_text)

        except Exception as e:
            logger.error(f"摘要生成失败: {e}", exc_info=True)
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ 摘要生成失败: {e}",
            )
        finally:
            typing_task.cancel()

    async def _do_stats(self, message, hours: int):
        """发送统计信息"""
        await self._ensure_db()
        chat_id = message.chat_id
        bot = message.get_bot()

        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')

        stats = await self.db.get_stats(since=since)
        top_senders = await self.db.get_top_senders(since=since, limit=5)

        if not stats:
            await bot.send_message(chat_id=chat_id, text="📭 暂无统计数据。")
            return

        total_msgs = sum(s["message_count"] for s in stats)
        total_users = sum(s["active_users"] for s in stats)

        # 获取实际时间范围
        date_range = await self.db.get_date_range(since=since)
        actual_first = self._fmt_time(date_range.get("first_msg", ""))
        actual_last = self._fmt_time(date_range.get("last_msg", ""))

        text = f"📊 *最近 {hours} 小时统计*\n\n"
        text += f"📌 总消息数: *{total_msgs}*\n"
        text += f"👥 总活跃用户: *{total_users}*\n"
        text += f"📂 活跃群组: *{len(stats)}*\n"
        text += f"⏰ 实际范围: {actual_first} → {actual_last}\n\n"

        text += "━━━━━━━━━━━━━━━━━━━━\n"
        for s in stats:
            title = s.get("title") or f"群组{s['group_id']}"
            text += f"▸ *{title}*\n"
            text += f"  💬 {s['message_count']} 条 · 👤 {s['active_users']} 人\n"

        if top_senders:
            text += "\n━━━━━━━━━━━━━━━━━━━━\n"
            text += "🏆 *最活跃用户*\n\n"
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            for i, t in enumerate(top_senders):
                name = t.get("sender_name") or "?"
                text += f"{medals[i]} {name} — {t['msg_count']} 条\n"

        await self._send_long_message(bot, chat_id, text, ParseMode.MARKDOWN)

    @staticmethod
    def _esc_html(text: str) -> str:
        """转义 HTML 特殊字符"""
        import html
        return html.escape(str(text)) if text else "?"

    async def _do_links(self, message, count: int):
        """发送链接（按 URL 聚合去重，高亮跨群广告）"""
        await self._ensure_db()
        chat_id = message.chat_id
        bot = message.get_bot()

        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            # 动态加载过滤域名
            block_domains = self.config.get("filtering", {}).get(
                "block_domains", 
                ["t.me", "telegram.me", "telegram.org", "telegra.ph", "telegram.dog"]
            )
            
            links = await self.db.get_links_aggregated(
                limit=count, 
                block_domains=block_domains
            )

            if not links:
                await bot.send_message(chat_id=chat_id, text="📭 暂无链接记录。")
                return

            # 分为跨群广告和普通链接
            spam_links = [l for l in links if (l.get("group_count") or 0) > 1]
            normal_links = [l for l in links if (l.get("group_count") or 0) <= 1]

            lines = []

            # ── 跨群广告区 ──
            if spam_links:
                lines.append(f"🚨 跨群推广链接 ({len(spam_links)} 条)")
                lines.append("以下链接出现在多个群中，疑似广告：\n")
                for i, link in enumerate(spam_links, 1):
                    url = link.get("url") or "?"
                    total = link.get("total_count") or 0
                    g_count = link.get("group_count") or 0
                    groups = link.get("group_titles") or "?"
                    senders = link.get("sender_names") or "?"
                    first = self._fmt_time(link.get("first_seen") or "")
                    last = self._fmt_time(link.get("last_seen") or "")

                    lines.append(f"{i}. 🔗 {url}")
                    lines.append(f"   📊 出现 {total} 次 · 涉及 {g_count} 个群")
                    lines.append(f"   📌 群组: {groups}")
                    lines.append(f"   👤 发送者: {senders}")
                    lines.append(f"   🕐 {first} → {last}")
                    lines.append("")

            # ── 普通链接区 ──
            if normal_links:
                start_idx = len(spam_links) + 1
                if spam_links:
                    lines.append("━" * 20)
                lines.append(f"🔗 其他链接 ({len(normal_links)} 条)\n")
                for i, link in enumerate(normal_links, start_idx):
                    url = link.get("url") or "?"
                    total = link.get("total_count") or 0
                    groups = link.get("group_titles") or "?"
                    senders = link.get("sender_names") or "?"
                    last = self._fmt_time(link.get("last_seen") or "")

                    lines.append(f"{i}. 🔗 {url}")
                    if total > 1:
                        lines.append(f"   📊 出现 {total} 次")
                    lines.append(f"   📌 {groups} · 👤 {senders}")
                    lines.append(f"   🕐 {last}")
                    lines.append("")

            text = "\n".join(lines)
            # 纯文本发送，不用任何格式化，避免特殊字符问题
            await self._send_long_message(bot, chat_id, text)

        except Exception as e:
            logger.error(f"❌ 链接查询失败: {e}", exc_info=True)
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ 链接查询出错: {e}",
            )

    async def _do_search(self, message, keyword: str, page: int = 0, edit: bool = False):
        """搜索消息（支持翻页，P1#5 修复）"""
        await self._ensure_db()
        chat_id = message.chat_id
        bot = message.get_bot()

        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        PAGE_SIZE = 10
        # 多拉一批，支持最多 6 页（60 条）
        all_results = await self.db.search_messages(keyword, limit=PAGE_SIZE * 6)

        if not all_results:
            msg = f'🔍 未找到包含 "{keyword}" 的消息。'
            if edit:
                await message.edit_text(msg)
            else:
                await bot.send_message(chat_id=chat_id, text=msg)
            return

        total = len(all_results)
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        page = min(page, total_pages - 1)  # 防止越界
        page_results = all_results[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

        text = f'🔍 *搜索: "{keyword}"*\n'
        text += f'第 {page + 1}/{total_pages} 页，共 {total} 条结果\n\n'

        for msg in page_results:
            date = self._fmt_time(msg.get("date", ""))
            group = msg.get("group_title") or f"群组{msg['group_id']}"
            sender = msg.get("sender_name") or "?"
            msg_text = (msg.get("text") or "")[:100]
            text += f"`{date}` [{group}]\n"
            text += f"👤 {sender}: {msg_text}\n\n"

        # 构建翻页按钮
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ 上一页", callback_data=f"search_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("下一页 ▶️", callback_data=f"search_page_{page + 1}"))
        keyboard = [nav_buttons] if nav_buttons else []
        keyboard.append([InlineKeyboardButton("◀️ 返回", callback_data="back_main")])
        markup = InlineKeyboardMarkup(keyboard)

        # 存储关键词供翻页回调使用
        # 注意：edit 模式用于翻页（edit_message），首次搜索用 send_message
        send_kwargs = dict(text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        if edit:
            try:
                await message.edit_text(**send_kwargs)
                return
            except Exception:
                pass  # 若 edit 失败则 fall through 到 send
        await bot.send_message(chat_id=chat_id, **send_kwargs)

    async def _do_report(self, message):
        """每日报告"""
        await self._ensure_db()
        chat_id = message.chat_id
        bot = message.get_bot()

        progress_msg = await bot.send_message(
            chat_id=chat_id,
            text="📊 *正在生成每日报告...*\n\n请稍候，AI 正在分析过去 24 小时的数据...",
            parse_mode=ParseMode.MARKDOWN,
        )

        # 使用工厂方法生成限速进度回调（P0#3 修复：消除重复代码）
        msg_count_24h = await self.db.get_message_count(
            since=(datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec='seconds')
        )
        progress_cb = self._make_progress_cb(progress_msg, msg_count_24h)

        # 保持 typing 动作（防止 TG 认为 bot 已停止响应）
        async def keep_typing():
            while True:
                try:
                    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                    await asyncio.sleep(4)
                except Exception:
                    break

        typing_task = asyncio.create_task(keep_typing())

        try:
            result = await self.summarizer.summarize_per_group(hours=24, save=True, progress_cb=progress_cb)

            try:
                await progress_msg.delete()
            except Exception:
                pass

            msg_count = await self.db.get_message_count(
                since=(datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec='seconds')
            )

            header = (
                f"📋 *每日报告*\n\n"
                f"📊 过去 24 小时共 {msg_count} 条消息\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
            )

            await self._send_long_message(bot, chat_id, header + result)

        except Exception as e:
            logger.error(f"报告生成失败: {e}", exc_info=True)
            await bot.send_message(chat_id=chat_id, text=f"❌ 报告生成失败: {e}")
        finally:
            typing_task.cancel()

    async def _do_history(self, message):
        """查看历史摘要"""
        await self._ensure_db()
        chat_id = message.chat_id
        bot = message.get_bot()

        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        summaries = await self.db.get_latest_summaries(limit=3)

        if not summaries:
            await bot.send_message(chat_id=chat_id, text="📭 暂无历史摘要。")
            return

        for s in summaries:
            group_name = s.get("group_title") or "全部群组"
            start = self._fmt_time(s.get("period_start", ""))
            end = self._fmt_time(s.get("period_end", ""))

            text = (
                f"📜 *历史摘要*\n"
                f"📌 {group_name} | {s['message_count']} 条消息\n"
                f"⏰ {start} → {end}\n\n"
                f"{s['content']}"
            )

            await self._send_long_message(bot, chat_id, text)

    async def _do_status(self, message):
        """系统状态"""
        await self._ensure_db()
        chat_id = message.chat_id
        bot = message.get_bot()

        groups = await self.db.get_groups()
        total_msgs = await self.db.get_message_count()

        now = datetime.now(timezone.utc)
        recent_count = await self.db.get_message_count(
            since=(now - timedelta(hours=1)).isoformat(timespec='seconds')
        )

        # B3 修复：显示数据库最新消息的实际时间，让用户能判断 collector 是否在正常工作
        date_range = await self.db.get_date_range()
        last_msg_time = self._fmt_time(date_range.get("last_msg", ""))
        # 判断 collector 健康状态：最新消息超过 30 分钟则可能异常
        last_msg_raw = date_range.get("last_msg", "")
        collector_ok = True
        if last_msg_raw:
            try:
                last_dt = datetime.fromisoformat(
                    last_msg_raw.replace("Z", "+00:00")
                )
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                gap_min = (now - last_dt).total_seconds() / 60
                collector_ok = gap_min < 30
            except Exception:
                pass

        status_icon = "✅ 正常" if collector_ok else "⚠️ 可能异常（超 30 分钟无新消息）"

        text = (
            "ℹ️ *系统状态*\n\n"
            f"📌 监控群组: {len(groups)} 个\n"
            f"💬 总消息量: {total_msgs} 条\n"
            f"⏰ 最近1小时: {recent_count} 条新消息\n"
            f"🕐 最新消息: {last_msg_time}\n"
            f"🤖 AI 模型: `{self.config.get('ai', {}).get('model', '?')}`\n"
            f"📡 Collector: {status_icon}\n"
        )

        keyboard = [[InlineKeyboardButton("◀️ 返回", callback_data="back_main")]]
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )

    # ═══════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════

    async def _send_long_message(self, bot, chat_id: int, text: str,
                                  parse_mode=None):
        """分段发送长消息（TG 限制 4096 字节）"""
        MAX_LEN = 4000  # 留些余量

        if len(text) <= MAX_LEN:
            await bot.send_message(
                chat_id=chat_id, text=text, parse_mode=parse_mode,
            )
            return

        # 按段落分割
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
            await bot.send_message(
                chat_id=chat_id, text=part, parse_mode=parse_mode,
            )

    # ═══════════════════════════════════════════
    # 启动
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
