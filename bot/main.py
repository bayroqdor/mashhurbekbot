import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from . import reports
from .config import load_config
from .db import Closing, Database
from .handlers import build_router, group_keyboard
from .processor import Processor
from .userbot import Userbot

log = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config()
    db = Database(cfg.db_path)
    bot = Bot(cfg.bot_token, default=DefaultBotProperties(parse_mode="HTML"))

    async def on_close(closing: Closing) -> None:
        await bot.send_message(cfg.group_id, reports.z_report(closing, cfg.tz), reply_markup=group_keyboard())

    async def on_empty_close() -> None:
        await bot.send_message(cfg.group_id, "ℹ️ Oxirgi yopilishdan keyin chek kelmagan, kun yopilmadi.")

    processor = Processor(db, cfg, on_close=on_close, on_empty_close=on_empty_close)
    userbot = Userbot(cfg, processor)

    dp = Dispatcher(storage=MemoryStorage(), db=db, cfg=cfg)
    dp.include_router(build_router(cfg))

    await userbot.start()
    try:
        await dp.start_polling(bot)
    finally:
        await userbot.stop()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
