"""
关键词告警模块
监控消息中的敏感关键词并通过 Bot 推送告警
"""
from __future__ import annotations

import asyncio
import collections
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, List, Optional, Set

import httpx

if TYPE_CHECKING:
    from .database import Database

logger = logging.getLogger("tg-monitor.alerts")

BJT = timezone(timedelta(hours=8))


def _to_bjt(iso_str: str) -> str:
    """将 ISO 时间字符串转为北京时间 (UTC+8) 可读格式"""
    if not iso_str:
        return "?"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(BJT).strftime("%m-%d %H:%M")
    except Exception:
        return iso_str[:16].replace("T", " ")


class AlertManager:
    """关键词告警管理器（告警去重状态持久化到 SQLite，重启不丢失）"""

    def __init__(self, config: dict, db: Optional["Database"] = None):
        self.config = config
        self.db = db  # 可选数据库引用，用于持久化去重
        self.bot_token = config.get("bot", {}).get("token", "")
        self.owner_id = config.get("bot", {}).get("owner_id")
        self.alert_cfg = config.get("alerts", {})
        self.enabled = self.alert_cfg.get("enabled", False)
        self.keywords: List[str] = self.alert_cfg.get("keywords", [])
        # 编译正则模式，忽略大小写
        self._patterns = [
            re.compile(re.escape(kw), re.IGNORECASE) for kw in self.keywords
        ]
        # 内存去重缓存：使用 deque 实现 FIFO 淘汰，防止随机淘汰最近 ID 导致重复告警
        self._alerted_deque: collections.deque = collections.deque(maxlen=2000)
        self._alerted_ids: Set[str] = set()  # deque 的镜像 set，保持 O(1) 查找

    async def load_from_db(self):
        """启动时从数据库加载最近 24h 的已告警 ID，防止重启后重复推送历史消息。"""
        if self.db is None:
            return
        try:
            ids = await self.db.get_recent_alerted_ids(hours=24)
            self._alerted_ids = set(ids)
            self._alerted_deque = collections.deque(ids, maxlen=2000)
            logger.info(f"✅ 加载 {len(ids)} 条历史告警去重记录")
        except Exception as e:
            logger.warning(f"⚠️ 加载告警去重记录失败，将使用空缓存: {e}")

    async def check_message(
        self,
        msg: dict,
        group_name: str = "",
    ) -> Optional[str]:
        """
        检查消息是否命中关键词。
        如果命中，发送告警并返回匹配的关键词；否则返回 None。
        优先读数据库中的 alerts_enabled 设置（运行时可动态切换）。
        """
        # 动态读取数据库开关（如果有 db 引用）
        enabled = self.enabled
        if self.db is not None:
            try:
                db_val = await self.db.get_setting("alerts_enabled")
                if db_val is not None:
                    enabled = db_val.lower() == "true"
            except Exception:
                pass  # 读取失败时回落到 config.yaml 的值

        if not enabled or not self._patterns:
            return None

        text = msg.get("text") or ""
        if not text:
            return None

        # 去重检查（内存 + 持久化双保险）
        msg_key = f"{msg.get('group_id')}_{msg.get('id')}"
        if msg_key in self._alerted_ids:
            return None

        # 检查关键词
        matched = []
        for i, pattern in enumerate(self._patterns):
            if pattern.search(text):
                matched.append(self.keywords[i])

        if not matched:
            return None

        # 记录去重：写入 deque（自动 FIFO 淘汰旧 ID）+ 同步 set
        if len(self._alerted_deque) == self._alerted_deque.maxlen:
            # deque 满了，最早的 ID 会被自动弹出，同步从 set 中删除
            oldest = self._alerted_deque[0]
            self._alerted_ids.discard(oldest)
        self._alerted_deque.append(msg_key)
        self._alerted_ids.add(msg_key)

        # 持久化到数据库（后台执行，不阻塞主流程）
        if self.db is not None:
            try:
                await self.db.add_alerted_message(msg_key)
            except Exception as e:
                logger.warning(f"⚠️ 持久化告警去重失败: {e}")

        # 发送告警
        keywords_str = ", ".join(f"「{k}」" for k in matched)
        sender = msg.get("sender_name", "?")
        date_str = _to_bjt(msg.get("date", ""))  # 展示北京时间

        # 截断消息文本
        display_text = text[:300]
        if len(text) > 300:
            display_text += "..."

        alert_text = (
            f"🚨 *关键词告警*\n\n"
            f"🔑 命中: {keywords_str}\n"
            f"📌 群组: {group_name}\n"
            f"👤 发送者: {sender}\n"
            f"⏰ 时间: {date_str}\n\n"
            f"💬 内容:\n{display_text}"
        )

        await self._send_alert(alert_text)
        logger.info(f"🚨 告警: {keywords_str} in [{group_name}] by {sender}")

        return keywords_str

    async def _send_alert(self, text: str):
        """通过 Bot API 发送告警消息"""
        if not self.bot_token or not self.owner_id:
            logger.warning("⚠️ 告警未配置 bot_token 或 owner_id，跳过推送")
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.owner_id,
            "text": text,
            "parse_mode": "Markdown",
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.error(f"❌ 告警推送失败: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"❌ 告警推送异常: {e}")
