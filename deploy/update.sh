#!/usr/bin/env bash
# Yangi versiyani o'rnatish: sudo bash /opt/mashhurbekbot/deploy/update.sh
set -euo pipefail

APP_DIR=/opt/mashhurbekbot
APP_USER=mashhurbekbot
SERVICE=mashhurbekbot

as_app() { runuser -u "$APP_USER" -- "$@"; }

if [ "$(id -u)" -ne 0 ]; then
    echo "root sifatida ishga tushiring: sudo bash $0" >&2
    exit 1
fi

echo "==> Kod yangilanmoqda"
as_app git -C "$APP_DIR" pull --ff-only
as_app "$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

install -m 644 "$APP_DIR/deploy/$SERVICE.service" "/etc/systemd/system/$SERVICE.service"
systemctl daemon-reload
systemctl restart "$SERVICE"
sleep 3
systemctl --no-pager --lines=15 status "$SERVICE"
