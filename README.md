# 🚀 Instagram & Telegram Mijozlarni Yig'ish va Avtomatlashtirish Tizimi

Ushbu tizim Instagram Direct (yoki veb-sayt / ManyChat / Make) orqali kelgan mijoz ma'lumotlarini qabul qilib, ularni **PostgreSQL / Supabase** va **Excel** faylga saqlaydi hamda **Telegram** orqali administratorga bildirishnoma va mijozga avtomatik xabar yuborish imkonini beradi.

---

## 📌 Tizim qanday ishlaydi?

```mermaid
flowchart TD
    IG[Instagram Direct / ManyChat / Webhook] -->|Ism, Tel, IG profil| API[FastAPI Backend]
    API -->|1. Saqlash| DB[(Supabase / PostgreSQL)]
    API -->|2. Qo'shish| XL[Excel: leads.xlsx]
    API -->|3. Raqamni tekshirish| UB[Telethon Userbot]
    API -->|4. Yangi mijoz bildirishnomasi| TG_ADMIN[Telegram Bot: Adminga xabar]
    TG_ADMIN -->|5. Admin 'Ha, xabar yuborish' tugmasini bosadi| BOT_HANDLER[Aiogram Callback]
    BOT_HANDLER -->|6. Mijozga avtomatik xabar jo'natish| CLIENT_TG[Mijozning Telegrami]
```

### ⚠️ Muhim texnik eslatma:
Telegram Bot API qoidalariga ko'ra, rasmiy botlar begona shaxsning telefon raqamiga birinchi bo'lib xabar yoza olmaydi (botga avval kirib `/start` bosgan bo'lishi shart).
Shuning uchun ushbu loyihada:
- **Telegram Bot (aiogram 3)** — Administrator bilan muloqot qilish, bildirishnoma va "Ha / Yo'q" tugmalarini chiqarish uchun;
- **Telegram Client / Userbot (Telethon)** — Telefon raqam egasini Telegram bazasidan topish va unga to'g'ridan-to'g'ri xabar jo'natish uchun ishlatiladi.

---

## 🛠 O'rnatish bo'yicha qo'llanma

### 1. Kutubxonalarni o'rnatish
Virtual muhit yarating va kerakli paketlarni o'rnating:

```bash
python3 -m venv venv
source venv/bin/activate  # Windows uchun: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Sozlamalarni kiritish (.env)
Loyihada `.env.example` faylidan nusxa olib, `.env` faylini yarating:

```bash
cp .env.example .env
```

`.env` faylini ochib, o'z parametrlaringizni kiriting:

| O'zgaruvchi | Qayerdan olinadi? | Tavsif |
|---|---|---|
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) | Telegram botingiz tokeni |
| `ADMIN_TELEGRAM_ID` | [@userinfobot](https://t.me/userinfobot) | O'zingizning Telegram ID raqamingiz |
| `TELEGRAM_API_ID` | [my.telegram.org](https://my.telegram.org) | Telegram API ID |
| `TELEGRAM_API_HASH` | [my.telegram.org](https://my.telegram.org) | Telegram API Hash |
| `TELEGRAM_PHONE` | Shaxsiy telefon | Userbot sifatida ishlaydigan akkaunt raqami |
| `DATABASE_URL` | Supabase / PostgreSQL | Ma'lumotlar bazasi URL manzili |

> **Supabase ulanish namunasi:**
> `DATABASE_URL=postgresql+asyncpg://postgres.your_id:your_password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres`
> *(Sinov uchun SQLite ishlatmoqchi bo'lsangiz: `sqlite+aiosqlite:///./leads.db` qoldirishingiz mumkin)*

---

### 3. Supabase / PostgreSQL jadval strukturasi (SQL)
Agar Supabase SQL Editor orqali jadvalni qo'lda yaratmoqchi bo'lsangiz:

```sql
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    instagram_username VARCHAR(255),
    phone_number VARCHAR(50) NOT NULL,
    telegram_id BIGINT,
    telegram_username VARCHAR(255),
    telegram_found BOOLEAN DEFAULT FALSE,
    message_sent BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone_number);
```
*(Dastur ishga tushganda SQLAlchemy jadvallarni avtomatik ham yaratadi)*

---

### 4. Telethon (Userbot) sessiyasini birinchi marta faollashtirish
Raqam egasiga to'g'ridan-to'g'ri xabar yuborish uchun quyidagi buyruqni bir marta ishga tushiring va Telegramdan kelgan SMS/kodni kiriting:

```bash
python -m app.services.telegram_service
```
Sessiya fayli (`userbot_session.session`) avtomatik saqlanadi.

---

### 5. Tizimni to'liq ishga tushirish
FastAPI serveri va Telegram botni bir vaqtda ishga tushirish uchun:

```bash
python run.py
```

Server ishga tushgach:
- **FastAPI Hujjatlari (Swagger UI):** `http://localhost:8000/docs`
- **Excel fayl:** `leads.xlsx` (avtomatik yaratiladi)
- **Telegram Bot:** Sizga yangi mijozlar haqida xabar jo'natishga tayyor holatda bo'ladi.

---

## 📡 API va Webhook orqali mijoz qo'shish

### 1. To'g'ridan-to'g'ri API (`POST /api/leads`)
```bash
curl -X POST "http://localhost:8000/api/leads" \
     -H "Content-Type: application/json" \
     -d '{
       "full_name": "Aziz Rahimov",
       "instagram_username": "aziz_rahimov",
       "phone_number": "+998901234567"
     }'
```

### 2. Instagram Direct / ManyChat Webhook (`POST /webhook/instagram`)
ManyChat yoki Make (Integromat) orqali ushbu webhook URL manziliga JSON yuborish kifoya.

### 3. Sinov skripti
Tizimni sinab ko'rish uchun maxsus skript:
```bash
python test_lead.py
```

---

## 📂 Loyiha tuzilishi

```
├── app/
│   ├── bot/
│   │   ├── bot.py             # Aiogram bot obyektlari va bildirishnomalar
│   │   ├── handlers.py        # Admin komandalari va "Ha/Yo'q" tugmalari
│   │   └── keyboards.py       # Inline tugmalar
│   ├── services/
│   │   ├── excel_service.py   # Excelga saqlash va yangilash
│   │   ├── lead_service.py    # Yangi lead to'liq siklini boshqarish
│   │   └── telegram_service.py# Telethon userbot (raqamni tekshirish va xabar yozish)
│   ├── config.py              # Sozlamalar (.env)
│   ├── database.py            # Supabase / PostgreSQL ulanishi
│   ├── models.py              # SQLAlchemy jadvallari
│   ├── schemas.py             # Pydantic schemalari
│   └── main.py                # FastAPI endpoints
├── .env.example
├── .gitignore
├── requirements.txt
├── test_lead.py               # Sinov skripti
└── run.py                     # Dasturni ishga tushiruvchi markaziy fayl
```

# instagram-agent
