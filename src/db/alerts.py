import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("tg-monitor.db.alerts")

class AlertsDAO:
    def __init__(self, conn):
        self.conn = conn

    async def add_alerted_message(self, msg_key: str):
        try:
            await self.conn.execute(
                "INSERT OR IGNORE INTO alerted_messages (msg_key) VALUES (?)",
                (msg_key,),
            )
            await self.conn.commit()
        except Exception as e:
            logger.warning(f"⚠️ 写入告警记录失败: {e}")

    async def get_recent_alerted_ids(self, hours: int = 24) -> set:
        try:
            since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec='seconds')
            cursor = await self.conn.execute(
                "SELECT msg_key FROM alerted_messages WHERE alerted_at >= ?",
                (since,),
            )
            rows = await cursor.fetchall()
            return {row["msg_key"] for row in rows}
        except Exception as e:
            logger.warning(f"⚠️ 读取告警记录失败: {e}")
            return set()

    async def cleanup_old_alerts(self, keep_hours: int = 48):
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=keep_hours)).isoformat(timespec='seconds')
            await self.conn.execute(
                "DELETE FROM alerted_messages WHERE alerted_at < ?",
                (cutoff,),
            )
            await self.conn.commit()
        except Exception as e:
            logger.warning(f"⚠️ 清理告警记录失败: {e}")
