from typing import Optional, List
from datetime import datetime, timezone

class GroupsDAO:
    def __init__(self, conn):
        self.conn = conn

    async def upsert_group(
        self, group_id: int, title: str, username: Optional[str] = None,
        member_count: Optional[int] = None
    ):
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        await self.conn.execute(
            """INSERT INTO groups (id, title, username, member_count, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 title = excluded.title,
                 username = excluded.username,
                 member_count = excluded.member_count,
                 updated_at = excluded.updated_at""",
            (group_id, title, username, member_count, now),
        )
        await self.conn.commit()

    async def get_groups(self) -> List[dict]:
        cursor = await self.conn.execute("SELECT * FROM groups ORDER BY title")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
