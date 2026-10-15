# 🖥 Serverga O'rnatish va 24/7 Boshqarish Qo'llanmasi (DEPLOY.md)

Ushbu qo'llanmada loyihani **Ubuntu Linux VPS** serveriga o'rnatish, 24/7 uzluksiz ishlashini ta'minlash va yangilanishlarni kiritish bo'yicha barcha amallar yozilgan.

---

## 📌 1. Server Parametrlari

* **Server IP:** `173.212.226.178`
* **Loyiha manzili:** `/root/bots/instagram-agent`
* **Xizmat nomi (Systemd):** `instagram_agent.service`

---

## 🚀 2. Serverga Noldan O'rnatish Bosqichlari

### 1-qadam: Tizim paketlarini yangilash
Serverga SSH orqali kiring:
```bash
ssh root@173.212.226.178
```
Kerakli paketlarni o'rnating:
```bash
apt-get update -y
apt-get install -y git python3-venv python3-pip
```

### 2-qadam: Loyihani GitHub'dan yuklab olish
```bash
mkdir -p /root/bots
cd /root/bots
git clone https://github.com/Ahrorxoja/instagram-agent.git
cd instagram-agent
```

### 3-qadam: Virtual muhit (venv) va kutubxonalarni o'rnatish
```bash
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

### 4-qadam: Maxfiy sessiya fayllarini kompyuterdan serverga nusxalash
> ⚠️ **Muhim:** Git repozitoriyada `.env` va `.session` fayllar bo'lmaydi. Shuning uchun lokal kompyuteringiz terminalidan quyidagi buyruq orqali ularni serverga uzatasiz:

```bash
# Lokal kompyuteringiz terminalida bajaring:
scp .env instagram_session.json userbot_session.session leads.db leads.xlsx root@173.212.226.178:/root/bots/instagram-agent/
```

---

## ⚙️ 3. 24/7 Avtomatik Ishga Tushirish (Systemd Service)

Serverda fon xizmatini yaratish:

```bash
cat << 'EOF' > /etc/systemd/system/instagram_agent.service
[Unit]
Description=Instagram and Telegram Lead Automation Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/bots/instagram-agent
ExecStart=/root/bots/instagram-agent/venv/bin/python run.py
Restart=always
RestartSec=5
EnvironmentFile=/root/bots/instagram-agent/.env

[Install]
WantedBy=multi-user.target
EOF
```

Xizmatni faollashtirish va ishga tushirish:
```bash
systemctl daemon-reload
systemctl enable instagram_agent
systemctl start instagram_agent
```

---

## 🛠 4. Serverni Boshqarish Buyruqlari

| Vazifa | Buyruq |
|---|---|
| **Xizmat holatini tekshirish** | `systemctl status instagram_agent` |
| **Jonli loglarni ko'rish (Real-time)** | `journalctl -u instagram_agent -f` |
| **Oxirgi 50 ta logni ko'rish** | `journalctl -u instagram_agent -n 50 --no-pager` |
| **Qayta ishga tushirish (Restart)** | `systemctl restart instagram_agent` |
| **To'xtatish (Stop)** | `systemctl stop instagram_agent` |
| **Ishga tushirish (Start)** | `systemctl start instagram_agent` |

---

## 🔄 5. Kodga O'zgartirish Kiritilganda Serverni Yangilash

Kelajakda kompyuteringizda kodni o'zgartirib, GitHub'ga push qilganingizdan so'ng, serverda quyidagi 2 ta buyruqni bering:

```bash
cd /root/bots/instagram-agent
git pull
systemctl restart instagram_agent
```

---

## 🛡 6. Server Xavfsizligi va Muhim Eslatmalar

1. **Port to'qnashuvi:**
   Loyiha 8001-portda ishlaydi (`PORT=8001`). Agar port o'zgarsa, `.env` faylida o'zgartirib, xizmatni qayta ishga tushiring.
2. **Sessiyalar daxlsizligi:**
   `instagram_session.json` va `userbot_session.session` fayllarini o'chirib yubormang. Ular Instagram va Telegram akkauntingizga qayta SMS yoki kod kiritmasdan kirishni ta'minlaydi.
3. **Avtomatik tiklanish:**
   Agar server elektr uzilishi yoki qayta yuklanish (reboot) bo'lsa, `instagram_agent.service` o'z-o'zidan barcha bot va kuzatuvchilarni avtomatik qayta yoqib oladi.

