# MMebel sklad

Mebel ishlab chiqarish va sklad uchun Telegram bot hamda 3 ta web panel (Telegram Mini App):

| Rol | Botda | Panelda |
|---|---|---|
| **Admin** | buyurtma yaratish/o'zgartirish, hisob-kitob, qarzlar, haydovchilar, statistika | hammasi + foydalanuvchilar va rollar, sozlamalar, jurnal |
| **Omborchi** | ombor, yetkazishlar nazorati, dostavka hisoboti | buyurtma holatlari, yetkazish, ombor qoldig'i, oylik hisobot |
| **Xodim** | faol buyurtmalar | ishlab chiqarish rejasi (model bo'yicha jamlangan), faol buyurtmalar |
| **Diller** | zakaz berish, bekor qilish, holat, to'lov bildirish | — |

Panel bot ichidagi **🖥 Panel** tugmasi (yoki chap pastdagi menyu tugmasi) orqali ochiladi. Login va parol yo'q: server Telegram imzosini (initData HMAC) tekshiradi, rolni esa bazadan oladi.

## Tuzilma

```
bot.py                  kirish nuqtasi (Render: python bot.py)
mmebel/
  config.py             sozlamalar (faqat muhit o'zgaruvchilaridan)
  store.py              Firebase / xotira ombori abstraksiyasi
  services/             biznes mantiq (bot va panel uchun yagona)
    orders.py           buyurtmalar, statuslar (tranzaksiya bilan)
    inventory.py        ombor qoldig'i (tranzaksiya bilan)
    finance.py          qarz hisobi, to'lovlar, haydovchi balanslari
    reports.py          hisobotlar, statistika, ishlab chiqarish rejasi
    users.py, catalog.py rollar, sozlanadigan ro'yxatlar, migratsiya
  bot/                  aiogram handlerlari, klaviaturalar, FSM ombori
  web/                  REST API, initData tekshiruvi, panel (HTML/CSS/JS)
  events.py, notify.py  xabarnomalar
  scheduler.py          kunlik eslatmalar va zaxira nusxa
tests/                  32 ta test (servislar, API, bot oqimlari)
database.rules.json     Firebase Rules: mijozdan to'g'ridan-to'g'ri kirish yopiq
```

## O'rnatish (Render)

1. **Muhit o'zgaruvchilari** (Render → Environment):
   - `API_TOKEN` — BotFather tokeni.
   - Firebase kaliti: `serviceAccountKey.json` ni Secret File sifatida qoldirish mumkin, yoki uning matnini `FIREBASE_CREDENTIALS_JSON` ga qo'ying.
   - `OWNER_IDS` — doimiy admin(lar)ning Telegram ID si (ixtiyoriy, tavsiya etiladi).
   - `CRON_SECRET` — tashqi cron ishlatilsa (ixtiyoriy).
   - `PUBLIC_URL` kerak emas: Render `RENDER_EXTERNAL_URL` ni o'zi beradi.
2. **Firebase Rules**: Firebase Console → Realtime Database → Rules ga `database.rules.json` mazmunini qo'yib, **Publish** bosing. Server Admin SDK orqali ishlaydi, Rules unga ta'sir qilmaydi.
3. Deploy. Birinchi ishga tushishda eski kodda qattiq yozilgan rollar va diller ID'lari bazaga bir marta ko'chiriladi (`meta/migrations`).

### Cron (ixtiyoriy)

Eslatmalar ichki rejalashtiruvchi orqali avtomatik yuboriladi (09:00, 15:00, 15:05; kuniga bir marta). Server uxlab qolsa, tashqi cron uyg'otishi mumkin:

```
GET https://<server>/cron/morning     Header: X-Cron-Secret: <CRON_SECRET>
GET https://<server>/cron/overdue
GET https://<server>/cron/tomorrow
```

Eski `?token=API_TOKEN` usuli **o'chirildi**: bot tokeni URL va loglarga tushardi.

## Lokal ishlab chiqish

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # API_TOKEN, Firebase kaliti; USE_POLLING=1
python bot.py
pytest                       # testlar Firebase'siz, xotirada ishlaydi
ruff check mmebel tests
```

## Xavfsizlik

- Webhook `secret_token` bilan himoyalangan — soxta update yuborib bo'lmaydi.
- Panel API: har so'rovda Telegram imzosi, rol tekshiruvi, rate limit (120/daqiqa), narxlar faqat adminga.
- Panelda `innerHTML` ishlatilmaydi (XSS yo'q), CSP sarlavhalari o'rnatilgan.
- Ombor qoldig'i, status o'zgarishlari, to'lov tasdig'i va eslatmalar Firebase tranzaksiyalari orqali — ikki kishi bir vaqtda bossa ham ikki marta yozilmaydi.
- Barcha muhim amallar `audit_log` ga yoziladi (panel → Boshqa → Jurnal).
