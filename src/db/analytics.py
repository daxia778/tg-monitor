from typing import Optional, List, Any
from datetime import datetime, timezone, timedelta

class AnalyticsDAO:
    def __init__(self, conn):
        self.conn = conn

    async def save_summary(
        self,
        group_id: Optional[int],
        period_start: str,
        period_end: str,
        message_count: int,
        content: str,
        model: Optional[str] = None,
    ):
        await self.conn.execute(
            """INSERT INTO summaries
               (group_id, period_start, period_end, message_count, content, model)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (group_id, period_start, period_end, message_count, content, model),
        )
        await self.conn.commit()

    async def get_latest_summaries(self, limit: int = 10) -> List[dict]:
        cursor = await self.conn.execute(
            """SELECT s.*, g.title as group_title
               FROM summaries s
               LEFT JOIN groups g ON s.group_id = g.id
               WHERE s.content NOT LIKE '%⚠️ 摘要生成失败%' AND s.content NOT LIKE '%❌%'
               ORDER BY s.created_at DESC LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_stats(
        self, since: Optional[str] = None, until: Optional[str] = None,
    ) -> List[dict]:
        conditions: List[str] = []
        params: List[Any] = []
        if since:
            conditions.append("m.date >= ?")
            params.append(since)
        if until:
            conditions.append("m.date <= ?")
            params.append(until)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        cursor = await self.conn.execute(
            f"""SELECT
                  g.title,
                  m.group_id,
                  COUNT(*) as message_count,
                  COUNT(DISTINCT COALESCE(CAST(m.sender_id AS TEXT), m.sender_name)) as active_users,
                  MIN(m.date) as first_msg,
                  MAX(m.date) as last_msg
                FROM messages m
                LEFT JOIN groups g ON m.group_id = g.id
                {where}
                GROUP BY m.group_id
                ORDER BY message_count DESC""",
            params,
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_top_senders(
        self,
        group_id: Optional[int] = None,
        since: Optional[str] = None,
        limit: int = 10,
    ) -> List[dict]:
        conditions: List[str] = []
        params: List[Any] = []
        if group_id is not None:
            conditions.append("group_id = ?")
            params.append(group_id)
        if since:
            conditions.append("date >= ?")
            params.append(since)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        cursor = await self.conn.execute(
            f"""SELECT sender_name, sender_id, COUNT(*) as msg_count
                FROM messages
                {where}
                GROUP BY sender_id
                ORDER BY msg_count DESC LIMIT ?""",
            [*params, limit],
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_date_range(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> dict:
        conditions: List[str] = []
        params: List[Any] = []
        if since:
            conditions.append("date >= ?")
            params.append(since)
        if until:
            conditions.append("date <= ?")
            params.append(until)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        cursor = await self.conn.execute(
            f"""SELECT MIN(date) as first_msg,
                       MAX(date) as last_msg,
                       COUNT(*) as total
                FROM messages {where}""",
            params,
        )
        row = await cursor.fetchone()
        return dict(row)

    async def get_heatmap_data(
        self, days: int = 30,
    ) -> List[dict]:
        now = datetime.now(timezone.utc)
        since = (now - timedelta(days=days)).isoformat(timespec='seconds')
        cursor = await self.conn.execute(
            """SELECT
                 CAST(strftime('%w', date) AS INTEGER) as dow,
                 CAST(strftime('%H', date) AS INTEGER) as hour,
                 COUNT(*) as count
               FROM messages
               WHERE date >= ?
               GROUP BY dow, hour
               ORDER BY dow, hour""",
            (since,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_hourly_comparison(
        self,
    ) -> dict:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)

        cursor_today = await self.conn.execute(
            """SELECT CAST(strftime('%H', date) AS INTEGER) as hour,
                      COUNT(*) as count
               FROM messages WHERE date >= ?
               GROUP BY hour ORDER BY hour""",
            (today_start.isoformat(timespec='seconds'),),
        )
        today = [dict(r) for r in await cursor_today.fetchall()]

        cursor_yesterday = await self.conn.execute(
            """SELECT CAST(strftime('%H', date) AS INTEGER) as hour,
                      COUNT(*) as count
               FROM messages WHERE date >= ? AND date < ?
               GROUP BY hour ORDER BY hour""",
            (yesterday_start.isoformat(timespec='seconds'), today_start.isoformat(timespec='seconds')),
        )
        yesterday = [dict(r) for r in await cursor_yesterday.fetchall()]

        return {"today": today, "yesterday": yesterday}

    async def get_group_messages(
        self,
        group_id: int,
        hours: int = 24,
        limit: int = 100,
    ) -> List[dict]:
        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')
        cursor = await self.conn.execute(
            """SELECT m.*, g.title as group_title
               FROM messages m
               LEFT JOIN groups g ON m.group_id = g.id
               WHERE m.group_id = ? AND m.date >= ?
               ORDER BY m.date DESC LIMIT ?""",
            (group_id, since, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_group_trends(
        self,
        group_id: int,
        hours: int = 72,
    ) -> List[dict]:
        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')
        cursor = await self.conn.execute(
            """SELECT
                 strftime('%Y-%m-%dT%H:00:00', date) as hour,
                 COUNT(*) as count
               FROM messages
               WHERE group_id = ? AND date >= ?
               GROUP BY hour ORDER BY hour ASC""",
            (group_id, since),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
