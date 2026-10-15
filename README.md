# 🚀 Instagram Direct & Telegram Lead Automation System

Ushbu tizim **Instagram Direct** orqali yangi suhbatlarni real-time (har 15 soniyada) avtomatik kuzatib, suhbatdoshlarning profil ma'lumotlari (Bio, havola, kontakt telefon) hamda chatdagi xabarlardan **Telefon raqami** va **Telegram manzillarini** ajratib oladi. Ma'lumotlarni **SQLite / PostgreSQL** bazasiga va **Excel** fayliga saqlaydi hamda **Telegram Userbot** orqali mijozlarga avtomatik xabar jo'natadi.

---

## 🏗 Loyiha Arxitekturasi va Tuzilishi

```text
instagram-agent/
│
├── app/
│   ├── bot/                      # Aiogram 3 Telegram Bot moduli (Admin boshqaruvi)
│   │   ├── bot.py                # Bot obyekti, Dispatcher va adminga bildirishnoma yuboruvchi
│   │   ├── handlers.py           # Admin buyruqlari (/send_all, /scan, /excel, /stats)
│   │   └── keyboards.py          # Inline tugmalar (Telegramda ochish, Telefon qilindi)
│   │
│   ├── services/                 # Asosiy biznes mantiq xizmatlari
│   │   ├── instagram_service.py  # Instagram hisobiga ulanish va Direct chatlarni real-time kuzatish
│   │   ├── parser_service.py     # Regex parser: bio va chatdan telefon va Telegramni ajratish
│   │   ├── telegram_service.py   # Telethon Userbot: raqamni Telegramda tekshirish va xabar yozish
│   │   ├── broadcast_service.py  # Ommaviy xavfsiz xabar tarqatish (35s delay, anti-spam)
│   │   ├── excel_service.py      # OpenPyXL: Dropdown list bilan leads.xlsx yuritish
│   │   └── lead_service.py       # Yangi lead to'liq siklini boshqarish
│   │
│   ├── config.py                 # Pydantic-settings orqali .env konfiguratsiyasini yuklash
│   ├── database.py               # SQLAlchemy asinxron ma'lumotlar bazasi ulanishi
│   ├── models.py                 # Ma'lumotlar bazasi modellari (Lead jadvali)
│   ├── schemas.py                # Pydantic schemalari va ma'lumotlar validatsiyasi
│   └── main.py                   # FastAPI REST API va Webhook serveri
│
├── .env                          # Maxfiy sozlamalar (tokenlar, loginlar, parollar)
├── .env.example                  # Namuna konfiguratsiya fayli
├── .gitignore                    # Git uchun istisnolar (sessiyalar, baza, env)
├── requirements.txt              # Kerakli Python kutubxonalari
├── run.py                        # FastAPI + Telegram Bot + Instagram Watcherni parallel yurgizuvchi
├── test_lead.py                  # API ni test qilish skripti
├── DEPLOY.md                     # Serverga o'rnatish va 24/7 sozlash qo'llanmasi
└── README.md                     # Ushbu hujjat
```

---

## 🧩 Kod Qismlari va Vazifalari

