"""Userbot (oddiy Telegram akkaunt): guruhdagi barcha xabarlarni o'qiydi.

Telegram botlari boshqa botlarning xabarlarini ko'rmaydi, cheklarni esa
to'lov boti yuboradi. Shuning uchun xabarlarni userbot o'qiydi.
"""
import logging

from telethon import TelegramClient, events
from telethon.sessions import StringSession

from .config import Config
from .processor import LAST_MSG_KEY, Processor

log = logging.getLogger(__name__)


def make_client(cfg: Config) -> TelegramClient:
    return TelegramClient(StringSession(cfg.userbot_session), cfg.api_id, cfg.api_hash)


class Userbot:
    def __init__(self, cfg: Config, processor: Processor):
        self.cfg = cfg
        self.processor = processor
        self.client = make_client(cfg)

    async def start(self) -> None:
        await self.client.connect()
        if not await self.client.is_user_authorized():
            raise SystemExit("Userbot avtorizatsiyadan o'tmagan: `python login.py` ni ishga tushiring")
        await self.client.get_dialogs()  # guruh ma'lumotlarini keshga olish

        async with self.processor.lock:
            self.client.add_event_handler(self._on_message, events.NewMessage(chats=self.cfg.group_id))
            self.client.add_event_handler(self._on_edit, events.MessageEdited(chats=self.cfg.group_id))
            await self._catch_up()
        me = await self.client.get_me()
        log.info("Userbot ishga tushdi: %s (%s)", me.first_name, me.id)

    async def _catch_up(self) -> None:
        """Bot o'chiq turgan paytda kelgan xabarlarni qayta ishlash."""
        last = self.processor.db.get_setting(LAST_MSG_KEY)
        if last is None:
            latest = await self.client.get_messages(self.cfg.group_id, limit=1)
            if latest:
                self.processor.db.set_setting(LAST_MSG_KEY, str(latest[0].id))
            return
        count = 0
        async for msg in self.client.iter_messages(self.cfg.group_id, min_id=int(last), reverse=True):
            await self.processor.handle_locked(msg.id, msg.date, msg.raw_text, msg.sender_id)
            count += 1
        if count:
            log.info("O'tkazib yuborilgan %s ta xabar qayta ishlandi", count)

    async def _on_message(self, event: events.NewMessage.Event) -> None:
        msg = event.message
        await self.processor.handle(msg.id, msg.date, msg.raw_text, msg.sender_id)

    async def _on_edit(self, event: events.MessageEdited.Event) -> None:
        msg = event.message
        await self.processor.handle(msg.id, msg.date, msg.raw_text, msg.sender_id, edited=True)

    async def stop(self) -> None:
        await self.client.disconnect()
