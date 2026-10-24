"""SQLite saqlovchi.

Har bir chek `checks` jadvaliga yoziladi. "Kun yopildi" kelganda shu xabardan
oldingi barcha yopilmagan cheklar yangi `closings` yozuviga biriktiriladi.
`closing_id IS NULL` bo'lgan cheklar — hozirgi ochiq kun (X otchot).
"""
import os
import sqlite3
from dataclasses import dataclass

from .parser import Check

_SCHEMA = """
CREATE TABLE IF NOT EXISTS checks (
    id          INTEGER PRIMARY KEY,
    chat_id     INTEGER NOT NULL,
    msg_id      INTEGER NOT NULL,
    msg_time    INTEGER NOT NULL,
    amount      INTEGER NOT NULL,
    paid_at     TEXT,
    pay_id      TEXT,
    qr_id       TEXT,
    qr_name     TEXT,
    closing_id  INTEGER REFERENCES closings(id),
    UNIQUE (chat_id, msg_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_checks_pay_id ON checks (chat_id, pay_id) WHERE pay_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_checks_open ON checks (chat_id, closing_id);
CREATE INDEX IF NOT EXISTS ix_checks_time ON checks (chat_id, msg_time);

CREATE TABLE IF NOT EXISTS closings (
    id              INTEGER PRIMARY KEY,
    chat_id         INTEGER NOT NULL,
    msg_id          INTEGER NOT NULL,
    opened_at       INTEGER NOT NULL,
    opened_by_check INTEGER NOT NULL DEFAULT 0,
    closed_at       INTEGER NOT NULL,
    check_count     INTEGER NOT NULL,
    total           INTEGER NOT NULL,
    UNIQUE (chat_id, msg_id)
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class Closing:
    id: int
    msg_id: int
    opened_at: int
    opened_by_check: bool  # True: oldingi yopilish yo'q, boshlanish = birinchi chek vaqti
    closed_at: int
    check_count: int
    total: int


@dataclass(frozen=True)
class Summary:
    count: int
    total: int
    first_at: int | None
    last_at: int | None


class Database:
    def __init__(self, path: str):
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # --- yozish ---------------------------------------------------------

    def add_check(self, chat_id: int, msg_id: int, msg_time: int, check: Check) -> bool:
        """Chekni qo'shadi. Takroriy (shu xabar yoki shu Pay ID) bo'lsa False.

        Chek allaqachon yopilgan kunga tegishli bo'lsa (tahrir yoki tarixni yuklash),
        o'sha kunga qo'shiladi va kun summasi yangilanadi.
        """
        row = self.conn.execute(
            "SELECT id FROM closings WHERE chat_id = ? AND msg_id > ? ORDER BY msg_id LIMIT 1",
            (chat_id, msg_id),
        ).fetchone()
        closing_id = row[0] if row else None
        with self.conn:
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO checks"
                " (chat_id, msg_id, msg_time, amount, paid_at, pay_id, qr_id, qr_name, closing_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    chat_id, msg_id, msg_time, check.amount,
                    check.paid_at.isoformat(sep=" ") if check.paid_at else None,
                    check.pay_id, check.qr_id, check.qr_name, closing_id,
                ),
            )
            if cur.rowcount == 1 and closing_id is not None:
                self.conn.execute(
                    "UPDATE closings SET check_count = check_count + 1, total = total + ? WHERE id = ?",
                    (check.amount, closing_id),
                )
        return cur.rowcount == 1

    def close_day(self, chat_id: int, msg_id: int, closed_at: int) -> Closing | None:
        """Ochiq kunni yopadi. Yopiladigan chek bo'lmasa yoki xabar takror bo'lsa None."""
        if self.conn.execute(
            "SELECT 1 FROM closings WHERE chat_id = ? AND msg_id = ?", (chat_id, msg_id)
        ).fetchone():
            return None
        count, total, first_at = self.conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount), 0), MIN(msg_time) FROM checks"
            " WHERE chat_id = ? AND closing_id IS NULL AND msg_id < ?",
            (chat_id, msg_id),
        ).fetchone()
        if count == 0:
            return None

        previous = self.last_closing(chat_id)
        opened_at = previous.closed_at if previous else first_at
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO closings (chat_id, msg_id, opened_at, opened_by_check, closed_at, check_count, total)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (chat_id, msg_id, opened_at, previous is None, closed_at, count, total),
            )
            self.conn.execute(
                "UPDATE checks SET closing_id = ? WHERE chat_id = ? AND closing_id IS NULL AND msg_id < ?",
                (cur.lastrowid, chat_id, msg_id),
            )
        return self.get_closing(cur.lastrowid)

    def add_closing_raw(self, chat_id: int, msg_id: int, closed_at: int) -> None:
        """Tarixni yuklashda: yopilishni yozib qo'yadi, hisob-kitob `rebuild` da."""
        self.conn.execute(
            "INSERT OR IGNORE INTO closings (chat_id, msg_id, opened_at, closed_at, check_count, total)"
            " VALUES (?, ?, ?, ?, 0, 0)",
            (chat_id, msg_id, closed_at, closed_at),
        )
        self.conn.commit()

    def rebuild(self, chat_id: int) -> None:
        """Barcha kunlarni xabarlar tartibi bo'yicha qaytadan hisoblaydi.

        Har bir yopilish o'zidan oldingi yopilishdan keyingi cheklarni oladi.
        Cheksiz yopilishlar o'chiriladi (jonli rejimdagi kabi, ular kunni yopmaydi).
        """
        with self.conn:
            self.conn.execute("UPDATE checks SET closing_id = NULL WHERE chat_id = ?", (chat_id,))
            prev_msg_id, prev_closed_at = 0, None
            closings = self.conn.execute(
                "SELECT id, msg_id, closed_at FROM closings WHERE chat_id = ? ORDER BY msg_id", (chat_id,)
            ).fetchall()
            for closing_id, msg_id, closed_at in closings:
                bounds = (chat_id, prev_msg_id, msg_id)
                count, total, first_at = self.conn.execute(
                    "SELECT COUNT(*), COALESCE(SUM(amount), 0), MIN(msg_time) FROM checks"
                    " WHERE chat_id = ? AND msg_id > ? AND msg_id < ?",
                    bounds,
                ).fetchone()
                if count == 0:
                    self.conn.execute("DELETE FROM closings WHERE id = ?", (closing_id,))
                    continue
                self.conn.execute(
                    "UPDATE checks SET closing_id = ? WHERE chat_id = ? AND msg_id > ? AND msg_id < ?",
                    (closing_id, *bounds),
                )
                self.conn.execute(
                    "UPDATE closings SET opened_at = ?, opened_by_check = ?, check_count = ?, total = ?"
                    " WHERE id = ?",
                    (prev_closed_at if prev_closed_at is not None else first_at,
                     prev_closed_at is None, count, total, closing_id),
                )
                prev_msg_id, prev_closed_at = msg_id, closed_at

    def get_setting(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.conn.commit()

    # --- o'qish ---------------------------------------------------------

    def _closing(self, row) -> Closing | None:
        if not row:
            return None
        return Closing(row[0], row[1], row[2], bool(row[3]), row[4], row[5], row[6])

    _CLOSING_COLS = "id, msg_id, opened_at, opened_by_check, closed_at, check_count, total"

    def get_closing(self, closing_id: int) -> Closing | None:
        return self._closing(self.conn.execute(
            f"SELECT {self._CLOSING_COLS} FROM closings WHERE id = ?", (closing_id,)
        ).fetchone())

    def last_closing(self, chat_id: int) -> Closing | None:
        return self._closing(self.conn.execute(
            f"SELECT {self._CLOSING_COLS} FROM closings WHERE chat_id = ? ORDER BY msg_id DESC LIMIT 1",
            (chat_id,),
        ).fetchone())

    def list_closings(self, chat_id: int, offset: int, limit: int) -> list[Closing]:
        rows = self.conn.execute(
            f"SELECT {self._CLOSING_COLS} FROM closings WHERE chat_id = ?"
            " ORDER BY msg_id DESC LIMIT ? OFFSET ?",
            (chat_id, limit, offset),
        ).fetchall()
        return [self._closing(r) for r in rows]

    def count_closings(self, chat_id: int, start: int | None = None, end: int | None = None) -> int:
        sql, args = "SELECT COUNT(*) FROM closings WHERE chat_id = ?", [chat_id]
        if start is not None:
            sql, args = sql + " AND closed_at >= ? AND closed_at < ?", args + [start, end]
        return self.conn.execute(sql, args).fetchone()[0]

    def _summary(self, where: str, args: tuple) -> Summary:
        count, total, first_at, last_at = self.conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount), 0), MIN(msg_time), MAX(msg_time)"
            f" FROM checks WHERE {where}",
            args,
        ).fetchone()
        return Summary(count, total, first_at, last_at)

    def open_summary(self, chat_id: int) -> Summary:
        return self._summary("chat_id = ? AND closing_id IS NULL", (chat_id,))

    def range_summary(self, chat_id: int, start: int, end: int) -> Summary:
        """[start, end) oralig'idagi cheklar (unix vaqt)."""
        return self._summary("chat_id = ? AND msg_time >= ? AND msg_time < ?", (chat_id, start, end))

    def total_summary(self, chat_id: int) -> Summary:
        return self._summary("chat_id = ?", (chat_id,))
