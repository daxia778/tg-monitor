"""
数据库模块
使用 SQLite 存储群聊消息、链接和摘要
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite
import logging

logger = logging.getLogger("tg-monitor.database")

# URL 提取正则
URL_PATTERN = re.compile(
    r"https?://[^\s<>\"')\]，。！？、；：）》」』】\u200b]+"
)

# 不再使用硬编码域名过滤，改为在方法中动态使用参数化查询

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS groups (
    id           INTEGER PRIMARY KEY,
    title        TEXT NOT NULL,
    username     TEXT,
    member_count INTEGER,
    updated_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER NOT NULL,
    group_id     INTEGER NOT NULL,
    sender_id    INTEGER,
    sender_name  TEXT,
    text         TEXT,
    date         TEXT NOT NULL,
    media_type   TEXT,
    forward_from TEXT,
    reply_to_id  INTEGER,
    raw_json     TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (id, group_id)
);

CREATE TABLE IF NOT EXISTS links (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    url          TEXT NOT NULL,
    message_id   INTEGER NOT NULL,
    group_id     INTEGER NOT NULL,
    sender_name  TEXT,
    context      TEXT,
    discovered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS summaries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id     INTEGER,
    period_start TEXT NOT NULL,
    period_end   TEXT NOT NULL,
    message_count INTEGER NOT NULL,
    content      TEXT NOT NULL,
    model        TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_group_date ON messages(group_id, date);
CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date);
CREATE INDEX IF NOT EXISTS idx_links_group ON links(group_id, discovered_at);
CREATE INDEX IF NOT EXISTS idx_summaries_period ON summaries(period_start, period_end);

-- 链接去重索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_links_unique
    ON links(url, group_id, message_id);

CREATE INDEX IF NOT EXISTS idx_links_url ON links(url);

CREATE TABLE IF NOT EXISTS alerted_messages (
    msg_key      TEXT PRIMARY KEY,
    alerted_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# FTS5 全文搜索（分为独立语句，避免 executescript 的排他锁）
FTS_CREATE_SQL = """CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    text,
    sender_name,
    content='messages',
    content_rowid='rowid'
)"""

FTS_TRIGGER_SQL = """CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, text, sender_name)
    VALUES (new.rowid, new.text, new.sender_name);
END"""

# FTS5 UPDATE 触发器：消息编辑时同步更新全文索引
FTS_TRIGGER_UPDATE_SQL = """CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages
WHEN new.text IS NOT old.text BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, text, sender_name)
    VALUES ('delete', old.rowid, old.text, old.sender_name);
    INSERT INTO messages_fts(rowid, text, sender_name)
    VALUES (new.rowid, new.text, new.sender_name);
END"""

# ─── P1#8: 增量迁移系统 ─────────────────────────────────────────────────
# 每个元素为 (version: int, description: str, sql: str)
# version 必须单调递增、不得修改已经发布的 version。
MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "Add alerted_messages table for alert deduplication",
        """CREATE TABLE IF NOT EXISTS alerted_messages (
            msg_key    TEXT PRIMARY KEY,
            alerted_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
    ),
    # 未来新增字段示例（注释掉）：
    # (
    #     2,
    #     "Add sentiment column to messages",
    #     "ALTER TABLE messages ADD COLUMN sentiment TEXT",
    # ),
]


