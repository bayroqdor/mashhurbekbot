#!/usr/bin/env bash
# Bazaning kunlik zaxira nusxasi, oxirgi 30 kun saqlanadi.
# cron orqali ishlaydi (DEPLOY.md, 6-bo'lim).
set -euo pipefail

DB=/opt/mashhurbekbot/data/bot.db
DEST=/var/backups/mashhurbekbot
KEEP_DAYS=30

[ -f "$DB" ] || exit 0
mkdir -p "$DEST"
chmod 700 "$DEST"
sqlite3 "$DB" ".backup '$DEST/bot-$(date +%F).db'"
find "$DEST" -name 'bot-*.db' -mtime +"$KEEP_DAYS" -delete
