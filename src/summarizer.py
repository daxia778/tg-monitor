"""
AI 智能摘要模块
调用 LLM API 对群聊消息进行分析和汇总
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx

from .database import Database

logger = logging.getLogger("tg-monitor.summarizer")

# 默认每批最多给 LLM 的消息数（避免超长上下文）
DEFAULT_CHUNK_SIZE = 300


class Summarizer:
    """AI 群聊摘要生成器（支持多 API Key 轮询负载均衡）"""

    def __init__(self, config: dict, db: Database):
        self.config = config
        self.db = db
        self.ai_cfg = config.get("ai", {})
        self.api_url = self.ai_cfg.get("api_url", "http://localhost:18789/v1/chat/completions")
        self.model = self.ai_cfg.get("model", "gpt-4o")
        self.max_tokens = self.ai_cfg.get("max_tokens", 4096)
        self.system_prompt = self.ai_cfg.get("summary_system_prompt", "")

        # ── 多 Key 轮询负载均衡 ──────────────────────────────────────
        # 支持两种配置方式：
        #   单 key:  ai.api_key: "sk-xxx"
        #   多 keys: ai.api_keys: ["sk-aaa", "sk-bbb", "sk-ccc"]
        single_key = self.ai_cfg.get("api_key", "")
        keys_list: list = self.ai_cfg.get("api_keys", [])

        if keys_list:
            # 多 key 模式：去重 + 过滤空值
            self._keys: list = [k for k in keys_list if k]
        elif single_key:
            self._keys = [single_key]
        else:
            self._keys = [""]  # 无 key（本地代理不需要认证）

        # 每个 key 的并发上限（可单独配置，默认 3）
        per_key_concurrency = self.ai_cfg.get("max_concurrent_per_key", 3)
        # 使用 asyncio.Queue 实现动态负载平衡池，代替原有的静态轮询等待
        # 当有请求时只分配当前处于空闲状态的 key
        self._key_queue = asyncio.Queue()
        for key in self._keys:
            for _ in range(per_key_concurrency):
                self._key_queue.put_nowait(key)

        # 全局兼容属性
        max_concurrent = self.ai_cfg.get("max_concurrent", per_key_concurrency * len(self._keys))
        self._sem = asyncio.Semaphore(max_concurrent)

        total = per_key_concurrency * len(self._keys)
        logger.info(
            f"🤖 LLM 动态负载平衡池已构建: {len(self._keys)} 个 key × "
            f"{per_key_concurrency} = 最大 {total} 并发请求槽位"
        )

    async def summarize(
        self,
        group_id: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        hours: Optional[float] = None,
        save: bool = True,
        progress_cb: Optional[Any] = None,
    ) -> str:
        """
        生成指定范围的群聊摘要

        Args:
            group_id: 指定群组 ID，None 表示所有群
            since: 起始时间 ISO 格式
            until: 截止时间 ISO 格式
            hours: 最近 N 小时（与 since 二选一）
            save: 是否保存到数据库
            progress_cb: 进度回调函数 async def (text, current_step, total_steps)
        """
        # 计算时间范围
        now = datetime.now(timezone.utc)
        if hours is not None:
            since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')
        if since is None:
            since = (now - timedelta(hours=24)).isoformat(timespec='seconds')
        if until is None:
            until = now.isoformat(timespec='seconds')

        if progress_cb:
            await progress_cb("🔍 正在从数据库提取消息...", 1, 10)

        # 获取消息（时间范围内全部，不限条数）
        messages = await self.db.get_messages(
            group_id=group_id, since=since, until=until
        )

        if not messages:
            return "📭 该时间段内没有消息记录。"

        # 获取群组信息
        groups = await self.db.get_groups()
        group_map = {g["id"]: g["title"] for g in groups}

        # 格式化消息为聊天记录文本
        formatted = self._format_messages(messages, group_map)

        # 如果消息太多，分批处理再合并
        if len(messages) > DEFAULT_CHUNK_SIZE:
            summary = await self._summarize_chunked(messages, group_map, progress_cb)
        else:
            if progress_cb:
                await progress_cb(f"🧠 正在调用 AI 分析 {len(messages)} 条消息...", 5, 10)
            summary = await self._call_llm(formatted)

        # 清洗 Markdown 格式
        summary = self._clean_markdown(summary)

        if summary and save:
            if progress_cb:
                await progress_cb("💾 正在保存摘要结果...", 9, 10)
            await self.db.save_summary(
                group_id=group_id,
                period_start=since,
                period_end=until,
                message_count=len(messages),
                content=summary,
                model=self.model,
            )

        if progress_cb:
            await progress_cb("✅ 摘要生成完成", 10, 10)

        return summary

    def _format_messages(
        self, messages: List[dict], group_map: Dict[int, str]
    ) -> str:
        """将消息列表格式化为可读文本"""
        lines: List[str] = []
        current_group = None

        for msg in messages:
            gid = msg.get("group_id")
            group_name = group_map.get(gid, f"群组{gid}")

            # 群组切换时插入分隔符
            if gid != current_group:
                lines.append(f"\n{'='*40}")
                lines.append(f"📌 群组: {group_name}")
                lines.append(f"{'='*40}")
                current_group = gid

            # 格式化单条消息
            date_str = msg.get("date", "")[:19].replace("T", " ")
            sender = msg.get("sender_name", "?")
            text = msg.get("text", "")

            # 添加媒体/转发标记
            extras: List[str] = []
            if msg.get("media_type"):
                extras.append(f"[{msg['media_type']}]")
            if msg.get("forward_from"):
                extras.append(f"[转发自: {msg['forward_from']}]")
            if msg.get("reply_to_id"):
                extras.append(f"[回复#{msg['reply_to_id']}]")

            extra_str = " ".join(extras)
            if extra_str:
                extra_str = f" {extra_str}"

            # S4 修复：截断超长消息，防止单条消息撑爆 LLM context window
            if len(text) > 500:
                text = text[:250] + "\n...[长文本截断]...\n" + text[-250:]

            line = f"[{date_str}] {sender}: {text}{extra_str}"
            lines.append(line)

        return "\n".join(lines)

    async def _summarize_chunked(
        self, messages: List[dict], group_map: dict, progress_cb: Optional[Any] = None
    ) -> str:
        """分批摘要再合并（S3 修复：批次之间并发执行，大幅缩短多批次总耗时）"""
        total = len(messages)
        chunk_size = DEFAULT_CHUNK_SIZE
        n_chunks = (total + chunk_size - 1) // chunk_size

        processed_chunks = 0

        # S3：构建所有批次的协程，用 gather 并发执行
        async def _process_chunk(i: int) -> Optional[str]:
            nonlocal processed_chunks
            chunk = messages[i:i + chunk_size]
            chunk_text = self._format_messages(chunk, group_map)
            idx = i // chunk_size + 1
            logger.info(
                f"📝 处理消息批次 {idx}/{n_chunks} "
                f"({i+1}-{min(i+chunk_size, total)} / {total})"
            )
            
            res = await self._call_llm(
                chunk_text,
                extra_instruction=(
                    f"(这是第 {idx} 批消息，"
                    f"共 {n_chunks} 批，请先提取这一批的要点)"
                ),
            )
            processed_chunks += 1
            if progress_cb:
                # 进度映射：分批处理占 2-7 步
                p = 2 + int((processed_chunks / n_chunks) * 5)
                await progress_cb(f"🧠 正在分析消息批次 {processed_chunks}/{n_chunks}...", p, 10)
            return res

        results = await asyncio.gather(
            *[_process_chunk(i) for i in range(0, total, chunk_size)]
        )
        chunk_summaries = [r for r in results if r]

        # 合并所有批次的摘要
        if len(chunk_summaries) > 1:
            if progress_cb:
                await progress_cb("📝 正在合并各批次分析结果...", 8, 10)
            merge_prompt = (
                "请将以下多个批次的群聊分析结果合并为一份完整的摘要，"
                "去除重复内容，保留所有重要信息：\n\n"
                + "\n\n---\n\n".join(chunk_summaries)
            )
            final = await self._call_llm(merge_prompt, is_merge=True)
            return final or "\n\n---\n\n".join(chunk_summaries)
        elif chunk_summaries:
            return chunk_summaries[0]
        else:
            return "⚠️ 摘要生成失败"

    async def _call_llm(
        self,
        content: str,
        extra_instruction: str = "",
        is_merge: bool = False,
    ) -> str:
        """调用 LLM API（多 key 轮询负载均衡）"""
        if is_merge:
            system = "你是一个信息合并助手。请将多个分析结果合并为一份结构化摘要。请使用纯文本格式，不要使用 Markdown 语法（不要用 # * ** __ 等符号）。"
        else:
            system = self.system_prompt or (
                "你是一个 Telegram 群聊分析助手，请用中文输出结构化摘要。请使用纯文本格式，不要使用 Markdown 语法（不要用 # * ** __ 等符号），改用数字编号和物理换行来排版。"
            )

        if extra_instruction:
            system += f"\n{extra_instruction}"

        messages_payload = [
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ]

        payload = {
            "model": self.model,
            "messages": messages_payload,
            "max_tokens": self.max_tokens,
            "temperature": 0.3,
        }

        max_retries = 2
        last_error = ""

        for attempt in range(max_retries + 1):
            # 从空闲槽位队列中动态获取一个 Key
            api_key = await self._key_queue.get()
            key_prefix = api_key[:8] if api_key else "local"

            try:
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        self.api_url,
                        json=payload,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    reply = data["choices"][0]["message"]["content"]
                    logger.info(
                        f"✅ LLM 返回 {len(reply)} 字 (槽位 key:{key_prefix}...)"
                    )
                    return reply

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                last_error = e.response.text[:200]
                logger.error(
                    f"❌ LLM API 错误 [{status}] (第 {attempt+1} 次, "
                    f"槽位 key:{key_prefix}...): {last_error}"
                )
                if 400 <= status < 500 and status != 429:
                    return f"❌ AI 代理返回错误: {status}"
                if status == 429:
                    logger.info("⚠️ 触发限速(429)，自动由下一个空闲 key 接管...")
                    continue
                if status >= 500:
                    logger.warning(f"⚠️ AI代理服务端错误: {status}")
                    if attempt >= 1:
                        return f"❌ AI代理服务端错误: {status}"

            except httpx.RequestError as e:
                last_error = f"网络请求错误: {e}"
                logger.warning(f"⚠️ LLM 网络连通异常 (第 {attempt+1} 次): {e}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"⚠️ LLM 发生未知错误 (第 {attempt+1} 次): {e}")
            finally:
                # 不管成功失败，最后必须将 Key 槽位归还到队列中供其他任务使用
                self._key_queue.put_nowait(api_key)
                self._key_queue.task_done()

            if attempt < max_retries:
                wait = 2 ** attempt
                logger.info(f"⏳ 等待 {wait}s 后进行下一次调用...")
                await asyncio.sleep(wait)

        logger.error(f"❌ LLM 调用多次失败，放弃。最后错误: {last_error}")
        return "❌ LLM 调用失败，请检查网络或配置"

    def _clean_markdown(self, text: str) -> str:
        """移除所有 Markdown 符号，使其在纯文本环境下美观可读"""
        import re
        if not text:
            return ""

        # 1. 消除行首的 Markdown 标题符号（# ## ### 等）
        text = re.sub(r'^\s{0,3}#{1,6}\s+', '', text, flags=re.MULTILINE)

        # 2. 消除粗体/斜体组合 (**text** / __text__ / *text* / _text_)
        #    先处理双符号，再处理单符号，避免顺序问题
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text, flags=re.DOTALL)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text, flags=re.DOTALL)
        text = re.sub(r'__(.+?)__', r'\1', text, flags=re.DOTALL)
        text = re.sub(r'\*(.+?)\*', r'\1', text, flags=re.DOTALL)
        text = re.sub(r'_(.+?)_', r'\1', text, flags=re.DOTALL)

        # 3. 将 Markdown 列表项（行首的 * - + 号）替换为美观的「•」项目符号
        text = re.sub(r'^[ \t]*[*\-+]\s+', '• ', text, flags=re.MULTILINE)

        # 4. 移除行内代码块 `code`
        text = re.sub(r'`{1,3}([^`]+)`{1,3}', r'\1', text)

        # 5. 最后安全兜底：移除所有残留的孤立 * 和 # 字符
        #    仅匹配孤立出现（非中文标点语境里的合法字符）
        text = re.sub(r'(?<!\w)\*+(?!\w)', '', text)
        text = re.sub(r'(?<!\w)#+(?!\w)', '', text)

        # 6. 合并多余空行（最多保留 2 个连续换行）
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    async def quick_digest(self, hours: float = 6) -> str:
        """
        快速摘要：最近 N 小时的精华
        适合日常快速查看
        """
        return await self.summarize(hours=hours, save=False)

    async def summarize_per_group(self, hours: float = 24, save: bool = True, progress_cb: Optional[Any] = None) -> str:
        """按群组分别摘要，再合并为总结报告 (已改为并发执行)"""
        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=hours)).isoformat(timespec='seconds')
        until = now.isoformat(timespec='seconds')

        if progress_cb:
            await progress_cb("🔍 正在初始化群组列表...", 1, 10)

        groups = await self.db.get_groups()
        group_map = {g["id"]: g["title"] for g in groups}

        # 找出有消息的群组（并发统计）
        active_groups = []
        if progress_cb:
            await progress_cb("📊 正在统计各群组消息量...", 2, 10)

        async def _check_group(group):
            cnt = await self.db.get_message_count(group_id=group["id"], since=since, until=until)
            return (group, cnt) if cnt > 0 else None

        count_results = await asyncio.gather(*[_check_group(g) for g in groups])
        active_groups = [r for r in count_results if r is not None]

        if not active_groups:
            return "📭 该时间段内没有消息记录。"

        total_msgs = sum(count for _, count in active_groups)
        processed_count = 0
        total_active = len(active_groups)

        if progress_cb:
            await progress_cb(f"📋 找到 {total_active} 个活跃群组，共 {total_msgs} 条消息，开始并发分析...", 3, 10)

        # 定义处理单个群组的任务
        async def _process_single_group(group_data):
            nonlocal processed_count
            group, count = group_data
            gid = group["id"]
            title = group_map.get(gid, f"群组{gid}")

            # ★ 关键修复：在 LLM 调用前就立即更新进度，让用户在等待时看到反馈
            if progress_cb:
                p_before = 3 + int((processed_count / total_active) * 5)
                await progress_cb(f"🧠 正在读取 [{title}] 的消息...", p_before, 10)

            messages = await self.db.get_messages(
                group_id=gid, since=since, until=until
            )

            logger.info(f"📝 生成 [{title}] 摘要 ({len(messages)} 条消息)...")

            # ★ 再次更新：进入 LLM 阶段时立即通知，这是耗时最久的地方
            if progress_cb:
                p_llm = 3 + int((processed_count / total_active) * 5)
                await progress_cb(f"🤖 AI 正在分析 [{title}]（{len(messages)} 条，请稍候）...", p_llm, 10)

            if len(messages) > DEFAULT_CHUNK_SIZE:
                summary = await self._summarize_chunked(messages, group_map)
            else:
                formatted = self._format_messages(messages, group_map)
                summary = await self._call_llm(
                    formatted,
                    extra_instruction=f"这是群组「{title}」的消息记录。请重点关注该群讨论的核心话题和结论。",
                )

            processed_count += 1
            if progress_cb:
                p = 3 + int((processed_count / total_active) * 5)
                await progress_cb(f"✅ [{title}] 分析完成 ({processed_count}/{total_active})", p, 10)

            if summary:
                return f"📌 {title}\n\n{summary}"
            return None

        # 并发执行所有群组摘要（受信号量控制并发数）
        results = await asyncio.gather(*[_process_single_group(ag) for ag in active_groups])
        group_summaries = [r for r in results if r]

        if not group_summaries:
            return "⚠️ 摘要生成失败"

        # 合并各群组摘要
        if progress_cb:
            await progress_cb("📝 正在合并全群总览报告...", 9, 10)
            
        if len(group_summaries) > 1:
            merge_prompt = (
                "以下是各个 Telegram 群组的独立分析结果。\n"
                "请将它们整合为一份完整的跨群总览报告，格式如下：\n\n"
                "【今日速览】\n"
                "2-3 句话概括所有群聊的整体动态和氛围。\n\n"
                "────────\n"
                "【各群动态】\n"
                "• 群名称：核心发生了什么（一句话），活跃程度\n\n"
                "────────\n"
                "【需要关注的信息】\n"
                "• 具体说明哪个群、什么时间段、哪类内容值得去翻看\n\n"
                "────────\n"
                "【风险与注意事项】\n"
                "• 警告/投诉/异常信息（如无则省略此节）\n\n"
                "────────\n"
                "【行动建议】\n"
                "• 2-4 条今天需要采取的具体行动\n\n"
                "严禁使用 # * ** __ 等 Markdown 符号，列表项用「•」。\n\n"
                "各群分析数据如下：\n\n"
                + "\n\n────────\n\n".join(group_summaries)
            )
            final = await self._call_llm(merge_prompt, is_merge=True)
            result = final or "\n\n────────\n\n".join(group_summaries)
        else:
            result = group_summaries[0]

        # 清洗最终结果
        result = self._clean_markdown(result)

        if save:
            await self.db.save_summary(
                group_id=None,
                period_start=since,
                period_end=until,
                message_count=total_msgs,
                content=result,
                model=self.model,
            )

        if progress_cb:
            await progress_cb("✅ 报告生成完成", 10, 10)

        return result

    async def daily_report(self) -> str:
        """每日报告（使用按群组分别摘要）"""
        # 获取统计
        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=24)).isoformat(timespec='seconds')
        stats = await self.db.get_stats(since=since)

        stats_text = "📊 今日数据概览:\n\n"
        for s in stats:
            stats_text += (
                f"  • {s['title']}: {s['message_count']} 条消息, "
                f"{s['active_users']} 位活跃用户\n"
            )

        # 使用按群组分别摘要
        summary = await self.summarize_per_group(hours=24, save=True)

        return f"{stats_text}\n\n---\n\n{summary}"

