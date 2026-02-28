from typing import Optional, List, Dict, Any

class TenantsDAO:
    def __init__(self, conn):
        self.conn = conn

    async def add_tenant(self, api_id: int, api_hash: str, phone: str, session_name: str) -> int:
        cursor = await self.conn.execute(
            """INSERT INTO tenants (api_id, api_hash, phone, session_name, is_active)
               VALUES (?, ?, ?, ?, 1)""",
            (api_id, api_hash, phone, session_name),
        )
        await self.conn.commit()
        return cursor.lastrowid

    async def get_tenants(self, active_only: bool = True) -> List[dict]:
        where = "WHERE is_active = 1" if active_only else ""
        cursor = await self.conn.execute(f"SELECT * FROM tenants {where} ORDER BY created_at")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def set_tenant_active(self, tenant_id: int, is_active: bool):
        await self.conn.execute(
            "UPDATE tenants SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, tenant_id)
        )
        await self.conn.commit()
