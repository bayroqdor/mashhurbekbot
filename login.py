"""Userbot akkauntiga kirish va USERBOT_SESSION satrini olish.

Ishlatish:  python login.py
Telefon raqam va Telegram yuborgan kodni so'raydi, oxirida .env ga
yoziladigan USERBOT_SESSION satrini va guruhlar ID ro'yxatini chiqaradi.
"""
import asyncio
import os

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession


async def main() -> None:
    load_dotenv()
    api_id = int(os.getenv("API_ID") or input("API_ID: "))
    api_hash = os.getenv("API_HASH") or input("API_HASH: ")
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start()

    print("\nGuruhlaringiz (GROUP_ID uchun):")
    async for dialog in client.iter_dialogs():
        if dialog.is_group:
            print(f"  {dialog.id}\t{dialog.name}")

    print("\n.env fayliga quyidagini yozing (hech kimga bermang!):\n")
    print(f"USERBOT_SESSION={client.session.save()}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