### 1. `app/services/instagram_service.py` (Instagram Direct Kuzatuvchi)
* `instagrapi` orqali Instagram hisobingizga (`stolda.uz`) bir marta kiradi va sessiyani `instagram_session.json` ga saqlaydi (qayta parol so'ramaydi).
* Fon jarayonida har 15 soniyada Direct'dagi eng so'nggi suhbatlarni tekshiradi.
* Siz Instagramda yangi odamga yozganingizda yoki sizga javob kelganda:
  1. Suhbatdoshning profili (Bio, havolalari, kontaktdagi telefon) va chat matnini ko'radi;
  2. Telefon yoki Telegram topilsa — **bir zumda bazaga saqlaydi**;
  3. Excel faylga yangi qator qilib qo'shadi;
  4. Adminga Telegram bot orqali xabar beradi;
  5. Agar `INSTAGRAM_AUTO_SEND=true` bo'lsa — uning Telegramiga darhol andoza xabarni yuboradi!

### 2. `app/services/parser_service.py` (Matn Tahlilchisi)
* O'zbekiston (`+998...`) va xalqaro telefon raqamlarni istalgan formatdan (`+998 90 123 45 67`, `90 123-45-67`, `99890...`) aniqlab, toza xalqaro ko'rinishga keltiradi.
* Telegram havolalarini (`t.me/username`, `telegram.me/...`, `@username`) matndan ajratib oladi.

### 3. `app/services/telegram_service.py` (Telethon Userbot)
* Rasmiy Telegram Bot API begona raqamga birinchi bo'lib yozolmaydi. Shu sababli bu modul **Telethon (MTProto Client)** orqali ishlaydi.
* Shaxsiy / ishchi raqamingiz nomidan mijozning Telegramiga to'g'ridan-to'g'ri xabar jo'natadi.

### 4. `app/services/broadcast_service.py` (Xavfsiz Xabar Tarqatuvchi)
* Bazadagi barcha hali xabar bormagan (`message_sent == False`) mijozlarga ketma-ket xabar jo'natadi.
* **Anti-Spam Himoyasi:** Har bir xabar orasida **35 soniya aqlli tanaffus** qo'yilgan. Akkauntingiz Telegram tomonidan spam deb bloklanmaydi.
* Adminga har 5 ta mijozda jonli progress hisobotini berib boradi.
* Bitta odamga **hech qachon 2 marta xabar bormaydi** (duplikatdan 100% himoya).

### 5. `app/services/excel_service.py` (Excel Boshqaruvchisi)
* `leads.xlsx` faylini yaratadi va yuritadi.
* **DataValidation (Dropdown list):**
  - "Xabar yuborildi" ustuni — `[ Ha / Yo'q ]` tanlovli ro'yxat;
  - "Telefon qilindi" ustuni — `[ Ha / Yo'q ]` tanlovli ro'yxat;
  - "Holati" ustuni — `[ Yangi, Bog'lanildi, Rad etildi, Sotildi ]` ro'yxati.
* Ustun kengliklari va sarlavhalari avtomatik chiroyli formatlanadi.

---

## 🤖 Telegram Bot Buyruqlari (`@Stoldainstabot`)

Telegram botingiz menyusida quyidagi qulay buyruqlar mavjud:

| Buyruq | Tavsif |
|---|---|
| **`/send_all`** | 🚀 Bazadagi barcha hali xabar olmagan mijozlarga xavfsiz (35s interval bilan) avtomatik xabar jo'natishni boshlash. |
| **`/scan`** | 🔍 Instagram Direct'dagi oxirgi 100 ta suhbatni chuqur skanerlash. *(Masalan: `/scan 200` yoki `/scan 500` qilib ko'proq tekshirish mumkin).* |
| **`/excel`** | 📑 Eng so'nggi yangilangan `leads.xlsx` faylini to'g'ridan-to'g'ri Telegram chatga yuklab beradi. |
| **`/stats`** | 📊 Jami mijozlar, telefon qilinganlar va xabar yuborilganlar statistikasi. |
| **`/stop_send`** | 🛑 Xabar tarqatish jarayonini darhol to'xtatish. |
| **`/help`** | ℹ️ Botdan foydalanish bo'yicha to'liq qo'llanma. |

---

## 🔔 Xabar Kelgandagi Tugmalar:
Har bir mijoz ma'lumoti kelganda uning ostida:
1. **`📱 Telegramda yozish`** — bitta bosishda mijoz bilan shaxsiy chat ochiladi.
2. **`📞 Telefon qilindi`** — qo'ng'iroq qilgach bosasiz, Excelda avtomatik "Ha" bo'lib belgilanadi.
3. **`📸 Instagram`** — mijozning Instagram profiliga to'g'ridan-to'g'ri havola.
4. **`❌ Kerak emas`** — rad etish.

---

## ⚙️ Sozlamalar (.env)
Barcha konfiguratsiyalar [.env](file:///Users/ahrorxojausmonxojayev/Development/bots/instagram%20agent/.env) faylida saqlanadi:
* `BOT_TOKEN` — Admin bilan muloqot qiluvchi Telegram bot tokeni.
* `ADMIN_TELEGRAM_ID` — Administrator Telegram ID raqami.
* `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` — Userbot API kalitlari.
* `TELEGRAM_PHONE` — Xabar jo'natuvchi Telegram raqami.
* `INSTAGRAM_USERNAME` / `INSTAGRAM_PASSWORD` — Instagram login va paroli.
* `INSTAGRAM_AUTO_SEND=true` — Yangi odam topilishi bilan avtomat xabar yuborish rejimi.
* `AUTO_MESSAGE_TEMPLATE` — Mijozlarga boradigan andoza matn.
