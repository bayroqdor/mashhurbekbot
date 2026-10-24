# Mashhurbek hisobot boti

Guruhga tushadigan to'lov cheklarini hisoblaydi va Z / X otchotlarni chiqaradi.

```
✅ 19.10.2026 14:02:35

164 000 UZS
QR: Mashhurbek
QR ID: 6r06OJcQCQsw0JoMY7
Pay ID: 9TU292BOH2613GT81402
tel.: +998*9886
```

## Nima qiladi

- **Z otchot** — guruhda kimdir `Kun yopildi` deb yozsa, oldingi yopilishdan shu paytgacha
  kelgan cheklar yopiladi va bot guruhga yozadi: kun qachon boshlangan (oldingi yopilish vaqti),
  qachon tugagan, nechta chek, umumiy summa.
- **X otchot** — guruhda yozish maydoni ostida doim `📊 X otchot` tugmasi turadi (yoki `/x`).
  Bosilganda oxirgi yopilishdan hozirgacha cheklar soni, summasi va boshlanish vaqti chiqadi.
- **Shaxsiy chat** (faqat `ALLOWED_USERS` dagilar uchun):
  - 📕 Z otchot — oxirgi yopilgan kun
  - 📗 X otchot — joriy ochiq kun
  - 📅 Kunlar — yopilgan kunlar ro'yxati (boshlangan → tugagan), tanlanganining hisoboti
  - 🗓 Oylik — oy tanlanadi, o'sha oydagi cheklar va summa
  - 📆 Davr — ikki sana oralig'i (`01.10.2026 - 15.10.2026`) yoki bitta sana
  - 💰 Umumiy — hozirgacha jami

### Qoidalar

- Faqat `✅` bilan boshlanib, `... UZS` qatori bor xabarlar chek hisoblanadi.
- Bir xil `Pay ID` ikki marta kelsa, bir marta hisoblanadi.
- `Kun yopildi` matni katta-kichik harf va tinish belgilariga qaramaydi (`kun yopildi!`, `Кун ёпилди`
  ham bo'ladi), lekin boshqa so'z qo'shilsa (`Bugun kun yopildi`) hisoblanmaydi.
- Oxirgi yopilishdan keyin bitta ham chek kelmagan bo'lsa, `Kun yopildi` kunni yopmaydi,
  bot buni guruhga aytadi.
- Eng birinchi kunda oldingi yopilish yo'q, shuning uchun boshlanish = birinchi chek vaqti.
- Oylik va davr hisobotlari chek guruhga tushgan vaqt bo'yicha hisoblanadi.
- Vaqtlar `Asia/Tashkent` bo'yicha.

## Nega ikkita akkaunt kerak

Telegram botlari **boshqa botlarning xabarlarini ko'rmaydi**, cheklarni esa to'lov boti yuboradi.
Shuning uchun:

- **userbot** — oddiy Telegram akkaunt (alohida raqam tavsiya etiladi), guruhda a'zo bo'lib
  barcha xabarlarni o'qiydi;
- **bot** — hisobotlarni yozadi, tugmalarni ko'rsatadi.

Ikkalasi bitta dasturda ishlaydi.

## O'rnatish

1. Python 3.11+ o'rnating, so'ng:
   ```
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   ```
2. **Bot**: @BotFather da bot yarating, tokenni `.env` ga `BOT_TOKEN` qilib yozing.
   Botni guruhga qo'shib **admin** qiling (shunda u `📊 X otchot` tugmasi bosilganini ko'radi).
3. **Userbot**: https://my.telegram.org → *API development tools* dan `API_ID` va `API_HASH` oling,
   `.env` ga yozing. Userbot akkauntini guruhga qo'shing.
4. `python login.py` — telefon raqam va kod so'raydi, oxirida guruhlar ro'yxatini (ID bilan) va
   `USERBOT_SESSION=...` satrini chiqaradi. Ikkalasini `.env` ga yozing (`GROUP_ID` va `USERBOT_SESSION`).
   ⚠️ `USERBOT_SESSION` — akkauntga to'liq kirish kaliti, hech kimga bermang.
5. `ALLOWED_USERS` ga hisobot ko'radigan odamlarning Telegram ID larini yozing (ruxsatsiz odam
   botga yozsa, bot uning ID sini aytadi).
6. Ixtiyoriy: `CHECK_SENDER_ID` ga to'lov botining ID sini yozsangiz, faqat undan kelgan cheklar
   hisoblanadi (birov qo'lda chek yozib qo'ysa hisobga kirmaydi).
7. Ixtiyoriy, eski cheklarni ham yuklash uchun — **birinchi ishga tushirishdan oldin**:
   ```
   python import_history.py 2026-10-01
   ```
8. Ishga tushirish:
   ```
   python -m bot.main
   ```
9. Guruhda `/tugma` deb yozing — `📊 X otchot` tugmasi paydo bo'ladi. Tugma har Z va X otchot
   bilan ham yangilanib turadi.

Bot o'chib qolsa, qayta yoqilganda o'chiq paytda kelgan xabarlarni o'zi o'qib chiqadi.

## Serverda doimiy ishlatish (Linux, systemd)

`/etc/systemd/system/mashhurbekbot.service`:
```
[Unit]
Description=Mashhurbek hisobot boti
After=network-online.target

[Service]
WorkingDirectory=/opt/mashhurbekbot
ExecStart=/opt/mashhurbekbot/.venv/bin/python -m bot.main
Restart=always

[Install]
WantedBy=multi-user.target
```
```
sudo systemctl enable --now mashhurbekbot
```

## Testlar

```
pip install pytest
python -m pytest
```
