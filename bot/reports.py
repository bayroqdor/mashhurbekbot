"""Hisobot matnlari (HTML)."""
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .db import Closing, Database, Summary

MONTHS = [
    "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
]


def money(tiyin: int) -> str:
    sums, rest = divmod(tiyin, 100)
    text = f"{sums:,}".replace(",", " ")
    if rest:
        text += f",{rest:02d}"
    return f"{text} UZS"


def fmt_time(ts: int | None, tz: ZoneInfo, pattern: str = "%d.%m.%Y %H:%M:%S") -> str:
    if ts is None:
        return "—"
    return datetime.fromtimestamp(ts, tz).strftime(pattern)


def day_bounds(d: date, tz: ZoneInfo) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=tz).timestamp())


def month_bounds(year: int, month: int, tz: ZoneInfo) -> tuple[int, int]:
    nxt = date(year + month // 12, month % 12 + 1, 1)
    return day_bounds(date(year, month, 1), tz), day_bounds(nxt, tz)


def z_report(closing: Closing, tz: ZoneInfo) -> str:
    start_note = " (birinchi chek)" if closing.opened_by_check else ""
    return (
        "🔒 <b>Z otchot — kun yopildi</b>\n\n"
        f"🟢 Boshlangan: {fmt_time(closing.opened_at, tz)}{start_note}\n"
        f"🔴 Tugagan: {fmt_time(closing.closed_at, tz)}\n"
        f"🧾 Cheklar soni: <b>{closing.check_count} ta</b>\n"
        f"💰 Umumiy summa: <b>{money(closing.total)}</b>"
    )


def x_report(db: Database, chat_id: int, tz: ZoneInfo) -> str:
    last = db.last_closing(chat_id)
    s = db.open_summary(chat_id)
    if last:
        started = fmt_time(last.closed_at, tz)
    elif s.first_at:
        started = f"{fmt_time(s.first_at, tz)} (birinchi chek)"
    else:
        started = "—"
    return (
        "📊 <b>X otchot — joriy kun</b>\n\n"
        f"🟢 Kun boshlangan: {started}\n"
        f"🕐 Hozir: {fmt_time(int(time.time()), tz)}\n"
        f"🧾 Cheklar soni: <b>{s.count} ta</b>\n"
        f"💰 Summa: <b>{money(s.total)}</b>\n"
        f"🧾 Oxirgi chek: {fmt_time(s.last_at, tz)}"
    )


def _summary_lines(s: Summary, tz: ZoneInfo) -> str:
    return (
        f"🧾 Cheklar soni: <b>{s.count} ta</b>\n"
        f"💰 Umumiy summa: <b>{money(s.total)}</b>\n"
        f"⏱ Birinchi chek: {fmt_time(s.first_at, tz)}\n"
        f"⏱ Oxirgi chek: {fmt_time(s.last_at, tz)}"
    )


def month_report(db: Database, chat_id: int, year: int, month: int, tz: ZoneInfo) -> str:
    start, end = month_bounds(year, month, tz)
    s = db.range_summary(chat_id, start, end)
    return (
        f"🗓 <b>{MONTHS[month - 1]} {year}</b>\n\n"
        f"{_summary_lines(s, tz)}\n"
        f"🔒 Yopilgan kunlar: {db.count_closings(chat_id, start, end)} ta"
    )


def period_report(db: Database, chat_id: int, start: date, end: date, tz: ZoneInfo) -> str:
    lo, hi = day_bounds(start, tz), day_bounds(end + timedelta(days=1), tz)
    s = db.range_summary(chat_id, lo, hi)
    return (
        f"📆 <b>{start:%d.%m.%Y} — {end:%d.%m.%Y}</b>\n\n"
        f"{_summary_lines(s, tz)}\n"
        f"🔒 Yopilgan kunlar: {db.count_closings(chat_id, lo, hi)} ta"
    )


def total_report(db: Database, chat_id: int, tz: ZoneInfo) -> str:
    s = db.total_summary(chat_id)
    o = db.open_summary(chat_id)
    return (
        "💰 <b>Umumiy hisobot (hozirgacha)</b>\n\n"
        f"{_summary_lines(s, tz)}\n"
        f"🔒 Yopilgan kunlar: {db.count_closings(chat_id)} ta\n\n"
        f"Shundan joriy (yopilmagan) kunda: {o.count} ta, {money(o.total)}"
    )


def months_with_data(db: Database, chat_id: int, tz: ZoneInfo) -> list[tuple[int, int]]:
    """Cheklari bor oylar, yangisi birinchi."""
    s = db.total_summary(chat_id)
    if s.first_at is None:
        return []
    first = datetime.fromtimestamp(s.first_at, tz)
    last = datetime.fromtimestamp(s.last_at, tz)
    result = []
    y, m = last.year, last.month
    while (y, m) >= (first.year, first.month):
        if db.range_summary(chat_id, *month_bounds(y, m, tz)).count:
            result.append((y, m))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return result
