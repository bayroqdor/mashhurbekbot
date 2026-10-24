# Debian serverga o'rnatish

Debian 12 (bookworm) yoki 13 (trixie) uchun. Debian 11 va eskisida Python 3.11 yo'q, ishlamaydi.
Barcha buyruqlar serverda `root` sifatida (yoki `sudo` bilan) bajariladi.

Natijada:

| Nima | Qayerda |
|---|---|
| Kod | `/opt/mashhurbekbot` |
| Sozlamalar | `/opt/mashhurbekbot/.env` |
| Baza | `/opt/mashhurbekbot/data/bot.db` |
| Xizmat | `mashhurbekbot` (systemd) — server qayta yoqilganda o'zi ishga tushadi |
| Foydalanuvchi | `mashhurbekbot` (tizim useri, root huquqisiz) |

> ⚠️ Bot bir vaqtda faqat **bitta joyda** ishlashi kerak. Kompyuteringizda ishlatayotgan bo'lsangiz,
> serverda yoqishdan oldin uni o'chiring: bir xil `BOT_TOKEN` ikki joyda xato beradi, bir xil
> `USERBOT_SESSION` esa ikki joyda ishlatilsa Telegram sessiyani bekor qilishi mumkin.

## 1. Serverga ulanish

```
ssh root@SERVER_IP
```

## 2. O'rnatish skripti

```
apt-get update && apt-get install -y git
git clone https://github.com/bayroqdor/mashhurbekbot.git /tmp/mashhurbekbot
bash /tmp/mashhurbekbot/deploy/install.sh
rm -rf /tmp/mashhurbekbot
```

Skript: kerakli paketlarni o'rnatadi, `mashhurbekbot` userini yaratadi, kodni `/opt/mashhurbekbot`
ga yuklaydi, Python muhitini tayyorlaydi, `.env` faylini yaratadi va systemd xizmatini yoqadi.

**Repo private bo'lsa**, GitHub'da *Settings → Developer settings → Personal access tokens →
Fine-grained* orqali faqat shu repoga *Contents: Read-only* ruxsatli token yarating va manzilni shunday bering:

```
git clone https://TOKEN@github.com/bayroqdor/mashhurbekbot.git /tmp/mashhurbekbot
REPO_URL=https://TOKEN@github.com/bayroqdor/mashhurbekbot.git bash /tmp/mashhurbekbot/deploy/install.sh
```

## 3. Sozlash

1. `.env` ni to'ldiring (`BOT_TOKEN`, `API_ID`, `API_HASH`, `ALLOWED_USERS`; nimani qayerdan olish
   [README.md](README.md#ornatish) da yozilgan):
   ```
   nano /opt/mashhurbekbot/.env
   ```
   Saqlash: `Ctrl+O`, `Enter`, chiqish: `Ctrl+X`.

2. Userbot akkauntiga kiring — telefon raqam va Telegram yuborgan kodni so'raydi:
   ```
   cd /opt/mashhurbekbot
   runuser -u mashhurbekbot -- .venv/bin/python login.py
   ```
   Oxirida guruhlar ro'yxati va `USERBOT_SESSION=...` satri chiqadi.

3. Shu satrni va kerakli guruh ID sini `.env` ga yozing (`USERBOT_SESSION=` va `GROUP_ID=`):
   ```
   nano /opt/mashhurbekbot/.env
   ```

4. *(Ixtiyoriy)* Bot qo'shilishidan oldingi eski cheklarni yuklash — 5-bo'limdagi
   "Eski xabarlarni yuklash" ga qarang.

## 4. Ishga tushirish

```
systemctl start mashhurbekbot
systemctl status mashhurbekbot
```

`active (running)` yozuvi chiqsa, bot ishlayapti. Loglarda `Userbot ishga tushdi` va
`Start polling` qatorlari bo'lishi kerak. Keyin guruhga `/tugma` deb yozing.

## 5. Kundalik boshqaruv

| Vazifa | Buyruq |
|---|---|
| Loglarni jonli kuzatish | `journalctl -u mashhurbekbot -f` |
| Oxirgi 100 qator log | `journalctl -u mashhurbekbot -n 100` |
| Qayta ishga tushirish | `systemctl restart mashhurbekbot` |
| To'xtatish | `systemctl stop mashhurbekbot` |
| `.env` o'zgargandan keyin | `systemctl restart mashhurbekbot` |
| Yangi versiyani o'rnatish | `bash /opt/mashhurbekbot/deploy/update.sh` |

Bot qulasa, systemd uni 10 soniyadan keyin o'zi qayta yoqadi. To'xtab turgan paytda kelgan
cheklar qayta yoqilganda o'qib olinadi.

### Eski xabarlarni yuklash

Bot birinchi marta yoqilganda guruh tarixini o'qimaydi, faqat undan keyin kelganlarni sanaydi.
Eski cheklar va "Kun yopildi" lar kerak bo'lsa (sanani o'zingiz tanlang):

