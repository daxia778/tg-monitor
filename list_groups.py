"""列出你 Telegram 里所有的群组/频道，方便选择要监控哪些"""
from __future__ import annotations
import asyncio
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat

API_ID = 611335
API_HASH = "d524b414d21f4d37f08684c1df41ac9c"
PHONE = "+959684092992"

async def main():
    client = TelegramClient("tg_monitor", API_ID, API_HASH)
    await client.start(phone=PHONE)
    
    me = await client.get_me()
    print(f"\n✅ 登录成功: {me.first_name} (@{me.username})\n")
    print("=" * 70)
    print(f"{'序号':<5} {'类型':<8} {'群组名称':<30} {'ID':<18} {'Username'}")
    print("=" * 70)
    
    idx = 1
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if isinstance(entity, (Channel, Chat)):
            dtype = "频道" if getattr(entity, "broadcast", False) else "群组"
            title = getattr(entity, "title", "?")[:28]
            eid = entity.id
            uname = getattr(entity, "username", "") or ""
            print(f"{idx:<5} {dtype:<8} {title:<30} {eid:<18} {uname}")
            idx += 1
    
    print("=" * 70)
    print(f"\n共 {idx - 1} 个群组/频道")
    print("\n📌 请记下你想监控的群组的 ID 或 Username，告诉我就行！")
    
    await client.disconnect()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
