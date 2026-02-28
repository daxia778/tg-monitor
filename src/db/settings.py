"""
设置 KV 存储 DAO
用于存储用户运行时可调整的系统设置（如告警开关）
"""
from typing import Optional


class SettingsDAO:
    """轻量级 Key-Value 设置存储（持久化到 SQLite settings 表）"""

    def __init__(self, conn):
        self.conn = conn

    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """读取设置值"""
        cursor = await self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row["value"] if row else default

    async def get_bool(self, key: str, default: bool = False) -> bool:
        """读取布尔设置"""
        val = await self.get(key)
        if val is None:
            return default
        return val.lower() in ("1", "true", "yes", "on")

    async def set(self, key: str, value: str):
        """写入设置值"""
        await self.conn.execute(
            """INSERT INTO settings (key, value, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET
                 value = excluded.value,
                 updated_at = excluded.updated_at""",
            (key, value),
        )
        await self.conn.commit()

    async def set_bool(self, key: str, value: bool):
        """写入布尔设置"""
        await self.set(key, "true" if value else "false")

    async def all(self) -> dict:
        """读取所有设置"""
        cursor = await self.conn.execute("SELECT key, value FROM settings")
        rows = await cursor.fetchall()
        return {r["key"]: r["value"] for r in rows}
