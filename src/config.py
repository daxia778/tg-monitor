"""
配置管理模块
从 config.yaml 和环境变量加载配置
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# 加载 .env
load_dotenv(PROJECT_ROOT / ".env")


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载配置文件，环境变量优先级更高"""
    if config_path is None:
        config_path = PROJECT_ROOT / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 环境变量覆盖
    env_api_id = os.getenv("TG_API_ID")
    env_api_hash = os.getenv("TG_API_HASH")
    env_phone = os.getenv("TG_PHONE")
    env_ai_key = os.getenv("AI_API_KEY")
    env_ai_url = os.getenv("AI_API_URL")

    if env_api_id:
        cfg["telegram"]["api_id"] = int(env_api_id)
    elif cfg["telegram"].get("api_id"):
        cfg["telegram"]["api_id"] = int(cfg["telegram"]["api_id"])

    if env_api_hash:
        cfg["telegram"]["api_hash"] = env_api_hash
    if env_phone:
        cfg["telegram"]["phone"] = env_phone
    if env_ai_key:
        cfg["ai"]["api_key"] = env_ai_key
    if env_ai_url:
        cfg["ai"]["api_url"] = env_ai_url

    # 多 key 轮询：从 .env 加载 AI_API_KEY_1 … AI_API_KEY_5
    # 只要有任意一个数字 key，就用列表模式覆盖 yaml 中的 api_keys
    numbered_keys = [
        os.getenv(f"AI_API_KEY_{i}") for i in range(1, 6)
    ]
    numbered_keys = [k for k in numbered_keys if k]  # 过滤空值
    if numbered_keys:
        cfg["ai"]["api_keys"] = numbered_keys

    # Bot Token 环境变量覆盖
    env_bot_token = os.getenv("BOT_TOKEN")
    if env_bot_token:
        cfg.setdefault("bot", {})["token"] = env_bot_token

    # Bot Owner ID 环境变量覆盖（P0 修复：敏感 ID 从 .env 读取，不写在 yaml）
    env_owner_id = os.getenv("BOT_OWNER_ID")
    if env_owner_id:
        try:
            cfg.setdefault("bot", {})["owner_id"] = int(env_owner_id)
        except ValueError:
            pass  # 格式错误时保留 yaml 中的值，避免启动失败

    # 解析数据库路径为绝对路径
    db_path = cfg.get("database", {}).get("path", "./data/tg_monitor.db")
    if not Path(db_path).is_absolute():
        cfg["database"]["path"] = str(PROJECT_ROOT / db_path)

    return cfg


def validate_config(cfg: dict) -> List[str]:
    """验证配置，返回错误列表"""
    errors = []

    tg = cfg.get("telegram", {})
    if not tg.get("api_id"):
        errors.append("缺少 telegram.api_id（请到 https://my.telegram.org 获取）")
    if not tg.get("api_hash"):
        errors.append("缺少 telegram.api_hash")

    groups = cfg.get("groups", [])
    if not groups:
        errors.append("未配置任何监控群组（groups 列表为空）")

    return errors
