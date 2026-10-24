"""Guruhning eski xabarlarini bazaga yuklash.

Ishlatish:  python import_history.py 2026-10-01
Ko'rsatilgan sanadan boshlab barcha cheklar va "Kun yopildi" xabarlari bazaga
yoziladi, so'ng barcha kunlar qaytadan hisoblanadi. Guruhga hech narsa
yuborilmaydi. Bazada allaqachon bor xabarlar ikki marta hisoblanmaydi, shuning
uchun qayta ishga tushirish xavfsiz. Ishga tushirishdan oldin botni to'xtating.
"""
import asyncio
import sys
from datetime import datetime

from bot.config import load_config
from bot.db import Database
from bot.processor import Processor
from bot.userbot import make_client


async def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Ishlatish: python import_history.py YYYY-MM-DD")
    cfg = load_config()
    since = datetime.strptime(sys.argv[1], "%Y-%m-%d").replace(tzinfo=cfg.tz)
    db = Database(cfg.db_path)
    processor = Processor(db, cfg)

    client = make_client(cfg)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Avval `python login.py` ni ishga tushiring")
    await client.get_dialogs()

    seen = checks = closes = 0
    async for msg in client.iter_messages(cfg.group_id, offset_date=since, reverse=True):
        seen += 1
        result = processor.import_message(msg.id, msg.date, msg.raw_text, msg.sender_id)
        checks += result == "check"
        closes += result == "close"
    await client.disconnect()
    db.rebuild(cfg.group_id)

    print(f"Ko'rib chiqildi: {seen} ta xabar")
    print(f"Yangi cheklar: {checks} ta, \"Kun yopildi\": {closes} ta")
    print(f"Bazada jami yopilgan kunlar: {db.count_closings(cfg.group_id)} ta")


if __name__ == "__main__":
    asyncio.run(main())
