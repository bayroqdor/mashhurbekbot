"""Bot (aiogram) handlerlari: guruhdagi X otchot tugmasi va shaxsiy chatdagi hisobotlar."""
import re
from datetime import date

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from . import reports
from .config import Config
from .db import Database

X_BUTTON = "📊 X otchot"

MENU_Z = "📕 Z otchot"
MENU_X = "📗 X otchot"
MENU_DAYS = "📅 Kunlar"
MENU_MONTHS = "🗓 Oylik"
MENU_PERIOD = "📆 Davr"
MENU_TOTAL = "💰 Umumiy"

DAYS_PAGE = 8


def group_keyboard() -> ReplyKeyboardMarkup:
    """Guruhda yozish maydoni ostida doim turadigan tugma."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=X_BUTTON)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def private_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_Z), KeyboardButton(text=MENU_X)],
            [KeyboardButton(text=MENU_DAYS), KeyboardButton(text=MENU_MONTHS)],
            [KeyboardButton(text=MENU_PERIOD), KeyboardButton(text=MENU_TOTAL)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


async def safe_edit(message: Message, text: str, markup: InlineKeyboardMarkup | None) -> None:
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            raise


class PeriodInput(StatesGroup):
    waiting = State()


def build_router(cfg: Config) -> Router:
    root = Router()
    group = Router()
    group.message.filter(F.chat.id == cfg.group_id)

    private = Router()
    private.message.filter(F.chat.type == "private", F.from_user.id.in_(cfg.allowed_users))
    private.callback_query.filter(F.from_user.id.in_(cfg.allowed_users))

    # --- guruh ------------------------------------------------------------

    @group.message(Command("start", "tugma"))
    async def group_button(message: Message):
        await message.answer("Pastdagi tugma orqali X otchotni ko'rishingiz mumkin.",
                             reply_markup=group_keyboard())

    @group.message(F.text == X_BUTTON)
    @group.message(Command("x"))
    async def group_x(message: Message, db: Database):
        await message.answer(reports.x_report(db, cfg.group_id, cfg.tz), reply_markup=group_keyboard())

    # --- shaxsiy chat -----------------------------------------------------

    @private.message(CommandStart())
    async def start(message: Message, state: FSMContext):
        await state.clear()
        await message.answer("Hisobot turini tanlang:", reply_markup=private_keyboard())

    @private.message(F.text == MENU_Z)
    async def menu_z(message: Message, state: FSMContext, db: Database):
        await state.clear()
        last = db.last_closing(cfg.group_id)
        await message.answer(reports.z_report(last, cfg.tz) if last else "Hali birorta kun yopilmagan.")

    @private.message(F.text == MENU_X)
    async def menu_x(message: Message, state: FSMContext, db: Database):
        await state.clear()
        await message.answer(reports.x_report(db, cfg.group_id, cfg.tz))

    @private.message(F.text == MENU_TOTAL)
    async def menu_total(message: Message, state: FSMContext, db: Database):
        await state.clear()
        await message.answer(reports.total_report(db, cfg.group_id, cfg.tz))

    # Kunlar: yopilgan kunlar ro'yxati, tanlangani bo'yicha Z otchot

    def days_markup(db: Database, offset: int) -> InlineKeyboardMarkup | None:
        closings = db.list_closings(cfg.group_id, offset, DAYS_PAGE)
        if not closings:
            return None
        rows = []
        for c in closings:
            label = (f"{reports.fmt_time(c.opened_at, cfg.tz, '%d.%m %H:%M')} → "
                     f"{reports.fmt_time(c.closed_at, cfg.tz, '%d.%m %H:%M')} · {c.check_count} ta")
            rows.append([InlineKeyboardButton(text=label, callback_data=f"day:{c.id}:{offset}")])
        nav = []
        if offset > 0:
            nav.append(InlineKeyboardButton(text="⬅️ Yangilari",
                                            callback_data=f"days:{max(offset - DAYS_PAGE, 0)}"))
        if db.count_closings(cfg.group_id) > offset + DAYS_PAGE:
            nav.append(InlineKeyboardButton(text="Eskilari ➡️", callback_data=f"days:{offset + DAYS_PAGE}"))
        if nav:
            rows.append(nav)
        return InlineKeyboardMarkup(inline_keyboard=rows)

    @private.message(F.text == MENU_DAYS)
    async def menu_days(message: Message, state: FSMContext, db: Database):
        await state.clear()
        markup = days_markup(db, 0)
        if markup is None:
            await message.answer("Hali birorta kun yopilmagan.")
            return
        await message.answer("📅 Kunni tanlang (boshlangan → tugagan):", reply_markup=markup)

    @private.callback_query(F.data.startswith("days:"))
    async def cb_days(call: CallbackQuery, db: Database):
        offset = int(call.data.split(":")[1])
        markup = days_markup(db, offset)
        await safe_edit(call.message, "📅 Kunni tanlang (boshlangan → tugagan):", markup)
        await call.answer()

    @private.callback_query(F.data.startswith("day:"))
    async def cb_day(call: CallbackQuery, db: Database):
        _, closing_id, offset = call.data.split(":")
        closing = db.get_closing(int(closing_id))
        if closing is None:
            await call.answer("Topilmadi", show_alert=True)
            return
        back = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Ro'yxatga qaytish", callback_data=f"days:{offset}")
        ]])
        await safe_edit(call.message, reports.z_report(closing, cfg.tz), back)
        await call.answer()

    # Oylik

    def months_markup(db: Database) -> InlineKeyboardMarkup | None:
        months = reports.months_with_data(db, cfg.group_id, cfg.tz)
        if not months:
            return None
        buttons = [InlineKeyboardButton(text=f"{reports.MONTHS[m - 1]} {y}", callback_data=f"month:{y}:{m}")
                   for y, m in months]
        return InlineKeyboardMarkup(inline_keyboard=[buttons[i:i + 2] for i in range(0, len(buttons), 2)])

    @private.message(F.text == MENU_MONTHS)
    async def menu_months(message: Message, state: FSMContext, db: Database):
        await state.clear()
        markup = months_markup(db)
        if markup is None:
            await message.answer("Hali cheklar yo'q.")
            return
        await message.answer("🗓 Oyni tanlang:", reply_markup=markup)

    @private.callback_query(F.data == "months")
    async def cb_months(call: CallbackQuery, db: Database):
        await safe_edit(call.message, "🗓 Oyni tanlang:", months_markup(db))
        await call.answer()

    @private.callback_query(F.data.startswith("month:"))
    async def cb_month(call: CallbackQuery, db: Database):
        _, y, m = call.data.split(":")
        back = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Oylarga qaytish", callback_data="months")
        ]])
        await safe_edit(call.message, reports.month_report(db, cfg.group_id, int(y), int(m), cfg.tz), back)
        await call.answer()

    # Davr: ikki sana oralig'i

    @private.message(F.text == MENU_PERIOD)
    async def menu_period(message: Message, state: FSMContext):
        await state.set_state(PeriodInput.waiting)
        await message.answer(
            "📆 Sanalarni kiriting:\n"
            "<code>01.10.2026 - 15.10.2026</code>\n"
            "yoki bitta sana: <code>19.10.2026</code>"
        )

    @private.message(PeriodInput.waiting, F.text)
    async def period_input(message: Message, state: FSMContext, db: Database):
        dates = []
        for d, m, y in re.findall(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", message.text):
            try:
                dates.append(date(int(y), int(m), int(d)))
            except ValueError:
                pass
        if not 1 <= len(dates) <= 2:
            await message.answer("Sana noto'g'ri. Masalan: <code>01.10.2026 - 15.10.2026</code>")
            return
        start, end = min(dates), max(dates)
        await state.clear()
        await message.answer(reports.period_report(db, cfg.group_id, start, end, cfg.tz))

    # Ruxsatsiz userlar (yoki menyudan tashqari matn)

    fallback = Router()

    @fallback.message(F.chat.type == "private")
    async def not_allowed(message: Message):
        if message.from_user and message.from_user.id in cfg.allowed_users:
            await message.answer("Menyudan tanlang:", private_keyboard())
            return
        await message.answer(
            "⛔ Sizga ruxsat berilmagan.\n"
            f"Sizning ID: <code>{message.from_user.id}</code> — uni adminga yuboring."
        )

    root.include_router(group)
    root.include_router(private)
    root.include_router(fallback)
    return root
