from datetime import datetime

from bot.parser import is_close_message, parse_amount, parse_check

SAMPLE = """✅ 19.10.2026 14:02:35

164 000 UZS
QR: Mashhurbek
QR ID: 6r06OJcQCQsw0JoMY7
Pay ID: 9TU292BOH2613GT81402
tel.: +998*9886"""


def test_parse_sample_check():
    check = parse_check(SAMPLE)
    assert check is not None
    assert check.amount == 164_000_00
    assert check.paid_at == datetime(2026, 10, 19, 14, 2, 35)
    assert check.pay_id == "9TU292BOH2613GT81402"
    assert check.qr_id == "6r06OJcQCQsw0JoMY7"
    assert check.qr_name == "Mashhurbek"


def test_not_a_check():
    assert parse_check("Salom") is None
    assert parse_check(None) is None
    assert parse_check(SAMPLE.replace("✅", "❌")) is None
    assert parse_check("✅ 19.10.2026 14:02:35\nsumma yo'q") is None


def test_amount_formats():
    assert parse_amount("164 000") == 164_000_00
    assert parse_amount("164 000") == 164_000_00
    assert parse_amount("1 250 000,50") == 1_250_000_50
    assert parse_amount("164.000") == 164_000_00
    assert parse_amount("5000") == 5000_00
    assert parse_amount("12.5") == 12_50


def test_close_message():
    assert is_close_message("Kun yopildi")
    assert is_close_message("  kun   YOPILDI! ")
    assert is_close_message("Kun yopildi ✅")
    assert is_close_message("Кун ёпилди")
    assert not is_close_message("Kun yopildimi?")
    assert not is_close_message("Bugun kun yopildi")
    assert not is_close_message(None)
