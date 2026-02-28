"""
核心数据库连接与结构模块
负责 SQLite 连接、PRAGMA 配置、Schema 初始化及迁移
"""
import aiosqlite
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

logger = logging.getLogger("tg-monitor.db.core")

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
    discovered_at TEXT NOT NULL,
    title        TEXT,
    description  TEXT,
    image_url    TEXT
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

CREATE TABLE IF NOT EXISTS summary_jobs (
    id           TEXT PRIMARY KEY,
    group_id     INTEGER,
    hours        INTEGER,
    mode         TEXT,
    status       TEXT,
    progress     INTEGER DEFAULT 0,
    progress_text TEXT,
    result       TEXT,
    error_msg    TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
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

CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT
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

# FTS5 DELETE 触发器：消息删除时同步清除全文索引
FTS_TRIGGER_DELETE_SQL = """CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, text, sender_name)
    VALUES ('delete', old.rowid, old.text, old.sender_name);
END"""

MIGRATIONS: List[Tuple[int, str, str]] = [
    (
        1,
        "Add alerted_messages table for alert deduplication",
        """CREATE TABLE IF NOT EXISTS alerted_messages (
            msg_key    TEXT PRIMARY KEY,
            alerted_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
    ),
    (
        2,
        "Add title to links",
        "ALTER TABLE links ADD COLUMN title TEXT",
    ),
    (
        3,
        "Add description to links",
        "ALTER TABLE links ADD COLUMN description TEXT",
    ),
    (
        4,
        "Add image_url to links",
        "ALTER TABLE links ADD COLUMN image_url TEXT",
    ),
]

class DatabaseConnection:
    """处理数据库底层连接、初始化及迁移"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        
        await self.conn.execute("PRAGMA busy_timeout=60000")
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("PRAGMA cache_size = -32000")
        await self.conn.execute("PRAGMA temp_store = MEMORY")
        await self.conn.execute("PRAGMA synchronous = NORMAL")
        await self.conn.execute("PRAGMA wal_autocheckpoint = 1000")
        
        for stmt in SCHEMA_SQL.split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                await self.conn.execute(stmt)
            except aiosqlite.OperationalError as e:
                if "already exists" not in str(e).lower():
                    logger.error(f"❌ Schema 初始化失败: {e}\nSQL: {stmt[:120]}")
                    raise
            except aiosqlite.IntegrityError as e:
                if "idx_links_unique" in stmt:
                    logger.warning("⚠️ links 表存在重复数据，正在去重后重建唯一索引...")
                    await self.conn.execute("""
                        DELETE FROM links WHERE rowid NOT IN (
                            SELECT MIN(rowid) FROM links
                            GROUP BY url, group_id, message_id
                        )
                    """)
                    await self.conn.commit()
                    await self.conn.execute(stmt)
                    logger.info("✅ links 表去重完成，唯一索引已建立")
                else:
                    logger.warning(f"⚠️ Schema 语句跳过（IntegrityError）: {e}")
        await self.conn.commit()
        
        try:
            await self.conn.execute(FTS_CREATE_SQL)
            await self.conn.execute(FTS_TRIGGER_SQL)
            await self.conn.execute(FTS_TRIGGER_UPDATE_SQL)
            await self.conn.execute(FTS_TRIGGER_DELETE_SQL)
            await self.conn.commit()
            
            cursor = await self.conn.execute("SELECT COUNT(*) as cnt FROM messages_fts")
            fts_count = (await cursor.fetchone())["cnt"]
            cursor2 = await self.conn.execute("SELECT COUNT(*) as cnt FROM messages WHERE text IS NOT NULL")
            msg_count = (await cursor2.fetchone())["cnt"]
            if fts_count == 0 and msg_count > 0:
                logger.info(f"🔄 重建 FTS 索引 ({msg_count} 条消息)...")
                await self.conn.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
                await self.conn.commit()
                logger.info("✅ FTS 索引重建完成")
        except Exception as e:
            logger.warning(f"⚠️ FTS5 初始化失败（回退到 LIKE 搜索）: {e}")
            
        await self._run_migrations()
        logger.info("✅ 数据库已连接 (WAL 模式)")

    async def _run_migrations(self):
        cursor = await self.conn.execute("SELECT COALESCE(MAX(version), 0) as ver FROM schema_version")
        current = (await cursor.fetchone())["ver"]

        pending = [(v, d, s) for v, d, s in MIGRATIONS if v > current]
        if not pending:
            return

        logger.info(f"🔄 应用 {len(pending)} 个迁移（当前版本: {current}）...")
        for version, description, sql in sorted(pending, key=lambda x: x[0]):
            try:
                await self.conn.execute(sql)
                await self.conn.execute(
                    "INSERT OR IGNORE INTO schema_version (version, description) VALUES (?, ?)",
                    (version, description),
                )
                await self.conn.commit()
                logger.info(f"   ✅ v{version}: {description}")
            except (aiosqlite.OperationalError, aiosqlite.IntegrityError) as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    await self.conn.execute(
                        "INSERT OR IGNORE INTO schema_version (version, description) VALUES (?, ?)",
                        (version, description),
                    )
                    await self.conn.commit()
                    logger.info(f"   ⚠️ v{version}: 已存在，跳过")
                else:
                    logger.error(f"   ❌ v{version} 迁移失败: {e}")
                    raise

    async def close(self):
        if self.conn:
            await self.conn.close()
