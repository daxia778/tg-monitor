from typing import Optional, List, Any

class LinksDAO:
    def __init__(self, conn):
        self.conn = conn

    async def get_links(
        self,
        group_id: Optional[int] = None,
        limit: int = 20,
        block_domains: Optional[List[str]] = None,
    ) -> List[dict]:
        conditions: List[str] = []
        params: List[Any] = []
        
        if block_domains:
            for domain in block_domains:
                conditions.append("LOWER(l.url) NOT LIKE ?")
                params.append(f"%{domain.lower()}%")
                
        if group_id is not None:
            conditions.append("l.group_id = ?")
            params.append(group_id)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        cursor = await self.conn.execute(
            f"""SELECT l.*, g.title as group_title
                FROM links l
                LEFT JOIN groups g ON l.group_id = g.id
                {where}
                ORDER BY l.discovered_at DESC LIMIT ?""",
            [*params, limit],
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_links_aggregated(
        self,
        limit: int = 50,
        block_domains: Optional[List[str]] = None,
    ) -> List[dict]:
        conditions: List[str] = ["1=1"]
        params: List[Any] = []
        
        if block_domains:
            for domain in block_domains:
                conditions.append("LOWER(l.url) NOT LIKE ?")
                params.append(f"%{domain.lower()}%")

        where = " AND ".join(conditions)
        cursor = await self.conn.execute(
            f"""SELECT
                  l.url,
                  COUNT(*) as total_count,
                  COUNT(DISTINCT l.group_id) as group_count,
                  GROUP_CONCAT(DISTINCT g.title) as group_titles,
                  GROUP_CONCAT(DISTINCT l.sender_name) as sender_names,
                  MIN(l.discovered_at) as first_seen,
                  MAX(l.discovered_at) as last_seen
               FROM links l
               LEFT JOIN groups g ON l.group_id = g.id
               WHERE {where}
               GROUP BY l.url
               ORDER BY total_count DESC, last_seen DESC
               LIMIT ?""",
            [*params, limit],
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
