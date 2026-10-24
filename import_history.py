"""Guruhning eski xabarlarini bazaga yuklash.

Ishlatish:  python import_history.py 2026-10-01
Faqat bo'sh bazada, botni birinchi marta ishga tushirishdan OLDIN bajariladi.
Ko'rsatilgan sanadan boshlab barcha cheklar va "Kun yopildi" xabarlari
ketma-ket qayta ishlanadi. Guruhga hech narsa yuborilmaydi.
"""
import asyncio
import sys
from datetime import datetime

from bot.config import load_config
from bot.db import Database
from bot.processor import LAST_MSG_KEY, Processor
from bot.userbot import make_client


async def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Ishlatish: python import_history.py YYYY-MM-DD")
    cfg = load_config()
    since = datetime.strptime(sys.argv[1], "%Y-%m-%d").replace(tzinfo=cfg.tz)
    db = Database(cfg.db_path)
    if db.get_setting(LAST_MSG_KEY) is not None:
        raise SystemExit("Baza bo'sh emas: tarixni faqat birinchi ishga tushirishdan oldin yuklash mumkin")
    processor = Processor(db, cfg)

    client = make_client(cfg)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Avval `python login.py` ni ishga tushiring")
    await client.get_dialogs()

    count = 0
    async for msg in client.iter_messages(cfg.group_id, offset_date=since, reverse=True):
        await processor.handle(msg.id, msg.date, msg.raw_text, msg.sender_id, notify=False)
        count += 1
    await client.disconnect()
    print(f"{count} ta xabar ko'rib chiqildi.")


if __name__ == "__main__":
    asyncio.run(main())
