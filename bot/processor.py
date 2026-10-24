"""Guruh xabarlarini qayta ishlash: cheklarni yozish va kunni yopish."""
import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime

from .config import Config
from .db import Closing, Database
from .parser import is_close_message, parse_check

log = logging.getLogger(__name__)

LAST_MSG_KEY = "last_msg_id"


class Processor:
    def __init__(
        self,
        db: Database,
        cfg: Config,
        on_close: Callable[[Closing], Awaitable[None]] | None = None,
        on_empty_close: Callable[[], Awaitable[None]] | None = None,
    ):
        self.db = db
        self.cfg = cfg
        self.on_close = on_close
        self.on_empty_close = on_empty_close
        self.lock = asyncio.Lock()

    async def handle(self, msg_id: int, date: datetime, text: str | None, sender_id: int | None,
                     notify: bool = True) -> None:
        async with self.lock:
            await self.handle_locked(msg_id, date, text, sender_id, notify)

    async def handle_locked(self, msg_id: int, date: datetime, text: str | None, sender_id: int | None,
                            notify: bool = True) -> None:
        """`self.lock` olingan holda chaqiriladi."""
        chat_id = self.cfg.group_id
        ts = int(date.timestamp())
        last = int(self.db.get_setting(LAST_MSG_KEY) or 0)
        if msg_id > last:
            self.db.set_setting(LAST_MSG_KEY, str(msg_id))

        if is_close_message(text):
            closing = self.db.close_day(chat_id, msg_id, ts)
            if closing:
                log.info("Kun yopildi: %s ta chek, %s", closing.check_count, closing.total)
                if notify and self.on_close:
                    await self.on_close(closing)
            elif notify and self.on_empty_close and msg_id > last:
                await self.on_empty_close()
            return

        check = parse_check(text)
        if check is None:
            return
        if self.cfg.check_sender_id is not None and sender_id != self.cfg.check_sender_id:
            log.warning("Chek boshqa joydan keldi (sender=%s), hisoblanmadi: msg %s", sender_id, msg_id)
            return
        if self.db.add_check(chat_id, msg_id, ts, check):
            log.info("Chek qo'shildi: msg %s, %s tiyin", msg_id, check.amount)
        else:
            log.info("Takroriy chek o'tkazib yuborildi: msg %s, Pay ID %s", msg_id, check.pay_id)
