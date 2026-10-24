import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bot import reports
from bot.config import Config
from bot.db import Database
from bot.processor import Processor

GROUP = -100123
TZ = ZoneInfo("Asia/Tashkent")


def make(tmp_path):
    cfg = Config("t", 1, "h", "s", GROUP, frozenset({1}), None, TZ, str(tmp_path / "db.sqlite"))
    db = Database(cfg.db_path)
    closed, empty = [], []

    async def on_close(c):
        closed.append(c)

    async def on_empty():
        empty.append(True)

    return db, Processor(db, cfg, on_close, on_empty), closed, empty


def check_text(amount: str, pay_id: str) -> str:
    return f"✅ 19.10.2026 14:02:35\n\n{amount} UZS\nQR: Mashhurbek\nQR ID: X\nPay ID: {pay_id}\ntel.: +998*9886"


T0 = datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc)  # 09:00 Toshkent


def feed(proc, items):
    async def run():
        for i, text in enumerate(items, start=1):
            await proc.handle(i, T0 + timedelta(minutes=i), text, 42)
    asyncio.run(run())


def test_full_day_cycle(tmp_path):
    db, proc, closed, empty = make(tmp_path)
    feed(proc, [
        check_text("164 000", "A"),
        check_text("36 000", "B"),
        check_text("36 000", "B"),        # takroriy Pay ID — hisoblanmaydi
        "Salom",
        "Kun yopildi",
        check_text("10 000", "C"),
        "kun yopildi",
        "Kun yopildi",                     # yangi chek yo'q — kun yopilmaydi
        check_text("5 000", "D"),
    ])

    assert [(c.check_count, c.total) for c in closed] == [(2, 200_000_00), (1, 10_000_00)]
    assert closed[0].opened_by_check and closed[0].opened_at == int((T0 + timedelta(minutes=1)).timestamp())
    assert not closed[1].opened_by_check and closed[1].opened_at == closed[0].closed_at
    assert empty == [True]

    open_s = db.open_summary(GROUP)
    assert (open_s.count, open_s.total) == (1, 5_000_00)
    total = db.total_summary(GROUP)
    assert (total.count, total.total) == (4, 215_000_00)

    z = reports.z_report(closed[0], TZ)
    assert "2 ta" in z and "200 000 UZS" in z and "19.10.2026 09:05:00" in z
    x = reports.x_report(db, GROUP, TZ)
    assert "1 ta" in x and "5 000 UZS" in x and reports.fmt_time(closed[1].closed_at, TZ) in x

    assert reports.months_with_data(db, GROUP, TZ) == [(2026, 10)]
    assert "215 000 UZS" in reports.month_report(db, GROUP, 2026, 10, TZ)
    d = datetime(2026, 10, 19).date()
    assert "215 000 UZS" in reports.period_report(db, GROUP, d, d, TZ)
    assert "0 ta" in reports.period_report(db, GROUP, d + timedelta(days=1), d + timedelta(days=1), TZ)


def test_reprocessing_is_idempotent(tmp_path):
    db, proc, closed, empty = make(tmp_path)
    items = [check_text("1 000", "A"), "Kun yopildi"]
    feed(proc, items)
    feed(proc, items)
    assert len(closed) == 1 and empty == []
    assert db.count_closings(GROUP) == 1


def test_import_out_of_order_matches_live(tmp_path):
    items = [
        check_text("100", "A"), check_text("200", "B"), "Kun yopildi",
        check_text("300", "C"), "Kun yopildi", "Kun yopildi",
        check_text("400", "D"), "Kun yopildi", check_text("500", "E"),
    ]
    live_db, live_proc, _, _ = make(tmp_path / "live")
    feed(live_proc, items)

    # Bot oxirgi qismini jonli ko'rgan, boshi esa keyin tarixdan yuklangan
    db, proc, _, _ = make(tmp_path / "imp")
    split = 6
    asyncio.run(_feed_from(proc, items, split))
    for i, text in enumerate(items[:split], start=1):
        proc.import_message(i, T0 + timedelta(minutes=i), text, 42)
    db.rebuild(GROUP)

    def state(d):
        return [(c.msg_id, c.opened_at, c.opened_by_check, c.closed_at, c.check_count, c.total)
                for c in d.list_closings(GROUP, 0, 100)], d.open_summary(GROUP)

    assert state(db) == state(live_db)
    assert len(state(db)[0]) == 3


async def _feed_from(proc, items, start):
    for i, text in enumerate(items[start:], start=start + 1):
        await proc.handle(i, T0 + timedelta(minutes=i), text, 42)


def test_edited_message_becomes_check(tmp_path):
    db, proc, closed, _ = make(tmp_path)

    async def run():
        await proc.handle(1, T0, "⏳ To'lov kutilmoqda", 42)
        await proc.handle(2, T0 + timedelta(minutes=1), "Kun yopildi", 42)  # chek yo'q — yopilmaydi
        await proc.handle(3, T0 + timedelta(minutes=2), check_text("1 000", "Z"), 42)
        await proc.handle(4, T0 + timedelta(minutes=3), "Kun yopildi", 42)
        # 1-xabar keyin ✅ ga tahrirlandi — yopilgan kunga qo'shiladi
        await proc.handle(1, T0, check_text("2 000", "Y"), 42, edited=True)
        await proc.handle(4, T0 + timedelta(minutes=3), "Kun yopildi", 42, edited=True)
    asyncio.run(run())

    last = db.last_closing(GROUP)
    assert (last.check_count, last.total) == (2, 3_000_00)
    assert db.open_summary(GROUP).count == 0
    assert db.count_closings(GROUP) == 1
