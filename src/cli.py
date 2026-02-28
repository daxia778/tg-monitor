"""
CLI 命令行界面
使用 Click + Rich 提供美观的命令行交互
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress
from rich import box

from .config import load_config, validate_config
from .database import Database
from .collector import Collector
from .summarizer import Summarizer


console = Console()


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def run_async(coro):
    """统一的异步运行入口"""
    return asyncio.run(coro)


async def _get_db(config: dict) -> Database:
    db = Database(config["database"]["path"])
    await db.connect()
    return db


# ═══════════════════════════════════════════════════════
# CLI 主入口
# ═══════════════════════════════════════════════════════


@click.group()
@click.option("--config", "-c", default=None, help="配置文件路径")
@click.option("--verbose", "-v", is_flag=True, help="详细日志")
@click.pass_context
def cli(ctx, config, verbose):
    """🔍 TG Monitor — Telegram 群聊监控 & 智能汇总"""
    setup_logging(verbose)
    ctx.ensure_object(dict)
    try:
        cfg = load_config(config)
        ctx.obj["config"] = cfg
    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        console.print(
            "[yellow]💡 请复制 config.yaml.example 为 config.yaml 并填写配置[/yellow]"
        )
        raise SystemExit(1)


# ═══════════════════════════════════════════════════════
# start — 启动实时监控
# ═══════════════════════════════════════════════════════


@cli.command()
@click.option("--fetch-history", "-H", default=0, type=int,
              help="启动前先拉取每个群的最近 N 条历史消息")
@click.pass_context
def start(ctx, fetch_history):
    """🚀 启动实时群聊监控"""
    cfg = ctx.obj["config"]

    errors = validate_config(cfg)
    if errors:
        for e in errors:
            console.print(f"[red]❌ {e}[/red]")
        raise SystemExit(1)

    async def _run():
        db = await _get_db(cfg)
        collector = Collector(cfg, db)
        await collector.start()

        if fetch_history > 0:
            console.print(
                f"\n[cyan]⏳ 正在拉取每个群的最近 {fetch_history} 条历史消息...[/cyan]"
            )
            total = await collector.fetch_history(limit=fetch_history)
            console.print(f"[green]✅ 共拉取 {total} 条历史消息[/green]\n")

        await collector.run_realtime()

    try:
        run_async(_run())
    except KeyboardInterrupt:
        console.print("\n[yellow]⏹ 已停止监控[/yellow]")


# ═══════════════════════════════════════════════════════
# fetch — 拉取历史消息
# ═══════════════════════════════════════════════════════


@cli.command()
@click.option("--limit", "-l", default=500, help="每个群拉取的最大消息数")
@click.option("--group", "-g", default=None, help="指定群组 ID")
@click.pass_context
def fetch(ctx, limit, group):
    """📥 拉取历史消息到本地数据库"""
    cfg = ctx.obj["config"]

    errors = validate_config(cfg)
    if errors:
        for e in errors:
            console.print(f"[red]❌ {e}[/red]")
        raise SystemExit(1)

    async def _run():
        db = await _get_db(cfg)
        collector = Collector(cfg, db)
        await collector.start()

        group_id = int(group) if group else None
        total = await collector.fetch_history(group_id=group_id, limit=limit)
        console.print(f"\n[green]✅ 共拉取 {total} 条消息[/green]")

        await collector.stop()
        await db.close()

    run_async(_run())


# ═══════════════════════════════════════════════════════
# summary — AI 智能摘要
# ═══════════════════════════════════════════════════════


@cli.command()
@click.option("--hours", "-h", default=24.0, type=float, help="最近 N 小时 (默认24)")
@click.option("--since", "-s", default=None, help="起始时间 (ISO 格式)")
@click.option("--until", "-u", default=None, help="截止时间 (ISO 格式)")
@click.option("--group", "-g", default=None, help="指定群组 ID")
@click.option("--no-save", is_flag=True, help="不保存摘要到数据库")
@click.pass_context
def summary(ctx, hours, since, until, group, no_save):
    """📝 生成群聊 AI 智能摘要"""
    cfg = ctx.obj["config"]

    async def _run():
        db = await _get_db(cfg)
        summarizer = Summarizer(cfg, db)

        group_id = int(group) if group else None

        with console.status("[bold cyan]🧠 AI 正在分析群聊消息...[/bold cyan]"):
            if since:
                result = await summarizer.summarize(
                    group_id=group_id, since=since, until=until,
                    save=not no_save,
                )
            else:
                result = await summarizer.summarize(
                    group_id=group_id, hours=hours,
                    save=not no_save,
                )

        console.print()
        console.print(Panel(
            Markdown(result),
            title="[bold green]📋 群聊摘要[/bold green]",
            border_style="green",
            padding=(1, 2),
        ))

        await db.close()

    run_async(_run())


# ═══════════════════════════════════════════════════════
# report — 每日报告
# ═══════════════════════════════════════════════════════


@cli.command()
@click.pass_context
def report(ctx):
    """📊 生成每日综合报告"""
    cfg = ctx.obj["config"]

    async def _run():
        db = await _get_db(cfg)
        summarizer = Summarizer(cfg, db)

        with console.status("[bold cyan]📊 正在生成每日报告...[/bold cyan]"):
            result = await summarizer.daily_report()

        console.print()
        console.print(Panel(
            Markdown(result),
            title="[bold blue]📊 每日报告[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        ))

        await db.close()

    run_async(_run())


# ═══════════════════════════════════════════════════════
# links — 查看最新链接
# ═══════════════════════════════════════════════════════


@cli.command()
@click.option("--last", "-n", default=20, help="显示最近 N 条链接")
@click.option("--group", "-g", default=None, help="指定群组 ID")
@click.pass_context
def links(ctx, last, group):
    """🔗 查看最新分享的链接"""
    cfg = ctx.obj["config"]

    async def _run():
        db = await _get_db(cfg)

        group_id = int(group) if group else None
        results = await db.get_links(group_id=group_id, limit=last)

        if not results:
            console.print("[yellow]暂无链接记录[/yellow]")
            await db.close()
            return

        table = Table(
            title="🔗 最新链接",
            box=box.ROUNDED,
            show_lines=True
        )
        table.add_column("时间", style="dim", width=16)
        table.add_column("群组", style="cyan", width=15)
        table.add_column("发送者", style="green", width=12)
        table.add_column("链接", style="blue", max_width=60)
        table.add_column("上下文", style="white", max_width=30)

        for link in results:
            table.add_row(
                link["discovered_at"][:16].replace("T", " "),
                link.get("group_title", str(link["group_id"]))[:15],
                (link.get("sender_name") or "?")[:12],
                link["url"][:60],
                (link.get("context") or "")[:30] + "..." if link.get("context") else "",
            )

        console.print(table)
        await db.close()

    run_async(_run())


# ═══════════════════════════════════════════════════════
# search — 搜索消息
# ═══════════════════════════════════════════════════════


@cli.command()
@click.argument("keyword")
@click.option("--limit", "-l", default=30, help="最多显示条数")
@click.pass_context
def search(ctx, keyword, limit):
    """🔍 搜索群聊消息"""
    cfg = ctx.obj["config"]

    async def _run():
        db = await _get_db(cfg)
        results = await db.search_messages(keyword, limit=limit)

        if not results:
            console.print(f"[yellow]未找到包含 \"{keyword}\" 的消息[/yellow]")
            await db.close()
            return

        console.print(f"[green]找到 {len(results)} 条匹配消息[/green]\n")

        for msg in results:
            date = msg["date"][:16].replace("T", " ")
            group = msg.get("group_title", f"群组{msg['group_id']}")
            sender = msg.get("sender_name", "?")
            text = msg.get("text", "")

            # 高亮关键词
            highlighted = text.replace(
                keyword, f"[bold yellow]{keyword}[/bold yellow]"
            )

            console.print(
                f"[dim]{date}[/dim] [cyan][{group}][/cyan] "
                f"[green]{sender}[/green]: {highlighted}"
            )

        await db.close()

    run_async(_run())


# ═══════════════════════════════════════════════════════
# stats — 统计信息
# ═══════════════════════════════════════════════════════


@cli.command()
@click.option("--hours", "-h", default=24.0, type=float, help="统计最近 N 小时")
@click.pass_context
def stats(ctx, hours):
    """📊 查看群组统计信息"""
    cfg = ctx.obj["config"]

    async def _run():
        db = await _get_db(cfg)

        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')

        results = await db.get_stats(since=since)

        if not results:
            console.print("[yellow]暂无统计数据[/yellow]")
            await db.close()
            return

        table = Table(
            title=f"📊 最近 {hours} 小时统计",
            box=box.ROUNDED,
        )
        table.add_column("群组", style="cyan")
        table.add_column("消息数", style="green", justify="right")
        table.add_column("活跃用户", style="blue", justify="right")
        table.add_column("首条消息", style="dim")
        table.add_column("最新消息", style="dim")

        total_msgs = 0
        for s in results:
            table.add_row(
                s.get("title", str(s["group_id"])),
                str(s["message_count"]),
                str(s["active_users"]),
                (s["first_msg"] or "")[:16].replace("T", " "),
                (s["last_msg"] or "")[:16].replace("T", " "),
            )
            total_msgs += s["message_count"]

        console.print(table)
        console.print(f"\n[bold]总消息数: {total_msgs}[/bold]")

        # 显示 Top 发送者
        top = await db.get_top_senders(since=since, limit=5)
        if top:
            console.print(f"\n[bold]🏆 最活跃用户:[/bold]")
            for i, t in enumerate(top, 1):
                console.print(
                    f"  {i}. {t.get('sender_name', '?')} — "
                    f"{t['msg_count']} 条消息"
                )

        await db.close()

    run_async(_run())


# ═══════════════════════════════════════════════════════
# groups — 管理监控群组
# ═══════════════════════════════════════════════════════


@cli.group(name="groups")
def groups_cmd():
    """📌 管理监控群组"""
    pass


@groups_cmd.command(name="list")
@click.pass_context
def groups_list(ctx):
    """列出已注册的群组"""
    cfg = ctx.obj["config"]

    async def _run():
        db = await _get_db(cfg)
        groups = await db.get_groups()

        if not groups:
            console.print("[yellow]暂无群组记录（请先启动监控或拉取历史）[/yellow]")
            await db.close()
            return

        table = Table(title="📌 监控群组", box=box.ROUNDED)
        table.add_column("ID", style="dim")
        table.add_column("名称", style="cyan")
        table.add_column("Username", style="green")
        table.add_column("成员数", justify="right")
        table.add_column("更新时间", style="dim")

        for g in groups:
            table.add_row(
                str(g["id"]),
                g["title"],
                g.get("username") or "-",
                str(g.get("member_count") or "-"),
                (g["updated_at"] or "")[:16].replace("T", " "),
            )

        console.print(table)

        # 显示配置中的群组
        cfg_groups = cfg.get("groups", [])
        if cfg_groups:
            console.print(f"\n[dim]config.yaml 中配置了 {len(cfg_groups)} 个群组[/dim]")

        await db.close()

    run_async(_run())


@groups_cmd.command(name="scan")
@click.pass_context
def groups_scan(ctx):
    """扫描 Telegram 中所有群组/频道（从账号中拉取）"""
    cfg = ctx.obj["config"]

    errors = validate_config(cfg)
    if errors:
        for e in errors:
            console.print(f"[red]❌ {e}[/red]")
        raise SystemExit(1)

    async def _run():
        from telethon import TelegramClient
        from telethon.tl.types import Channel, Chat

        tg_cfg = cfg["telegram"]
        client = TelegramClient(
            tg_cfg.get("session_name", "tg_monitor"),
            int(tg_cfg["api_id"]),
            tg_cfg["api_hash"],
        )
        await client.start(phone=tg_cfg.get("phone"))

        me = await client.get_me()
        console.print(f"\n[green]✅ 已登录: {me.first_name} (@{me.username})[/green]\n")

        table = Table(title="📡 所有群组/频道", box=box.ROUNDED)
        table.add_column("#", style="dim", width=4)
        table.add_column("类型", style="blue", width=6)
        table.add_column("名称", style="cyan", width=30)
        table.add_column("ID", style="green", width=15)
        table.add_column("Username", style="dim")

        idx = 1
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if isinstance(entity, (Channel, Chat)):
                dtype = "频道" if getattr(entity, "broadcast", False) else "群组"
                table.add_row(
                    str(idx),
                    dtype,
                    getattr(entity, "title", "?")[:28],
                    str(entity.id),
                    getattr(entity, "username", "") or "-",
                )
                idx += 1

        console.print(table)
        console.print(f"\n[dim]共 {idx - 1} 个群组/频道[/dim]")
        console.print("[yellow]📌 将想要监控的群组 ID 添加到 config.yaml 中即可[/yellow]")

        await client.disconnect()

    run_async(_run())


# ═══════════════════════════════════════════════════════
# history — 查看历史摘要
# ═══════════════════════════════════════════════════════


@cli.command()
@click.option("--last", "-n", default=5, help="显示最近 N 条摘要")
@click.pass_context
def history(ctx, last):
    """📜 查看历史摘要记录"""
    cfg = ctx.obj["config"]

    async def _run():
        db = await _get_db(cfg)
        summaries = await db.get_latest_summaries(limit=last)

        if not summaries:
            console.print("[yellow]暂无摘要记录[/yellow]")
            await db.close()
            return

        for s in summaries:
            group_name = s.get("group_title") or "全部群组"
            start = s["period_start"][:16].replace("T", " ")
            end = s["period_end"][:16].replace("T", " ")

            console.print(Panel(
                Markdown(s["content"]),
                title=f"[bold]{group_name}[/bold] | {start} → {end} | "
                      f"{s['message_count']} 条消息",
                border_style="dim",
                padding=(1, 2),
            ))
            console.print()

        await db.close()

    run_async(_run())


# ═══════════════════════════════════════════════════════
# bot — 启动 TG 机器人
# ═══════════════════════════════════════════════════════


@cli.command()
@click.pass_context
def bot(ctx):
    """🤖 启动 Telegram 机器人交互界面"""
    cfg = ctx.obj["config"]

    if not cfg.get("bot", {}).get("token"):
        console.print("[red]❌ 未配置 bot.token[/red]")
        console.print("[yellow]💡 请先通过 @BotFather 创建机器人并在 config.yaml 中配置 token[/yellow]")
        raise SystemExit(1)

    from .bot import MonitorBot
    monitor_bot = MonitorBot(cfg)
    console.print("[green]🤖 启动 TG 机器人...[/green]")
    monitor_bot.run()


# ═══════════════════════════════════════════════════════
# dashboard — Web 仪表盘
# ═══════════════════════════════════════════════════════


@cli.command()
@click.option("--host", default="0.0.0.0", help="绑定地址")
@click.option("--port", "-p", default=8501, type=int, help="端口号")
@click.pass_context
def dashboard(ctx, host, port):
    """🌐 启动 Web 监控仪表盘"""
    from .dashboard import run_dashboard
    console.print(f"[green]🌐 启动 Dashboard: http://localhost:{port}[/green]")
    run_dashboard(host=host, port=port)


if __name__ == "__main__":
    cli()