```
cd /opt/mashhurbekbot
systemctl stop mashhurbekbot
runuser -u mashhurbekbot -- .venv/bin/python import_history.py 2026-10-01
systemctl start mashhurbekbot
```

Bazada bor xabarlar ikki marta hisoblanmaydi, barcha kunlar qaytadan hisoblanadi — skriptni
xohlagancha qayta ishga tushirish mumkin. Guruhga hech narsa yozilmaydi.

### Chek hisobga tushmasa

```
cd /opt/mashhurbekbot
runuser -u mashhurbekbot -- .venv/bin/python diagnose.py 30
```

Oxirgi 30 ta xabarning har biri uchun bot uni nima deb tanigani (chek / kun yopildi / tanilmadi),
kim yuborgani (`sender=`) va bazada bor-yo'qligi chiqadi. Bu ishlayotgan botga xalaqit bermaydi.

## 6. Bazani zaxiralash (tavsiya etiladi)

Har kuni 03:00 da bazaning nusxasini `/var/backups/mashhurbekbot` ga oladi, oxirgi 30 kunini saqlaydi:

```
echo '0 3 * * * root bash /opt/mashhurbekbot/deploy/backup.sh' > /etc/cron.d/mashhurbekbot-backup
```

Zaxiradan tiklash:

```
systemctl stop mashhurbekbot
cp /var/backups/mashhurbekbot/bot-2026-10-24.db /opt/mashhurbekbot/data/bot.db
chown mashhurbekbot:mashhurbekbot /opt/mashhurbekbot/data/bot.db
systemctl start mashhurbekbot
```

Server butunlay yo'qolishi mumkinligini hisobga olsangiz, `/var/backups/mashhurbekbot` ni vaqti-vaqti
bilan boshqa joyga ham ko'chirib turing.

## 7. Muammolar

| Belgi (logda) | Sabab va yechim |
|---|---|
| `.env faylida ... ko'rsatilmagan` | `.env` da shu qator bo'sh. To'ldirib, `systemctl restart mashhurbekbot`. |
| `Userbot avtorizatsiyadan o'tmagan` | `USERBOT_SESSION` noto'g'ri yoki bekor qilingan. 3-bo'limdagi `login.py` ni qaytadan bajaring. |
| `Unauthorized` / `Not Found` (aiogram) | `BOT_TOKEN` noto'g'ri. |
| `TelegramConflictError` | Bot boshqa joyda ham ishlab turibdi. O'sha joyda o'chiring. |
| `Could not find the input entity` | Userbot akkaunti guruhda yo'q yoki `GROUP_ID` noto'g'ri. |
| Tugma bosilsa javob yo'q | Bot guruhda admin emas. Botni admin qiling. |
| Chek kelsa ham hisoblanmayapti | `diagnose.py` ni ishga tushiring (5-bo'lim). `BAZADA YO'Q` — chek bot birinchi yoqilishidan oldin kelgan, `import_history.py` bilan yuklang. `HISOBLANMAYDI: sender` — `CHECK_SENDER_ID` ga o'sha `sender=` raqamini yozing yoki bo'sh qoldiring. `TANILMADI` — chek formati boshqacha, o'sha xabar matnini dasturchiga yuboring. |
