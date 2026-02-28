"""
多租户 Session Worker Pool
管理多个 Telethon 客户端的并发监控，支持动态新增、暂停、销毁
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger("tg-monitor.session_pool")


class SessionWorker:
    """代表单个租户的 Telethon 会话工作者"""

    def __init__(self, tenant: dict, config: dict, db_path: str):
        self.tenant = tenant
        self.config = config
        self.db_path = db_path
        self.tenant_id: int = tenant["id"]
        self.session_name: str = tenant["session_name"]
        self.phone: str = tenant.get("phone", "")

        self._task: Optional[asyncio.Task] = None
        self._client = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    async def start(self):
        """启动该租户的采集循环"""
        if self.is_running:
            logger.warning(f"[Tenant #{self.tenant_id}] 已在运行，跳过")
            return

        self._running = True
        self._task = asyncio.create_task(self._run(), name=f"tenant-{self.tenant_id}")
        logger.info(f"[Tenant #{self.tenant_id} | {self.phone}] ✅ Worker 已启动")

    async def stop(self):
        """停止该租户的采集循环"""
        self._running = False
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"[Tenant #{self.tenant_id}] ⏹ Worker 已停止")

    async def _run(self):
        """内部: 初始化 Telethon 并运行实时监控"""
        try:
            from .database import Database
            from .collector import Collector

            db = Database(self.db_path)
            await db.connect()

            # 将租户 api_id / api_hash 注入 config
            cfg = dict(self.config)
            cfg["telegram"] = dict(self.config.get("telegram", {}))
            if self.tenant.get("api_id"):
                cfg["telegram"]["api_id"] = self.tenant["api_id"]
            if self.tenant.get("api_hash"):
                cfg["telegram"]["api_hash"] = self.tenant["api_hash"]
            if self.tenant.get("phone"):
                cfg["telegram"]["phone"] = self.tenant["phone"]
            cfg["telegram"]["session_name"] = self.session_name

            collector = Collector(cfg, db)
            await collector.start()
            self._client = collector.client

            await collector.run_realtime()
        except asyncio.CancelledError:
            logger.info(f"[Tenant #{self.tenant_id}] CancelledError, 正常停止")
        except Exception as e:
            logger.error(f"[Tenant #{self.tenant_id}] Worker 异常: {e}", exc_info=True)
            self._running = False


class SessionPool:
    """多租户会话调度池"""

    def __init__(self, config: dict, db_path: str):
        self.config = config
        self.db_path = db_path
        self._workers: Dict[int, SessionWorker] = {}

    async def start_all(self):
        """从数据库加载所有活跃租户并同时启动"""
        from .database import Database

        db = Database(self.db_path)
        await db.connect()
        tenants = await db.get_tenants(active_only=True)
        await db.close()

        if not tenants:
            logger.warning("⚠️ 无活跃租户，Pool 未启动任何 Worker")
            return

        logger.info(f"🚀 SessionPool 启动 {len(tenants)} 个租户 Worker...")
        await asyncio.gather(*[self._start_tenant(t) for t in tenants])

    async def start_tenant(self, tenant_id: int):
        """动态启动单个租户"""
        from .database import Database

        db = Database(self.db_path)
        await db.connect()
        tenants = await db.get_tenants(active_only=False)
        await db.close()

        t = next((t for t in tenants if t["id"] == tenant_id), None)
        if t is None:
            logger.error(f"[Tenant #{tenant_id}] 不存在")
            return
        await self._start_tenant(t)

    async def _start_tenant(self, tenant: dict):
        tid = tenant["id"]
        if tid in self._workers and self._workers[tid].is_running:
            logger.info(f"[Tenant #{tid}] 已在运行")
            return
        worker = SessionWorker(tenant, self.config, self.db_path)
        self._workers[tid] = worker
        await worker.start()

    async def stop_tenant(self, tenant_id: int):
        """停止单个租户 Worker"""
        if tenant_id in self._workers:
            await self._workers[tenant_id].stop()
            del self._workers[tenant_id]

    async def stop_all(self):
        """停止所有 Worker"""
        if not self._workers:
            return
        logger.info(f"⏹ 停止所有 {len(self._workers)} 个 Worker...")
        await asyncio.gather(*[w.stop() for w in self._workers.values()])
        self._workers.clear()

    def status(self) -> Dict[int, Any]:
        """返回每个 Worker 的运行状态"""
        return {
            tid: {
                "tenant_id": tid,
                "phone": w.phone,
                "session_name": w.session_name,
                "running": w.is_running,
            }
            for tid, w in self._workers.items()
        }
