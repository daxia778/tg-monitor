import asyncio
import re
from typing import Optional, List, Any
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("tg-monitor.db.messages")

URL_PATTERN = re.compile(
    r"https?://[^\s<>\"')\]，。！？、；：）》」』】\u200b]+"
)

class MessagesDAO:
    def __init__(self, conn):
        self.conn = conn

    async def insert_message(self, msg: dict):
        try:
            await self.conn.execute(
                """INSERT OR IGNORE INTO messages
                   (id, group_id, sender_id, sender_name, text, date,
                    media_type, forward_from, reply_to_id, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    msg["id"], msg["group_id"], msg.get("sender_id"),
                    msg.get("sender_name"), msg.get("text"), msg["date"],
                    msg.get("media_type"), msg.get("forward_from"),
                    msg.get("reply_to_id"), msg.get("raw_json"),
                ),
            )
            if msg.get("text"):
                urls = URL_PATTERN.findall(msg["text"])
                for url in urls:
                    await self.conn.execute(
                        """INSERT OR IGNORE INTO links (url, message_id, group_id, sender_name,
                                             context, discovered_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            url, msg["id"], msg["group_id"],
                            msg.get("sender_name"),
                            msg["text"][:200],
                            msg["date"],
                        ),
                    )
            await self.conn.commit()
        except Exception as e:
            logger.error(
                f"❌ 插入消息失败 (msg_id={msg.get('id')}, "
                f"group_id={msg.get('group_id')}): {e}"
            )

    async def insert_messages_batch(self, messages: List[dict]):
        if not messages:
            return
        try:
            for msg in messages:
                await self.conn.execute(
                    """INSERT OR IGNORE INTO messages
                       (id, group_id, sender_id, sender_name, text, date,
                        media_type, forward_from, reply_to_id, raw_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        msg["id"], msg["group_id"], msg.get("sender_id"),
                        msg.get("sender_name"), msg.get("text"), msg["date"],
                        msg.get("media_type"), msg.get("forward_from"),
                        msg.get("reply_to_id"), msg.get("raw_json"),
                    ),
                )
                if msg.get("text"):
                    urls = URL_PATTERN.findall(msg["text"])
                    for url in urls:
                        await self.conn.execute(
                            """INSERT OR IGNORE INTO links (url, message_id, group_id,
                                                 sender_name, context, discovered_at)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (
                                url, msg["id"], msg["group_id"],
                                msg.get("sender_name"),
                                msg["text"][:200],
                                msg["date"],
                            ),
                        )
            await self.conn.commit()
            logger.info(f"✅ 批量插入 {len(messages)} 条消息")
        except Exception as e:
            logger.error(f"❌ 批量插入失败: {e}")

    async def get_messages(
        self,
        group_id: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[dict]:
        conditions = []
        params: List[Any] = []

        if group_id is not None:
            conditions.append("group_id = ?")
            params.append(group_id)
        if since:
            conditions.append("date >= ?")
            params.append(since)
        if until:
            conditions.append("date <= ?")
            params.append(until)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        limit_clause = f"LIMIT {limit}" if limit else ""
        query = f"SELECT * FROM messages {where} ORDER BY date ASC {limit_clause}"

        cursor = await self.conn.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_message_count(
        self,
        group_id: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> int:
        conditions: List[str] = []
        params: List[Any] = []
        if group_id is not None:
            conditions.append("group_id = ?")
            params.append(group_id)
        if since:
            conditions.append("date >= ?")
            params.append(since)
        if until:
            conditions.append("date <= ?")
            params.append(until)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        cursor = await self.conn.execute(
            f"SELECT COUNT(*) as cnt FROM messages {where}", params
        )
        row = await cursor.fetchone()
        return row["cnt"]

    async def search_messages(self, keyword: str, limit: int = 50) -> List[dict]:
        try:
            cursor = await self.conn.execute(
                """SELECT m.*, g.title as group_title
                   FROM messages m
                   JOIN messages_fts fts ON m.rowid = fts.rowid
                   LEFT JOIN groups g ON m.group_id = g.id
                   WHERE messages_fts MATCH ?
                   ORDER BY m.date DESC LIMIT ?""",
                (keyword, limit),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception:
            cursor = await self.conn.execute(
                """SELECT m.*, g.title as group_title
                   FROM messages m
                   LEFT JOIN groups g ON m.group_id = g.id
                   WHERE m.text LIKE ?
                   ORDER BY m.date DESC LIMIT ?""",
                (f"%{keyword}%", limit),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update_message_text(
        self,
        msg_id: int,
        group_id: int,
        new_text: Optional[str],
        media_type: Optional[str] = None,
    ) -> bool:
        try:
            cursor = await self.conn.execute(
                """UPDATE messages
                   SET text = ?, media_type = COALESCE(?, media_type)
                   WHERE id = ? AND group_id = ?
                   AND text IS NOT ?""",
                (new_text, media_type, msg_id, group_id, new_text),
            )
            await self.conn.commit()
            changed = cursor.rowcount > 0
            if changed:
                logger.debug(f"✏️ 消息已更新 (id={msg_id}, group={group_id})")
            return changed
        except Exception as e:
            logger.error(f"❌ 更新消息失败 (id={msg_id}): {e}")
            return False

    async def delete_messages(
        self,
        msg_ids: List[int],
        group_id: int,
    ) -> int:
        if not msg_ids:
            return 0
        try:
            placeholders = ",".join("?" * len(msg_ids))
            cursor = await self.conn.execute(
                f"""SELECT rowid, text, sender_name FROM messages
                    WHERE id IN ({placeholders}) AND group_id = ?""",
                [*msg_ids, group_id],
            )
            existing = await cursor.fetchall()

            if not existing:
                return 0

            for row in existing:
                try:
                    await self.conn.execute(
                        """INSERT INTO messages_fts(messages_fts, rowid, text, sender_name)
                           VALUES ('delete', ?, ?, ?)""",
                        (row["rowid"], row["text"] or "", row["sender_name"] or ""),
                    )
                except Exception:
                    pass

            cursor2 = await self.conn.execute(
                f"DELETE FROM messages WHERE id IN ({placeholders}) AND group_id = ?",
                [*msg_ids, group_id],
            )
            await self.conn.commit()
            deleted = cursor2.rowcount
            logger.info(f"🗑️ 已删除 {deleted} 条消息 (group={group_id}, ids={msg_ids[:5]}{'...' if len(msg_ids)>5 else ''})")
            return deleted
        except Exception as e:
            logger.error(f"❌ 删除消息失败 (group={group_id}): {e}")
            return 0

    async def cleanup_old_messages(
        self,
        keep_days: int = 90,
    ) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat(timespec='seconds')
        total_deleted_links = 0
        total_deleted_msgs = 0
        try:
            while True:
                cursor = await self.conn.execute(
                    "DELETE FROM links WHERE id IN (SELECT id FROM links WHERE discovered_at < ? LIMIT 5000)", 
                    (cutoff,)
                )
                await self.conn.commit()
                deleted = cursor.rowcount
                total_deleted_links += deleted
                if deleted < 5000:
                    break
                await asyncio.sleep(0.1)

            while True:
                cursor = await self.conn.execute(
                    "DELETE FROM messages WHERE rowid IN (SELECT rowid FROM messages WHERE date < ? LIMIT 5000)", 
                    (cutoff,)
                )
                await self.conn.commit()
                deleted = cursor.rowcount
                total_deleted_msgs += deleted
                if deleted < 5000:
                    break
                await asyncio.sleep(0.1)

            logger.info(f"🧹 清理超期数据: {total_deleted_msgs} 条消息, {total_deleted_links} 条链接 (cutoff={cutoff[:10]})")
            return total_deleted_msgs
        except Exception as e:
            logger.error(f"❌ 分批清理老数据失败: {e}")
            return total_deleted_msgs

    async def export_messages(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        group_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[dict]:
        conditions = []
        params = []
        if group_id:
            conditions.append("m.group_id = ?")
            params.append(group_id)
        if since:
            conditions.append("m.date >= ?")
            params.append(since)
        if until:
            conditions.append("m.date <= ?")
            params.append(until)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        limit_clause = f"LIMIT {int(limit)}" if limit else ""
        cursor = await self.conn.execute(
            f"""SELECT m.id, m.group_id, g.title as group_title,
                       m.sender_name, m.text, m.date,
                       m.media_type, m.forward_from
                FROM messages m
                LEFT JOIN groups g ON m.group_id = g.id
                {where}
                ORDER BY m.date ASC {limit_clause}""",
            params,
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_recent_messages(
        self,
        limit: int = 100,
        group_id: Optional[int] = None,
    ) -> List[dict]:
        conditions = []
        params: List[Any] = []
        if group_id is not None:
            conditions.append("group_id = ?")
            params.append(group_id)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(limit)
        cursor = await self.conn.execute(
            f"SELECT * FROM messages {where} ORDER BY date DESC LIMIT ?",
            params,
        )
        rows = await cursor.fetchall()
        messages = [dict(r) for r in rows]
        messages.reverse()
        return messages

    async def get_message_trends(self, hours: int = 72) -> List[dict]:
        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')
        cursor = await self.conn.execute(
            """SELECT strftime('%Y-%m-%dT%H:00:00', date) as hour, COUNT(*) as count
               FROM messages WHERE date >= ?
               GROUP BY hour ORDER BY hour ASC""",
            (since,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
