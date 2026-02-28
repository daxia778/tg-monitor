import logging
import asyncio
from datetime import datetime, timezone, timedelta
from telegram.constants import ChatAction, ParseMode

logger = logging.getLogger("tg-monitor.bot.actions")

class BotActionsMixin:
    """提供各种具体汇报和服务功能（依赖 BotUtilsMixin 部分辅助方法）"""

    async def _do_summary(self, message, hours: int):
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

        progress_cb = self._make_progress_cb(progress_msg, msg_count)

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

    async def _do_links(self, message, count: int):
        await self._ensure_db()
        chat_id = message.chat_id
        bot = message.get_bot()

        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

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

            spam_links = [l for l in links if (l.get("group_count") or 0) > 1]
            normal_links = [l for l in links if (l.get("group_count") or 0) <= 1]

            lines = []

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
            await self._send_long_message(bot, chat_id, text)

        except Exception as e:
            logger.error(f"❌ 链接查询失败: {e}", exc_info=True)
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ 链接查询出错: {e}",
            )

    async def _do_search(self, message, keyword: str, page: int = 0, edit: bool = False):
        await self._ensure_db()
        chat_id = message.chat_id
        bot = message.get_bot()

        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        PAGE_SIZE = 10
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
        page = min(page, total_pages - 1)
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

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ 上一页", callback_data=f"search_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("下一页 ▶️", callback_data=f"search_page_{page + 1}"))
        keyboard = [nav_buttons] if nav_buttons else []
        keyboard.append([InlineKeyboardButton("◀️ 返回", callback_data="back_main")])
        markup = InlineKeyboardMarkup(keyboard)

        send_kwargs = dict(text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        if edit:
            try:
                await message.edit_text(**send_kwargs)
                return
            except Exception:
                pass
        await bot.send_message(chat_id=chat_id, **send_kwargs)

    async def _do_report(self, message):
        await self._ensure_db()
        chat_id = message.chat_id
        bot = message.get_bot()

        progress_msg = await bot.send_message(
            chat_id=chat_id,
            text="📊 *正在生成每日报告...*\n\n请稍候，AI 正在分析过去 24 小时的数据...",
            parse_mode=ParseMode.MARKDOWN,
        )

        msg_count_24h = await self.db.get_message_count(
            since=(datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec='seconds')
        )
        progress_cb = self._make_progress_cb(progress_msg, msg_count_24h)

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
        await self._ensure_db()
        chat_id = message.chat_id
        bot = message.get_bot()

        groups = await self.db.get_groups()
        total_msgs = await self.db.get_message_count()

        now = datetime.now(timezone.utc)
        recent_count = await self.db.get_message_count(
            since=(now - timedelta(hours=1)).isoformat(timespec='seconds')
        )

        date_range = await self.db.get_date_range()
        last_msg_time = self._fmt_time(date_range.get("last_msg", ""))
        last_msg_raw = date_range.get("last_msg", "")
        collector_ok = True
        if last_msg_raw:
            try:
                last_dt = datetime.fromisoformat(last_msg_raw.replace("Z", "+00:00"))
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

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [[InlineKeyboardButton("◀️ 返回", callback_data="back_main")]]
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )
