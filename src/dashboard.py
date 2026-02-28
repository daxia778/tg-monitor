"""
Web Dashboard V2 — FastAPI 后端
提供 REST API 供前端展示监控数据
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse

from .config import load_config
from .database import Database

logger = logging.getLogger("tg-monitor.web")

app = FastAPI(title="TG Monitor Dashboard", version="2.0.0")

# 全局状态
_db: Optional[Database] = None
_config: Optional[dict] = None

STATIC_DIR = Path(__file__).parent / "web" / "static"


async def get_db() -> Database:
    global _db, _config
    if _db is None:
        _config = load_config()
        _db = Database(_config["database"]["path"])
        await _db.connect()
    return _db


@app.on_event("startup")
async def startup():
    await get_db()
    logger.info("🌐 Dashboard V2 API 已启动")


@app.on_event("shutdown")
async def shutdown():
    if _db:
        await _db.close()


# ─── 静态文件 & 首页 ───
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


# ═══════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════

@app.get("/api/health")
async def api_health(db: Database = Depends(get_db)):
    """健康检查 (增强版)"""
    try:
        total = await db.get_message_count()
        groups = await db.get_groups()
        
        # 获取数据库文件大小
        db_path = Path(_config["database"]["path"]) if _config else Path("data/tg_monitor.db")
        db_size_mb = round(db_path.stat().st_size / (1024 * 1024), 2) if db_path.exists() else 0
        
        # 获取最新的消息时间
        recent = await db.get_recent_messages(limit=1)
        last_sync = recent[0]["date"] if recent else "never"
        
        return {
            "status": "ok", 
            "messages": total, 
            "groups": len(groups),
            "db_size_mb": db_size_mb,
            "last_sync": last_sync,
            "version": "2.0.1"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "detail": str(e)}


@app.get("/api/overview")
async def api_overview(db: Database = Depends(get_db)):
    """总览数据"""
    now = datetime.now(timezone.utc)

    total = await db.get_message_count()
    h1 = await db.get_message_count(since=(now - timedelta(hours=1)).isoformat(timespec='seconds'))
    h24 = await db.get_message_count(since=(now - timedelta(hours=24)).isoformat(timespec='seconds'))
    h7d = await db.get_message_count(since=(now - timedelta(days=7)).isoformat(timespec='seconds'))
    groups = await db.get_groups()

    # 链接和摘要统计
    links = await db.get_links(limit=1)
    summaries = await db.get_latest_summaries(limit=1)

    return {
        "total_messages": total,
        "last_1h": h1,
        "last_24h": h24,
        "last_7d": h7d,
        "group_count": len(groups),
        "model": _config.get("ai", {}).get("model", "?") if _config else "?",
        "alerts_enabled": _config.get("alerts", {}).get("enabled", False) if _config else False,
    }


@app.get("/api/trends")
async def api_trends(hours: int = Query(default=72, ge=1, le=720), db: Database = Depends(get_db)):
    """消息趋势数据"""
    rows = await db.get_message_trends(hours=hours)
    return {"data": [{"hour": r["hour"], "count": r["count"]} for r in rows]}


@app.get("/api/comparison")
async def api_comparison(db: Database = Depends(get_db)):
    """今天 vs 昨天消息量对比"""
    return await db.get_hourly_comparison()


@app.get("/api/heatmap")
async def api_heatmap(days: int = Query(default=30), db: Database = Depends(get_db)):
    """活跃度热力图数据"""
    data = await db.get_heatmap_data(days=days)
    return {"data": data}


@app.get("/api/groups")
async def api_groups(hours: int = Query(default=24), db: Database = Depends(get_db)):
    """群组统计"""
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')
    stats = await db.get_stats(since=since)
    return {"data": stats}


@app.get("/api/groups/{group_id}")
async def api_group_detail(group_id: int, hours: int = Query(default=24), db: Database = Depends(get_db)):
    """群组详情 — 消息列表"""
    messages = await db.get_group_messages(group_id, hours=hours, limit=200)
    trends = await db.get_group_trends(group_id, hours=max(hours, 72))

    # 群组基本信息
    groups = await db.get_groups()
    group_info = next((g for g in groups if g["id"] == group_id), {})

    # 活跃用户
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')
    top = await db.get_top_senders(group_id=group_id, since=since, limit=5)

    return {
        "info": group_info,
        "messages": messages,
        "trends": trends,
        "top_senders": top,
    }


@app.get("/api/top_senders")
async def api_top_senders(hours: int = Query(default=24), limit: int = Query(default=10), db: Database = Depends(get_db)):
    """最活跃用户"""
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')
    top = await db.get_top_senders(since=since, limit=limit)
    return {"data": top}


@app.get("/api/links")
async def api_links(limit: int = Query(default=30), db: Database = Depends(get_db)):
    """最新链接"""
    config = _config or load_config()
    
    # 动态加载过滤域名，默认过滤内部短链接
    block_domains = config.get("filtering", {}).get(
        "block_domains", 
        ["t.me", "telegram.me", "telegram.org", "telegra.ph", "telegram.dog"]
    )
    
    links = await db.get_links(limit=limit, block_domains=block_domains)
    return {"data": links}


@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=1), limit: int = Query(default=50), db: Database = Depends(get_db)):
    """搜索消息"""
    results = await db.search_messages(q, limit=limit)
    return {"data": results, "total": len(results)}


@app.get("/api/alerts_config")
async def api_alerts_config(db: Database = Depends(get_db)):
    """告警配置"""
    config = _config or load_config()
    alerts = config.get("alerts", {})
    return {
        "enabled": alerts.get("enabled", False),
        "keywords": alerts.get("keywords", []),
    }


@app.get("/api/recent_messages")
async def api_recent_messages(
    limit: int = Query(default=100, le=500),
    group_id: Optional[int] = Query(default=None),
    db: Database = Depends(get_db)
):
    """最新消息流（始终返回最新的 N 条）"""
    messages = await db.get_recent_messages(limit=limit, group_id=group_id)

    groups = await db.get_groups()
    group_map = {g["id"]: g["title"] for g in groups}
    for msg in messages:
        msg["group_title"] = group_map.get(msg.get("group_id", 0), "未知")

    # 检查是否命中告警关键词
    config = _config or load_config()
    keywords = config.get("alerts", {}).get("keywords", [])
    for msg in messages:
        text = (msg.get("text") or "").lower()
        msg["alert_keywords"] = [kw for kw in keywords if kw.lower() in text]

    return {"data": messages}


@app.get("/api/export")
async def api_export(
    hours: int = Query(default=24),
    group_id: Optional[int] = Query(default=None),
    # D4 修复：加条数上限参数，防止全量导出 OOM 或超时
    max_rows: int = Query(default=10000, le=50000, description="最多导出条数"),
    db: Database = Depends(get_db)
):
    """CSV 数据导出"""
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')
    filename = f"tg_monitor_export_{now.strftime('%Y%m%d_%H%M')}.csv"
    
    async def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "群组", "发送者", "内容", "时间", "媒体类型", "转发"])
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)
        
        chunk_size = 500
        total_fetched = 0
        while total_fetched < max_rows:
            fetch_limit = min(chunk_size, max_rows - total_fetched)
            chunk = await db.export_messages(since=since, group_id=group_id, limit=fetch_limit, offset=total_fetched)
            if not chunk:
                break
                
            for r in chunk:
                writer.writerow([
                    r["id"], r.get("group_title", ""), r.get("sender_name", ""),
                    (r.get("text") or "")[:500], r.get("date", ""),
                    r.get("media_type", ""), r.get("forward_from", ""),
                ])
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)
            total_fetched += len(chunk)

    return StreamingResponse(

        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ═══════════════════════════════════════════
# 摘要相关 API
# ═══════════════════════════════════════════

import asyncio
import uuid
import httpx
from .summarizer import Summarizer


@app.get("/api/llm/status")
async def api_llm_status(db: Database = Depends(get_db)):
    """检测 LLM 代理连接状态"""
    config = _config or load_config()
    ai_cfg = config.get("ai", {})
    api_url = ai_cfg.get("api_url", "")
    model = ai_cfg.get("model", "?")

    if not api_url:
        return {"ok": False, "error": "未配置 ai.api_url", "url": "", "model": model}

    # 尝试请求 /v1/models 端点检测连通性
    base_url = api_url.rsplit("/v1/", 1)[0] if "/v1/" in api_url else api_url.rsplit("/", 1)[0]
    test_url = f"{base_url}/v1/models"

    try:
        api_key = ai_cfg.get("api_key", "")
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(test_url, headers=headers)
            if resp.status_code == 200:
                return {"ok": True, "url": api_url, "model": model, "test_url": test_url}
            else:
                return {"ok": False, "error": f"HTTP {resp.status_code}", "url": api_url, "model": model}
    except httpx.ConnectError:
        return {"ok": False, "error": "连接被拒绝（代理未运行）", "url": api_url, "model": model}
    except httpx.TimeoutException:
        return {"ok": False, "error": "连接超时", "url": api_url, "model": model}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "url": api_url, "model": model}


@app.post("/api/summary/generate")
async def api_summary_generate(
    hours: int = Query(default=24, ge=1, le=720),
    mode: str = Query(default="quick", regex="^(quick|per_group)$"),
    db: Database = Depends(get_db)
):
    """触发摘要生成（异步任务，返回 task_id 用于轮询进度）"""
    config = _config or load_config()

    task_id = str(uuid.uuid4())[:12]
    
    # 将任务存入数据库
    await db.create_summary_job(task_id, group_id=None, hours=hours, mode=mode)

    async def _run_summary():
        try:
            summarizer = Summarizer(config, db)
            
            async def progress_cb(text, current, total):
                # 将进度百分比折算为 0~100 的整数
                progress_pct = int((current / max(total, 1)) * 100)
                await db.update_summary_job(
                    task_id,
                    progress=progress_pct,
                    progress_text=f"{text} ({current}/{total})"
                )
                logger.info(f"Task {task_id} Progress: {text} ({current}/{total})")

            if mode == "per_group":
                result = await summarizer.summarize_per_group(hours=hours, save=True, progress_cb=progress_cb)
            else:
                result = await summarizer.summarize(hours=hours, save=True, progress_cb=progress_cb)

            if result and not result.startswith("❌"):
                await db.update_summary_job(task_id, status="done", result=result, progress=100)
            else:
                error_msg = result or "LLM 返回空结果，请检查 AI 代理是否在线"
                await db.update_summary_job(task_id, status="error", error_msg=error_msg)

        except Exception as e:
            logger.error(f"摘要生成失败: {e}", exc_info=True)
            await db.update_summary_job(task_id, status="error", error_msg=f"{type(e).__name__}: {str(e)[:300]}")

    asyncio.create_task(_run_summary())
    return {"task_id": task_id, "status": "running"}


@app.get("/api/summary/status/{task_id}")
async def api_summary_status(task_id: str, db: Database = Depends(get_db)):
    """查询摘要生成任务状态"""
    task = await db.get_summary_job(task_id)
    if not task:
        return {"status": "not_found", "error": "任务不存在"}
    
    # 转换为前端期待的格式以保持兼容性
    return {
        "status": task["status"],
        "progress": task["progress_text"] or "",
        "current_step": task["progress"],  # 前端用 current_step/total_steps 算百分比
        "total_steps": 100,               # 配合 progress=0-100 使用
        "result": task["result"],
        "error": task["error_msg"],
    }



@app.get("/api/summary/history")
async def api_summary_history(limit: int = Query(default=10, le=50), db: Database = Depends(get_db)):
    """获取历史摘要"""
    summaries = await db.get_latest_summaries(limit=limit)
    return {"data": summaries}


def run_dashboard(config_path=None, host="0.0.0.0", port=8501):
    """启动 Dashboard"""
    import uvicorn
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    uvicorn.run("src.dashboard:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run_dashboard()
