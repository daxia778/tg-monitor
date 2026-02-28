"""
Telegram 消息采集模块
使用 Telethon (MTProto) 实时监听指定群聊消息
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set

from telethon import TelegramClient, events
from telethon.tl.types import (
    Channel, Chat, User, MessageMediaPhoto,
    MessageMediaDocument, MessageMediaWebPage,
    MessageFwdHeader, PeerChannel, PeerChat, PeerUser,
    UpdateDeleteMessages, UpdateDeleteChannelMessages,
)

from .database import Database
from .alerts import AlertManager

logger = logging.getLogger("tg-monitor.collector")


def _get_sender_name(sender) -> str:
    """从 sender 对象提取显示名"""
    if sender is None:
        return "Unknown"
    if isinstance(sender, User):
        parts = [sender.first_name or "", sender.last_name or ""]
        name = " ".join(p for p in parts if p)
        return name or sender.username or str(sender.id)
    if isinstance(sender, Channel):
        return sender.title or str(sender.id)
    return str(getattr(sender, "id", "Unknown"))


def _get_media_type(media) -> Optional[str]:
    """获取媒体类型"""
    if media is None:
        return None
    if isinstance(media, MessageMediaPhoto):
        return "photo"
    if isinstance(media, MessageMediaDocument):
        doc = media.document
        if doc and doc.mime_type:
            if "video" in doc.mime_type:
                return "video"
            if "audio" in doc.mime_type:
                return "audio"
            if "sticker" in doc.mime_type or doc.mime_type == "application/x-tgsticker":
                return "sticker"
            return f"document ({doc.mime_type})"
        return "document"
    if isinstance(media, MessageMediaWebPage):
        return "webpage"
    return type(media).__name__


def _get_forward_info(fwd: Optional[MessageFwdHeader]) -> Optional[str]:
    """获取转发来源"""
    if fwd is None:
        return None
    parts: List[str] = []
    if fwd.from_name:
        parts.append(fwd.from_name)
    if fwd.from_id:
        if isinstance(fwd.from_id, PeerUser):
            parts.append(f"user:{fwd.from_id.user_id}")
        elif isinstance(fwd.from_id, PeerChannel):
            parts.append(f"channel:{fwd.from_id.channel_id}")
    return " / ".join(parts) if parts else "unknown"


class Collector:
    """Telegram 群聊消息采集器"""

    def __init__(self, config: dict, db: Database):
        self.config = config
        self.db = db
        self.client: Optional[TelegramClient] = None
        self._monitored_ids: Set[int] = set()
        self._running = False
        # 关键词告警（传入 db 以支持持久化去重）
        self.alert_manager = AlertManager(config, db=db)
        # 群组名称缓存
        self._group_names: Dict[int, str] = {}
        # 消息缺口恢复：记录最后一条消息的时间
        self._last_msg_time: Optional[datetime] = None

    async def start(self):
        """初始化 Telethon 客户端"""
        tg_cfg = self.config["telegram"]
        session_name = tg_cfg.get("session_name", "tg_monitor")

        self.client = TelegramClient(
            session_name,
            int(tg_cfg["api_id"]),
            tg_cfg["api_hash"],
        )

        phone = tg_cfg.get("phone")
        await self.client.start(phone=phone if phone else lambda: input("请输入手机号: "))

        me = await self.client.get_me()
        logger.info(f"✅ 已登录: {me.first_name} (@{me.username})")

        # 解析并注册监控群组
        await self._resolve_groups()

        # 从数据库中初始化最后消息时间（用于缺口恢复）
        await self._init_last_msg_time()

        # 加载历史告警去重记录（防止重启后重复推送）
        await self.alert_manager.load_from_db()

        return self

    async def _init_last_msg_time(self):
        """从数据库获取最新消息时间，用于启动时的缺口恢复"""
        try:
            date_range = await self.db.get_date_range()
            if date_range and date_range.get("last_msg"):
                latest = date_range["last_msg"]
                if isinstance(latest, str):
                    latest = datetime.fromisoformat(
                        latest.replace("Z", "+00:00")
                    )
                self._last_msg_time = latest
                logger.info(
                    f"📋 数据库最新消息时间: "
                    f"{self._last_msg_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
        except Exception as e:
            logger.warning(f"⚠️ 无法获取最后消息时间: {e}")

    async def _recover_gap(self):
        """重连后回填离线期间的消息缺口（P1#7 修复：改为并发回填）"""
        if not self._last_msg_time:
            logger.info("ℹ️ 无历史消息时间参考，跳过缺口恢徤")
            return

        gap_start = self._last_msg_time
        now = datetime.now(timezone.utc)
        gap_seconds = (now - gap_start).total_seconds()

        if gap_seconds < 30:
            return

        gap_hours = gap_seconds / 3600
        logger.info(
            f"🔄 检测到消息缺口: "
            f"{gap_start.strftime('%H:%M:%S')} → "
            f"{now.strftime('%H:%M:%S')} ({gap_hours:.1f}h)，并发回填 {len(self._monitored_ids)} 个群组..."
        )
        
        # P1.3 修复：提供批量插入锁，避免在并发抓取时造成 SQLite 锁竞争
        _db_lock = asyncio.Lock()

        async def _recover_one(gid: int) -> int:
            """recover a single group, return number of messages recovered"""
            try:
                entity = await self.client.get_entity(gid)
                title = getattr(entity, "title", str(gid))
                batch: list = []
                async for message in self.client.iter_messages(
                    entity,
                    offset_date=now,
                    reverse=False,
                    limit=None,
                ):
                    msg_time = message.date.replace(tzinfo=timezone.utc)
                    if msg_time <= gap_start:
                        break
                    msg_dict = await self._message_to_dict(message)
                    if msg_dict:
                        msg_dict["group_id"] = gid
                        batch.append(msg_dict)

                if batch:
                    async with _db_lock:
                        await self.db.insert_messages_batch(batch)
                    logger.info(f"   ✅ [{title}] 回填 {len(batch)} 条")
                return len(batch)
            except Exception as e:
                logger.error(
                    f"   ❌ [{self._group_names.get(gid, gid)}] 回填失败: {e}"
                )
                return 0

        # 并发回填所有群组，级别从 O(N) 串行降为 O(1) 并发
        results = await asyncio.gather(*[_recover_one(gid) for gid in self._monitored_ids])
        total_recovered = sum(results)

        if total_recovered > 0:
            logger.info(f"🔄 缺口回填完成: 共 {total_recovered} 条消息")
            self._last_msg_time = datetime.now(timezone.utc)
        else:
            logger.info("🔄 缺口期间无新消息")

    async def _resolve_groups(self):
        """解析配置中的群组，获取实际 ID"""
        groups = self.config.get("groups", [])
        if not groups:
            logger.warning("⚠️ 未配置任何监控群组")
            return

        for g in groups:
            try:
                # 支持 id 或 username
                identifier = g.get("id") or g.get("username")
                if identifier is None:
                    logger.warning(f"跳过无效群组配置: {g}")
                    continue

                entity = await self.client.get_entity(identifier)
                group_id = entity.id
                title = getattr(entity, "title", str(group_id))
                username = getattr(entity, "username", None)
                member_count = getattr(entity, "participants_count", None)

                self._monitored_ids.add(group_id)
                self._group_names[group_id] = title

                await self.db.upsert_group(
                    group_id=group_id,
                    title=title,
                    username=username,
                    member_count=member_count,
                )
                logger.info(f"📌 监控群组: {title} (ID: {group_id})")

            except Exception as e:
                logger.error(f"❌ 无法解析群组 {g}: {e}")

        logger.info(f"共监控 {len(self._monitored_ids)} 个群组")

    async def run_realtime(self):
        """实时模式：注册消息事件处理器并持续运行（带自动重连 + 缺口回填）"""
        if not self.client:
            raise RuntimeError("请先调用 start()")

        self._running = True
        chats = list(self._monitored_ids) if self._monitored_ids else None

        @self.client.on(events.NewMessage(chats=chats))
        async def on_new_message(event):
            try:
                msg_dict = await self._message_to_dict(event.message)
                if msg_dict:
                    await self.db.insert_message(msg_dict)
                    # 更新最后消息时间（用于缺口恢复）
                    msg_date = event.message.date
                    if msg_date:
                        self._last_msg_time = msg_date.replace(
                            tzinfo=timezone.utc
                        )
                    # 关键词告警检查（enabled=false 时完全跳过，不产生任何函数调用开销）
                    if self.alert_manager.enabled:
                        group_name = self._group_names.get(
                            msg_dict.get("group_id", 0), "未知群组"
                        )
                        await self.alert_manager.check_message(
                            msg_dict, group_name=group_name
                        )
                    logger.debug(
                        f"[{msg_dict.get('sender_name', '?')}] "
                        f"{(msg_dict.get('text') or '')[:60]}"
                    )
            except Exception as e:
                logger.error(f"处理消息失败: {e}", exc_info=True)

        @self.client.on(events.MessageEdited(chats=chats))
        async def on_message_edited(event):
            """消息被编辑时，同步更新数据库文本内容（FTS 由触发器自动维护）"""
            try:
                msg = event.message
                chat = await event.get_chat()
                group_id = getattr(chat, "id", None)
                if group_id is None or group_id not in self._monitored_ids:
                    return

                new_text = msg.text or msg.message or None
                media_type = _get_media_type(msg.media)
                changed = await self.db.update_message_text(
                    msg_id=msg.id,
                    group_id=group_id,
                    new_text=new_text,
                    media_type=media_type,
                )
                if changed:
                    group_name = self._group_names.get(group_id, str(group_id))
                    logger.info(
                        f"✏️ [{group_name}] 消息 #{msg.id} 被编辑: "
                        f"{(new_text or '')[:60]}"
                    )
            except Exception as e:
                logger.error(f"处理编辑消息失败: {e}", exc_info=True)

        @self.client.on(events.MessageDeleted())
        async def on_message_deleted(event):
            """
            消息被 Telegram 删除时，从数据库中进行物理删除。
            注意：Telegram 删除事件无法直接知道消息属于哪个群组，
            需要通过 channel_id 属性匹配监控列表。
            """
            try:
                msg_ids: list = list(event.deleted_ids or [])
                if not msg_ids:
                    return

                # 频道/超群删除事件带 channel_id
                channel_id = getattr(event, "channel_id", None)
                if channel_id:
                    # 仅删除属于已监控群组的消息
                    if channel_id not in self._monitored_ids:
                        return
                    deleted = await self.db.delete_messages(msg_ids, group_id=channel_id)
                    if deleted:
                        group_name = self._group_names.get(channel_id, str(channel_id))
                        logger.info(f"🗑️ [{group_name}] 已同步删除 {deleted} 条消息")
                else:
                    # 普通群删除事件：遍历所有监控群组尝试删除
                    for gid in self._monitored_ids:
                        deleted = await self.db.delete_messages(msg_ids, group_id=gid)
                        if deleted:
                            group_name = self._group_names.get(gid, str(gid))
                            logger.info(f"🗑️ [{group_name}] 已同步删除 {deleted} 条消息")
            except Exception as e:
                logger.error(f"处理删除事件失败: {e}", exc_info=True)

        # 启动时先回填缺口（处理重启后的离线时段）
        await self._recover_gap()

        # 启动时清理自动运行一次，防止告警记录表膨胀
        await self.db.cleanup_old_alerts(keep_hours=48)

        logger.info("🚀 实时监控已启动（采集+编辑/删除同步），按 Ctrl+C 停止")

        # 後台每日定期清理老消息（默认保留 90 天）
        cleanup_days = self.config.get("monitoring", {}).get("keep_days", 90)

        async def _daily_cleanup():
            while self._running:
                await asyncio.sleep(24 * 3600)  # 每 24 小时执行一次
                if not self._running:
                    break
                logger.info(f"🧹 定期清理启动 (keep_days={cleanup_days})…")
                await self.db.cleanup_old_messages(keep_days=cleanup_days)
                await self.db.cleanup_old_alerts(keep_hours=48)

        cleanup_task = asyncio.create_task(_daily_cleanup())

        # 自动重连循环（指数退避: 5s → 10s → 20s ... → 300s 上限）
        reconnect_delay = 5
        while self._running:
            try:
                if not self.client.is_connected():
                    logger.info("🔄 正在重新连接 Telegram...")
                    await self.client.connect()
                    if not await self.client.is_user_authorized():
                        logger.error("❌ 重连后账号未授权，请检查 session")
                        break
                    logger.info("✅ 重连成功")
                    reconnect_delay = 5  # 重置退避
                    # 重连后回填离线期间的消息缺口
                    await self._recover_gap()

                await self.client.run_until_disconnected()

            except KeyboardInterrupt:
                logger.info("⏹ 用户手动停止监控")
                self._running = False
                break
            except Exception as e:
                if not self._running:
                    break
                if type(e).__name__ == "FloodWaitError":
                    wait_time = getattr(e, 'seconds', reconnect_delay)
                    logger.warning(f"⚠️ 触发 FloodWait 限制，强制等待 {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                logger.warning(
                    f"⚠️ 连接断开: {e}，{reconnect_delay}s 后尝试重连..."
                )
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 300)

        self._running = False
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

    async def fetch_history(
        self,
        group_id: Optional[int] = None,
        limit: int = 1000,
        since: Optional[datetime] = None,
    ) -> int:
        """拉取历史消息"""
        if not self.client:
            raise RuntimeError("请先调用 start()")

        targets = [group_id] if group_id else list(self._monitored_ids)
        total = 0

        for gid in targets:
            try:
                entity = await self.client.get_entity(gid)
                title = getattr(entity, "title", str(gid))
                logger.info(f"⏳ 拉取 [{title}] 历史消息 (limit={limit})...")

                # C2 修复：先收集再批量 insert，避免逐条 commit 严重拖慢历史拉取
                batch: list = []
                async for message in self.client.iter_messages(
                    entity,
                    limit=limit,
                    offset_date=None,
                    reverse=True if since else False,
                ):
                    if since and message.date.replace(tzinfo=timezone.utc) < since:
                        break  # iter_messages 倒序遍历，遇到比 since 更早的消息即可停止

                    msg_dict = await self._message_to_dict(message)
                    if msg_dict:
                        msg_dict["group_id"] = gid
                        batch.append(msg_dict)

                if batch:
                    await self.db.insert_messages_batch(batch)
                logger.info(f"✅ [{title}] 拉取了 {len(batch)} 条消息")
                total += len(batch)

            except Exception as e:
                logger.error(f"❌ 拉取群组 {gid} 历史失败: {e}", exc_info=True)

        return total

    async def _message_to_dict(self, message) -> Optional[dict]:
        """将 Telethon Message 转为字典"""
        if message is None:
            return None

        # 跳过服务消息（加入/退出等）
        if message.action is not None:
            return None

        sender = await message.get_sender()
        chat = await message.get_chat()

        # 获取 group_id
        group_id = None
        if hasattr(chat, "id"):
            group_id = chat.id

        return {
            "id": message.id,
            "group_id": group_id,
            "sender_id": message.sender_id,
            "sender_name": _get_sender_name(sender),
            "text": message.text or message.message,
            "date": message.date.isoformat(timespec='seconds'),
            "media_type": _get_media_type(message.media),
            "forward_from": _get_forward_info(message.fwd_from),
            "reply_to_id": (
                message.reply_to.reply_to_msg_id
                if message.reply_to else None
            ),
            "raw_json": None,
        }

    async def stop(self):
        """停止采集器"""
        self._running = False
        if self.client:
            await self.client.disconnect()
            logger.info("🔌 已断开 Telegram 连接")