class Database:
    """异步 SQLite 数据库管理器"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """连接数据库并初始化 schema"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        # 防止并发锁冲突（等待 5 秒）
        await self._db.execute("PRAGMA busy_timeout=5000")
        # 开启 WAL 模式：提升并发性能和崩溃恢复能力
        await self._db.execute("PRAGMA journal_mode=WAL")
        # ── 性能调优 ──────────────────────────────────────
        # 32 MB 页缓存：减少热数据查询的磁盘 I/O（对摘要、统计、搜索查询效果显著）
        await self._db.execute("PRAGMA cache_size = -32000")
        # 临时表（ORDER BY/GROUP BY 中间结果）放内存，避免落盘
        await self._db.execute("PRAGMA temp_store = MEMORY")
        # WAL 模式下 NORMAL 同步足够安全（FULL 是 WAL 以外模式才需要）
        await self._db.execute("PRAGMA synchronous = NORMAL")
        # WAL 文件超过 1000 页时自动 checkpoint，防止 WAL 无限膨胀拖慢写入
        await self._db.execute("PRAGMA wal_autocheckpoint = 1000")
        # 逐条执行 schema（避免 executescript 的排他锁）
        for stmt in SCHEMA_SQL.split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                await self._db.execute(stmt)
            except aiosqlite.OperationalError as e:
                # 只忽略「已存在」类型的错误，其他错误（磁盘满、权限等）需要抛出
                if "already exists" not in str(e).lower():
                    logger.error(f"❌ Schema 初始化失败: {e}\nSQL: {stmt[:120]}")
                    raise
            except aiosqlite.IntegrityError as e:
                # UNIQUE INDEX 创建时，若已有重复数据会触发 IntegrityError
                # 先去重，再重试创建索引
                if "idx_links_unique" in stmt:
                    logger.warning("⚠️ links 表存在重复数据，正在去重后重建唯一索引...")
                    await self._db.execute("""
                        DELETE FROM links WHERE rowid NOT IN (
                            SELECT MIN(rowid) FROM links
                            GROUP BY url, group_id, message_id
                        )
                    """)
                    await self._db.commit()
                    await self._db.execute(stmt)  # 去重后重试
                    logger.info("✅ links 表去重完成，唯一索引已建立")
                else:
                    logger.warning(f"⚠️ Schema 语句跳过（IntegrityError）: {e}\nSQL: {stmt[:120]}")
        await self._db.commit()
        # 初始化 FTS5 全文搜索
        try:
            await self._db.execute(FTS_CREATE_SQL)
            await self._db.execute(FTS_TRIGGER_SQL)
            await self._db.execute(FTS_TRIGGER_UPDATE_SQL)
            await self._db.commit()
            # 检查是否需要重建索引（首次创建 FTS 表时）
            cursor = await self._db.execute(
                "SELECT COUNT(*) as cnt FROM messages_fts"
            )
            fts_count = (await cursor.fetchone())["cnt"]
            cursor2 = await self._db.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE text IS NOT NULL"
            )
            msg_count = (await cursor2.fetchone())["cnt"]
            if fts_count == 0 and msg_count > 0:
                logger.info(f"🔄 重建 FTS 索引 ({msg_count} 条消息)...")
                await self._db.execute(
                    "INSERT INTO messages_fts(messages_fts) VALUES('rebuild')"
                )
                await self._db.commit()  # P0 修复：重建后必须 commit 才能落盘
                logger.info("✅ FTS 索引重建完成")
        except Exception as e:
            logger.warning(f"⚠️ FTS5 初始化失败（回退到 LIKE 搜索）: {e}")
        # 初始化并运行增量迁移（P1#8）
        await self._run_migrations()
        logger.info("✅ 数据库已连接 (WAL 模式)")

    async def _run_migrations(self):
        """运行增量迁移（P1#8）。
        - 创建 schema_version 元数据表（若不存在）
        - 按 version 顺序应用尚未执行过的迁移
        - 每次迁移执行后立即内嵌 commit，确保原子性
        """
        # 确保元数据表存在
        await self._db.execute(
            """CREATE TABLE IF NOT EXISTS schema_version (
                version    INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now')),
                description TEXT
            )"""
        )
        await self._db.commit()

        # 读取已应用的最高版本
        cursor = await self._db.execute(
            "SELECT COALESCE(MAX(version), 0) as ver FROM schema_version"
        )
        current = (await cursor.fetchone())["ver"]

        pending = [(v, d, s) for v, d, s in MIGRATIONS if v > current]
        if not pending:
            return

        logger.info(f"🔄 应用 {len(pending)} 个迁移（当前版本: {current}）...")
        for version, description, sql in sorted(pending, key=lambda x: x[0]):
            try:
                await self._db.execute(sql)
                await self._db.execute(
                    "INSERT OR IGNORE INTO schema_version (version, description) VALUES (?, ?)",
                    (version, description),
                )
                await self._db.commit()
                logger.info(f"   ✅ v{version}: {description}")
            except (aiosqlite.OperationalError, aiosqlite.IntegrityError) as e:
                # 如果表/列已存在，视为已应用成功
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    await self._db.execute(
                        "INSERT OR IGNORE INTO schema_version (version, description) VALUES (?, ?)",
                        (version, description),
                    )
                    await self._db.commit()
                    logger.info(f"   ⚠️ v{version}: 已存在，跳过")
                else:
                    logger.error(f"   ❌ v{version} 迁移失败: {e}")
                    raise

    async def close(self):
        if self._db:
            await self._db.close()

    # ─── 群组操作 ───

    async def upsert_group(
        self, group_id: int, title: str, username: Optional[str] = None,
        member_count: Optional[int] = None
    ):
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        await self._db.execute(
            """INSERT INTO groups (id, title, username, member_count, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 title = excluded.title,
                 username = excluded.username,
                 member_count = excluded.member_count,
                 updated_at = excluded.updated_at""",
            (group_id, title, username, member_count, now),
        )
        await self._db.commit()

    async def get_groups(self) -> List[dict]:
        cursor = await self._db.execute("SELECT * FROM groups ORDER BY title")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ─── 消息操作 ───

    async def insert_message(self, msg: dict):
        """插入单条消息，同时自动提取链接。失败时记录日志但不中断。"""
        try:
            await self._db.execute(
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

            # 自动提取链接
            if msg.get("text"):
                urls = URL_PATTERN.findall(msg["text"])
                for url in urls:
                    await self._db.execute(
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

            await self._db.commit()
        except Exception as e:
            logger.error(
                f"❌ 插入消息失败 (msg_id={msg.get('id')}, "
                f"group_id={msg.get('group_id')}): {e}"
            )

    async def insert_messages_batch(self, messages: List[dict]):
        """批量插入消息（单事务，性能远优于逐条 commit）"""
        if not messages:
            return
        try:
            for msg in messages:
                await self._db.execute(
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
                # 提取链接
                if msg.get("text"):
                    urls = URL_PATTERN.findall(msg["text"])
                    for url in urls:
                        await self._db.execute(
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
            await self._db.commit()
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
        """查询消息（按时间范围，默认不限条数）"""
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

        cursor = await self._db.execute(query, params)
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
        cursor = await self._db.execute(
            f"SELECT COUNT(*) as cnt FROM messages {where}", params
        )
        row = await cursor.fetchone()
        return row["cnt"]

    async def search_messages(self, keyword: str, limit: int = 50) -> List[dict]:
        """全文搜索消息（优先使用 FTS5，回退到 LIKE）"""
        try:
            # 尝试 FTS5 搜索
            cursor = await self._db.execute(
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
            # 回退到 LIKE 搜索
            cursor = await self._db.execute(
                """SELECT m.*, g.title as group_title
                   FROM messages m
                   LEFT JOIN groups g ON m.group_id = g.id
                   WHERE m.text LIKE ?
                   ORDER BY m.date DESC LIMIT ?""",
                (f"%{keyword}%", limit),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ─── 链接操作 ───

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
        cursor = await self._db.execute(
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
        """按 URL 聚合链接，统计出现次数、来源群组和发送者"""
        conditions: List[str] = ["1=1"]
        params: List[Any] = []
        
        if block_domains:
            for domain in block_domains:
                conditions.append("LOWER(l.url) NOT LIKE ?")
                params.append(f"%{domain.lower()}%")

        where = " AND ".join(conditions)
        cursor = await self._db.execute(
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

    # ─── 告警去重持久化 ───

    async def add_alerted_message(self, msg_key: str):
        """记录已告警的消息 key，防止重启后重复推送"""
        try:
            await self._db.execute(
                "INSERT OR IGNORE INTO alerted_messages (msg_key) VALUES (?)",
                (msg_key,),
            )
            await self._db.commit()
        except Exception as e:
            logger.warning(f"⚠️ 写入告警记录失败: {e}")

    async def get_recent_alerted_ids(self, hours: int = 24) -> set:
        """加载最近 N 小时内已告警的 msg_key 集合（进程重启后恢复去重状态）"""
        try:
            since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec='seconds')
            cursor = await self._db.execute(
                "SELECT msg_key FROM alerted_messages WHERE alerted_at >= ?",
                (since,),
            )
            rows = await cursor.fetchall()
            return {row["msg_key"] for row in rows}
        except Exception as e:
            logger.warning(f"⚠️ 读取告警记录失败: {e}")
            return set()

    async def cleanup_old_alerts(self, keep_hours: int = 48):
        """清理超期告警记录，防止表无限增长"""
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=keep_hours)).isoformat(timespec='seconds')
            await self._db.execute(
                "DELETE FROM alerted_messages WHERE alerted_at < ?",
                (cutoff,),
            )
            await self._db.commit()
        except Exception as e:
            logger.warning(f"⚠️ 清理告警记录失败: {e}")

    # ─── 摘要操作 ───

    async def save_summary(
        self,
        group_id: Optional[int],
        period_start: str,
        period_end: str,
        message_count: int,
        content: str,
        model: Optional[str] = None,
    ):
        await self._db.execute(
            """INSERT INTO summaries
               (group_id, period_start, period_end, message_count, content, model)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (group_id, period_start, period_end, message_count, content, model),
        )
        await self._db.commit()

    async def get_latest_summaries(self, limit: int = 10) -> List[dict]:
        cursor = await self._db.execute(
            """SELECT s.*, g.title as group_title
               FROM summaries s
               LEFT JOIN groups g ON s.group_id = g.id
               WHERE s.content NOT LIKE '%⚠️ 摘要生成失败%' AND s.content NOT LIKE '%❌%'
               ORDER BY s.created_at DESC LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ─── 统计 ───

    async def get_stats(
        self, since: Optional[str] = None, until: Optional[str] = None,
    ) -> List[dict]:
        """按群组统计消息数和活跃用户数"""
        conditions: List[str] = []
        params: List[Any] = []
        if since:
            conditions.append("m.date >= ?")
            params.append(since)
        if until:
            conditions.append("m.date <= ?")
            params.append(until)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        cursor = await self._db.execute(
            f"""SELECT
                  g.title,
                  m.group_id,
                  COUNT(*) as message_count,
                  -- DB3 修复：sender_id 为 NULL 时（匿名频道消息）回退到 sender_name
                  -- 避免 COUNT(DISTINCT NULL) 将匿名发言者全部漏计
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
        cursor = await self._db.execute(
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
        """获取消息的实际时间范围"""
        conditions: List[str] = []
        params: List[Any] = []
        if since:
            conditions.append("date >= ?")
            params.append(since)
        if until:
            conditions.append("date <= ?")
            params.append(until)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        cursor = await self._db.execute(
            f"""SELECT MIN(date) as first_msg,
                       MAX(date) as last_msg,
                       COUNT(*) as total
                FROM messages {where}""",
            params,
        )
        row = await cursor.fetchone()
        return dict(row)

    # ─── 热力图 & 对比 ───

    async def get_heatmap_data(
        self, days: int = 30,
    ) -> List[dict]:
        """按星期×小时统计消息分布（用于活跃度热力图）"""
        now = datetime.now(timezone.utc)
        since = (now - timedelta(days=days)).isoformat(timespec='seconds')
        cursor = await self._db.execute(
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
        """今天 vs 昨天同时段消息量对比"""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)

        # 今天按小时
        cursor_today = await self._db.execute(
            """SELECT CAST(strftime('%H', date) AS INTEGER) as hour,
                      COUNT(*) as count
               FROM messages WHERE date >= ?
               GROUP BY hour ORDER BY hour""",
            (today_start.isoformat(timespec='seconds'),),
        )
        today = [dict(r) for r in await cursor_today.fetchall()]

        # 昨天按小时
        cursor_yesterday = await self._db.execute(
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
        """获取指定群组的最新消息"""
        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')
        cursor = await self._db.execute(
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
        """获取指定群组的消息趋势"""
        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')
        cursor = await self._db.execute(
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

    async def export_messages(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        group_id: Optional[int] = None,
        limit: Optional[int] = None,  # D4 修复：支持条数上限，防止全量导出 OOM
    ) -> List[dict]:
        """导出消息数据"""
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
        cursor = await self._db.execute(
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

    async def get_message_trends(self, hours: int = 72) -> List[dict]:
        """按小时统计消息趋势（用于 Dashboard /api/trends）"""
        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')
        cursor = await self._db.execute(
            """SELECT strftime('%Y-%m-%dT%H:00:00', date) as hour, COUNT(*) as count
               FROM messages WHERE date >= ?
               GROUP BY hour ORDER BY hour ASC""",
            (since,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_recent_messages(
        self,
        limit: int = 100,
        group_id: Optional[int] = None,
    ) -> List[dict]:
        """获取最新 N 条消息（用于 Dashboard /api/recent_messages）"""
        conditions = []
        params: List[Any] = []
        if group_id is not None:
            conditions.append("group_id = ?")
            params.append(group_id)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(limit)
        cursor = await self._db.execute(
            f"SELECT * FROM messages {where} ORDER BY date DESC LIMIT ?",
            params,
        )
        rows = await cursor.fetchall()
        messages = [dict(r) for r in rows]
        messages.reverse()  # 恢复时间正序
        return messages

    # ─── 消息编辑 / 删除同步 ───

    async def update_message_text(
        self,
        msg_id: int,
        group_id: int,
        new_text: Optional[str],
        media_type: Optional[str] = None,
    ) -> bool:
        """
        更新消息文本（消息被编辑时调用）。
        返回 True 表示实际有更新，False 表示消息不存在或文本未变。
        FTS 索引由数据库触发器（messages_au）自动维护。
        """
        try:
            cursor = await self._db.execute(
                """UPDATE messages
                   SET text = ?, media_type = COALESCE(?, media_type)
                   WHERE id = ? AND group_id = ?
                   AND text IS NOT ?""",  # 文本未变则跳过，避免无效写操作
                (new_text, media_type, msg_id, group_id, new_text),
            )
            await self._db.commit()
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
        """
        批量删除指定消息（消息被 Telegram 删除时调用）。
        同步清理 FTS 索引，避免幽灵搜索结果。
        返回实际删除条数。
        """
        if not msg_ids:
            return 0
        try:
            placeholders = ",".join("?" * len(msg_ids))
            # 先获取 rowid 以便手动清理 FTS（触发器仅处理 UPDATE，DELETE 需手动）
            cursor = await self._db.execute(
                f"""SELECT rowid, text, sender_name FROM messages
                    WHERE id IN ({placeholders}) AND group_id = ?""",
                [*msg_ids, group_id],
            )
            existing = await cursor.fetchall()

            if not existing:
                return 0

            # 从 FTS 索引中删除（content table 模式需手动维护 DELETE）
            for row in existing:
                try:
                    await self._db.execute(
                        """INSERT INTO messages_fts(messages_fts, rowid, text, sender_name)
                           VALUES ('delete', ?, ?, ?)""",
                        (row["rowid"], row["text"] or "", row["sender_name"] or ""),
                    )
                except Exception:
                    pass  # FTS 清理失败不中断主流程

            # 物理删除消息
            cursor2 = await self._db.execute(
                f"DELETE FROM messages WHERE id IN ({placeholders}) AND group_id = ?",
                [*msg_ids, group_id],
            )
            await self._db.commit()
            deleted = cursor2.rowcount
            logger.info(f"🗑️ 已删除 {deleted} 条消息 (group={group_id}, ids={msg_ids[:5]}{'...' if len(msg_ids)>5 else ''})")
            return deleted
        except Exception as e:
            logger.error(f"❌ 删除消息失败 (group={group_id}): {e}")
            return 0

    # ─── 数据清理 ───

    async def cleanup_old_messages(
        self,
        keep_days: int = 90,
    ) -> int:
        """
        清理超期消息（默认保留 90 天）。
        同步清理关联的 links 记录。
        返回删除条数。
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat(timespec='seconds')
        try:
            # 先清理 links（外键依赖 messages.id）
            await self._db.execute(
                "DELETE FROM links WHERE discovered_at < ?", (cutoff,)
            )
            cursor = await self._db.execute(
                "DELETE FROM messages WHERE date < ?", (cutoff,)
            )
            # FTS 内容表在 content= 模式下随物理表删除，重建一次即可
            await self._db.execute(
                "INSERT INTO messages_fts(messages_fts) VALUES('rebuild')"
            )
            await self._db.commit()
            deleted = cursor.rowcount
            logger.info(f"🧹 清理超期消息: {deleted} 条 (cutoff={cutoff[:10]})")
            return deleted
        except Exception as e:
            logger.error(f"❌ 清理消息失败: {e}")
            return 0
