"""
数据库门面模式模块 (Facade)
保持 API 兼容性，将逻辑路由到 src/db/ 内部的具体 DAO。
"""
from typing import Optional, List, Any

from .db.core import DatabaseConnection
from .db.messages import MessagesDAO
from .db.links import LinksDAO
from .db.analytics import AnalyticsDAO
from .db.groups import GroupsDAO
from .db.alerts import AlertsDAO
from .db.tenants import TenantsDAO

class Database:
    """异步 SQLite 数据库管理器门面"""

    def __init__(self, db_path: str):
        self._core = DatabaseConnection(db_path)
        self.messages: Optional[MessagesDAO] = None
        self.links: Optional[LinksDAO] = None
        self.analytics: Optional[AnalyticsDAO] = None
        self.groups: Optional[GroupsDAO] = None
        self.alerts: Optional[AlertsDAO] = None
        self.tenants: Optional[TenantsDAO] = None

    async def connect(self):
        """连接数据库并初始化"""
        await self._core.connect()
        # 初始化所有 DAO 依赖
        conn = self._core.conn
        self.messages = MessagesDAO(conn)
        self.links = LinksDAO(conn)
        self.analytics = AnalyticsDAO(conn)
        self.groups = GroupsDAO(conn)
        self.alerts = AlertsDAO(conn)
        self.tenants = TenantsDAO(conn)

    async def close(self):
        await self._core.close()

    # ─── 租户操作 (TenantsDAO) ───
    async def add_tenant(self, api_id: int, api_hash: str, phone: str, session_name: str) -> int:
        return await self.tenants.add_tenant(api_id, api_hash, phone, session_name)

    async def get_tenants(self, active_only: bool = True) -> List[dict]:
        return await self.tenants.get_tenants(active_only)

    async def set_tenant_active(self, tenant_id: int, is_active: bool):
        return await self.tenants.set_tenant_active(tenant_id, is_active)

    # ─── 群组操作 (GroupsDAO) ───
    async def upsert_group(self, group_id: int, title: str, username: Optional[str] = None, member_count: Optional[int] = None):
        return await self.groups.upsert_group(group_id, title, username, member_count)

    async def get_groups(self) -> List[dict]:
        return await self.groups.get_groups()

    # ─── 消息操作 (MessagesDAO) ───
    async def insert_message(self, msg: dict):
        return await self.messages.insert_message(msg)

    async def insert_messages_batch(self, messages: List[dict]):
        return await self.messages.insert_messages_batch(messages)

    async def get_messages(self, group_id: Optional[int] = None, since: Optional[str] = None, until: Optional[str] = None, limit: Optional[int] = None) -> List[dict]:
        return await self.messages.get_messages(group_id, since, until, limit)

    async def get_message_count(self, group_id: Optional[int] = None, since: Optional[str] = None, until: Optional[str] = None) -> int:
        return await self.messages.get_message_count(group_id, since, until)

    async def search_messages(self, keyword: str, limit: int = 50) -> List[dict]:
        return await self.messages.search_messages(keyword, limit)

    async def update_message_text(self, msg_id: int, group_id: int, new_text: Optional[str], media_type: Optional[str] = None) -> bool:
        return await self.messages.update_message_text(msg_id, group_id, new_text, media_type)

    async def delete_messages(self, msg_ids: List[int], group_id: int) -> int:
        return await self.messages.delete_messages(msg_ids, group_id)

    async def cleanup_old_messages(self, keep_days: int = 90) -> int:
        return await self.messages.cleanup_old_messages(keep_days)

    async def export_messages(self, since: Optional[str] = None, until: Optional[str] = None, group_id: Optional[int] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[dict]:
        return await self.messages.export_messages(since, until, group_id, limit, offset)

    async def get_recent_messages(self, limit: int = 100, group_id: Optional[int] = None) -> List[dict]:
        return await self.messages.get_recent_messages(limit, group_id)

    async def get_message_trends(self, hours: int = 72) -> List[dict]:
        return await self.messages.get_message_trends(hours)

    # ─── 链接操作 (LinksDAO) ───
    async def get_links(self, group_id: Optional[int] = None, limit: int = 20, block_domains: Optional[List[str]] = None) -> List[dict]:
        return await self.links.get_links(group_id, limit, block_domains)

    async def get_links_aggregated(self, limit: int = 50, block_domains: Optional[List[str]] = None) -> List[dict]:
        return await self.links.get_links_aggregated(limit, block_domains)

    # ─── 告警去重持久化 (AlertsDAO) ───
    async def add_alerted_message(self, msg_key: str):
        return await self.alerts.add_alerted_message(msg_key)

    async def get_recent_alerted_ids(self, hours: int = 24) -> set:
        return await self.alerts.get_recent_alerted_ids(hours)

    async def cleanup_old_alerts(self, keep_hours: int = 48):
        return await self.alerts.cleanup_old_alerts(keep_hours)

    # ─── 摘要操作 (AnalyticsDAO) ───
    async def save_summary(self, group_id: Optional[int], period_start: str, period_end: str, message_count: int, content: str, model: Optional[str] = None):
        return await self.analytics.save_summary(group_id, period_start, period_end, message_count, content, model)

    async def get_latest_summaries(self, limit: int = 10) -> List[dict]:
        return await self.analytics.get_latest_summaries(limit)

    # ─── 统计图表 (AnalyticsDAO) ───
    async def get_stats(self, since: Optional[str] = None, until: Optional[str] = None) -> List[dict]:
        return await self.analytics.get_stats(since, until)

    async def get_top_senders(self, group_id: Optional[int] = None, since: Optional[str] = None, limit: int = 10) -> List[dict]:
        return await self.analytics.get_top_senders(group_id, since, limit)

    async def get_date_range(self, since: Optional[str] = None, until: Optional[str] = None) -> dict:
        return await self.analytics.get_date_range(since, until)

    async def get_heatmap_data(self, days: int = 30) -> List[dict]:
        return await self.analytics.get_heatmap_data(days)

    async def get_hourly_comparison(self) -> dict:
        return await self.analytics.get_hourly_comparison()

    async def get_group_messages(self, group_id: int, hours: int = 24, limit: int = 100) -> List[dict]:
        return await self.analytics.get_group_messages(group_id, hours, limit)

    async def get_group_trends(self, group_id: int, hours: int = 72) -> List[dict]:
        return await self.analytics.get_group_trends(group_id, hours)

    # ─── 异步任务管理 (AnalyticsDAO) ───
    async def create_summary_job(self, job_id: str, group_id: Optional[int], hours: int, mode: str):
        return await self.analytics.create_summary_job(job_id, group_id, hours, mode)

    async def update_summary_job(self, job_id: str, status: Optional[str] = None, progress: Optional[int] = None, progress_text: Optional[str] = None, result: Optional[str] = None, error_msg: Optional[str] = None):
        return await self.analytics.update_summary_job(job_id, status, progress, progress_text, result, error_msg)

    async def get_summary_job(self, job_id: str) -> Optional[dict]:
        return await self.analytics.get_summary_job(job_id)
