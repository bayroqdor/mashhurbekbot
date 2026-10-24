"""Guruhga tushadigan chek va "Kun yopildi" xabarlarini tanib olish.

Chek namunasi:
    ✅ 19.10.2026 14:02:35

    164 000 UZS
    QR: Mashhurbek
    QR ID: 6r06OJcQCQsw0JoMY7
    Pay ID: 9TU292BOH2613GT81402
    tel.: +998*9886
"""
import re
from dataclasses import dataclass
from datetime import datetime

CLOSE_PHRASES = {"kun yopildi", "кун ёпилди"}

_AMOUNT_RE = re.compile(r"^\s*(\d[\d\s  .,]*?)\s*UZS\b", re.IGNORECASE | re.MULTILINE)
_PAID_AT_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2}:\d{2})")
_PAY_ID_RE = re.compile(r"^\s*Pay\s*ID\s*:\s*(\S+)", re.IGNORECASE | re.MULTILINE)
_QR_ID_RE = re.compile(r"^\s*QR\s*ID\s*:\s*(\S+)", re.IGNORECASE | re.MULTILINE)
_QR_NAME_RE = re.compile(r"^\s*QR\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class Check:
    amount: int  # tiyinda (1 so'm = 100 tiyin)
    paid_at: datetime | None
    pay_id: str | None
    qr_id: str | None
    qr_name: str | None


def is_close_message(text: str | None) -> bool:
    if not text:
        return False
    normalized = " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())
    return normalized in CLOSE_PHRASES


def parse_amount(raw: str) -> int | None:
    """'164 000' -> 16400000, '164 000,50' -> 16400050, '164.000' -> 16400000."""
    s = re.sub(r"[\s  ]", "", raw)
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):
        return int(re.sub(r"[.,]", "", s)) * 100
    m = re.fullmatch(r"(\d+)(?:[.,](\d{1,2}))?", s)
    if not m:
        return None
    return int(m.group(1)) * 100 + int((m.group(2) or "0").ljust(2, "0"))


def parse_check(text: str | None) -> Check | None:
    if not text or not text.lstrip().startswith("✅"):
        return None
    m = _AMOUNT_RE.search(text)
    if not m:
        return None
    amount = parse_amount(m.group(1))
    if amount is None:
        return None

    paid_at = None
    if dm := _PAID_AT_RE.search(text):
        try:
            paid_at = datetime.strptime(f"{dm.group(1)} {dm.group(2)}", "%d.%m.%Y %H:%M:%S")
        except ValueError:
            pass

    def group(regex: re.Pattern) -> str | None:
        found = regex.search(text)
        return found.group(1) if found else None

    return Check(
        amount=amount,
        paid_at=paid_at,
        pay_id=group(_PAY_ID_RE),
        qr_id=group(_QR_ID_RE),
        qr_name=group(_QR_NAME_RE),
    )
