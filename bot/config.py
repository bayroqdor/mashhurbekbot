import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    api_id: int
    api_hash: str
    userbot_session: str
    group_id: int
    allowed_users: frozenset[int]
    check_sender_id: int | None
    tz: ZoneInfo
    db_path: str


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f".env faylida {name} ko'rsatilmagan")
    return value


def _int_list(raw: str) -> frozenset[int]:
    return frozenset(int(x) for x in raw.replace(" ", "").split(",") if x)


def load_config() -> Config:
    load_dotenv()
    sender = os.getenv("CHECK_SENDER_ID", "").strip()
    return Config(
        bot_token=_required("BOT_TOKEN"),
        api_id=int(_required("API_ID")),
        api_hash=_required("API_HASH"),
        userbot_session=_required("USERBOT_SESSION"),
        group_id=int(_required("GROUP_ID")),
        allowed_users=_int_list(os.getenv("ALLOWED_USERS", "")),
        check_sender_id=int(sender) if sender else None,
        tz=ZoneInfo(os.getenv("TIMEZONE", "Asia/Tashkent")),
        db_path=os.getenv("DB_PATH", "data/bot.db"),
    )
