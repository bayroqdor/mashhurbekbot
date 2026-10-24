#!/usr/bin/env bash
# Debian serverga birinchi marta o'rnatish.
# Ishlatish:  sudo bash install.sh
# Qayta ishga tushirish xavfsiz: bor narsalarni buzmaydi.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/bayroqdor/mashhurbekbot.git}"
BRANCH="${BRANCH:-main}"
APP_DIR=/opt/mashhurbekbot
APP_USER=mashhurbekbot
SERVICE=mashhurbekbot

as_app() { runuser -u "$APP_USER" -- "$@"; }

if [ "$(id -u)" -ne 0 ]; then
    echo "root sifatida ishga tushiring: sudo bash $0" >&2
    exit 1
fi

echo "==> Paketlar o'rnatilmoqda"
apt-get update -q
apt-get install -y -q git python3 python3-venv sqlite3 ca-certificates

if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
    echo "Python 3.11 yoki yangisi kerak (Debian 12+). Hozirgisi: $(python3 --version)" >&2
    exit 1
fi

echo "==> '$APP_USER' foydalanuvchisi"
if ! id -u "$APP_USER" >/dev/null 2>&1; then
    useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi
mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> Kod: $REPO_URL ($BRANCH)"
if [ -d "$APP_DIR/.git" ]; then
    as_app git -C "$APP_DIR" pull --ff-only
else
    as_app git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

echo "==> Python muhiti"
if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
    as_app python3 -m venv "$APP_DIR/.venv"
fi
as_app "$APP_DIR/.venv/bin/pip" install -q --upgrade pip
as_app "$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

as_app mkdir -p "$APP_DIR/data"
if [ ! -f "$APP_DIR/.env" ]; then
    as_app cp "$APP_DIR/.env.example" "$APP_DIR/.env"
fi
chmod 600 "$APP_DIR/.env"

echo "==> systemd xizmati"
install -m 644 "$APP_DIR/deploy/$SERVICE.service" "/etc/systemd/system/$SERVICE.service"
systemctl daemon-reload
systemctl enable "$SERVICE" >/dev/null

if grep -qE '^USERBOT_SESSION=.+' "$APP_DIR/.env"; then
    systemctl restart "$SERVICE"
    echo "==> Tayyor, bot ishga tushdi. Loglar: journalctl -u $SERVICE -f"
else
    cat <<MSG

==> O'rnatildi. Keyingi qadamlar (DEPLOY.md, 3-bo'lim):
  1) nano $APP_DIR/.env            # BOT_TOKEN, API_ID, API_HASH, ALLOWED_USERS
  2) cd $APP_DIR && sudo runuser -u $APP_USER -- .venv/bin/python login.py
  3) nano $APP_DIR/.env            # USERBOT_SESSION va GROUP_ID
  4) sudo systemctl start $SERVICE
MSG
fi
