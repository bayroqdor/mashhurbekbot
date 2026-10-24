"""Guruhdagi oxirgi xabarlarni bot qanday tushunayotganini ko'rsatadi.

Ishlatish:  python diagnose.py [soni]     (standart: 30)
Har bir xabar uchun: ID, vaqt, kim yuborgan (sender ID), bot uni nima deb
tanidi va bazada bormi. Chek hisobga tushmasa, sababini shu yerdan ko'ring.
"""
import asyncio
import sys

from bot.config import load_config
from bot.db import Database
from bot.parser import is_close_message, parse_check
from bot.reports import fmt_time, money
from bot.userbot import make_client


async def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    cfg = load_config()
    db = Database(cfg.db_path)
    client = make_client(cfg)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Userbot avtorizatsiyadan o'tmagan: `python login.py` ni ishga tushiring")
    await client.get_dialogs()

    group = await client.get_entity(cfg.group_id)
    print(f"Guruh: {getattr(group, 'title', cfg.group_id)} ({cfg.group_id})")
    print(f"CHECK_SENDER_ID: {cfg.check_sender_id or 'ko`rsatilmagan (hamma cheklar hisoblanadi)'}")
    print(f"Bazadagi oxirgi ko'rilgan xabar ID: {db.get_setting('last_msg_id')}\n")

    messages = [m async for m in client.iter_messages(cfg.group_id, limit=limit)]
    for msg in reversed(messages):
        text = msg.raw_text or ""
        check = parse_check(text)
        in_db = db.conn.execute(
            "SELECT closing_id FROM checks WHERE chat_id = ? AND msg_id = ?", (cfg.group_id, msg.id)
        ).fetchone()
        if is_close_message(text):
            status = "KUN YOPILDI"
        elif check:
            if cfg.check_sender_id is not None and msg.sender_id != cfg.check_sender_id:
                status = f"CHEK {money(check.amount)} — HISOBLANMAYDI: sender CHECK_SENDER_ID ga teng emas"
            elif in_db:
                status = f"CHEK {money(check.amount)} — bazada bor" + (
                    " (yopilgan kunda)" if in_db[0] else " (joriy kunda)")
            else:
                status = f"CHEK {money(check.amount)} — BAZADA YO'Q"
        elif text.lstrip().startswith("✅"):
            status = "✅ bor, lekin chek deb TANILMADI (format boshqacha)"
        else:
            status = "-"
        edited = " (tahrirlangan)" if msg.edit_date else ""
        first_line = text.strip().splitlines()[0][:60] if text.strip() else "<matn yo'q>"
        print(f"#{msg.id}  {fmt_time(int(msg.date.timestamp()), cfg.tz)}  sender={msg.sender_id}{edited}")
        print(f"    {status}")
        print(f"    {first_line!r}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
