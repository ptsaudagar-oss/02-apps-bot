# 📬 00-GMAIL_BOT — Telegram Gmail Assistant (Autonomous Koyeb 24/7 & Local Engine)

Komponen utama ekosistem bot Telegram untuk pemantauan, triase, dan notifikasi email multi-akun (`pt.saudagar@gmail.com`, `8m.shop.online@gmail.com`, dan Privacy Enclave `kafnun84@gmail.com`) secara real-time.

---

## 🌟 Fitur Utama
1. **Multi-Account IMAP/SMTP Engine**: Mendukung triase otomatis email bisnis B2B, order e-commerce, dan isolasi akun pribadi owner.
2. **Interactive Inline Keyboards**: Baca email, tandai sudah dibaca (*mark as read*), balas cepat via AI Gemini, dan refresh inbox langsung dari chat Telegram.
3. **Privacy Enclave Guard**: Mengisolasi email personal owner agar tidak ter-broadcast ke grup publik atau channel umum.
4. **Micro HTTP Health Server**: Dilengkapi HTTP health check bawaan (`0.0.0.0:${PORT:-8000}/health`) untuk verifikasi status runtime cloud.

---

## 🚀 Menjalankan Secara Lokal

```bash
# Menggunakan Doppler (Rekomendasi Utama)
doppler run -- python 02-TELEGRAM_BOT/00-GMAIL_BOT/main.py

# Atau menggunakan venv lokal
python 02-TELEGRAM_BOT/00-GMAIL_BOT/main.py
```

---

## ☁️ Deployment ke Cloud Koyeb (24/7 Nonstop Region Singapore)

### 3 Langkah Aktivasi di Koyeb (app.koyeb.com):
1. **Connect GitHub Repo**: Hubungkan `ptsaudagar-oss/02-apps-bot` (Branch `main`).
2. **Builder**: Pilih **Dockerfile** -> `Dockerfile.telegram` (Port `8000`, Health Check `/health`, Region `Singapore`).
3. **Environment**: Masukkan Environment Variables yang sudah tersimpan di Doppler.

### Opsi Local Docker Container:
```bash
docker build -f Dockerfile.telegram -t telegram-gmail-bot .
docker run -d -p 8000:8000 --env-file .env telegram-gmail-bot
```

---

## 🔑 Environment Variables Wajib
| Variable | Deskripsi | Contoh Nilai |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Token Bot Telegram dari @BotFather | `8947277071:AA...` |
| `TELEGRAM_AUTHORIZED_CHAT_IDS` | ID Akun/Grup Telegram terotorisasi | `7828326094` |
| `GMAIL_PRIMARY_ACCOUNT` | Email Akun Bisnis Utama | `pt.saudagar@gmail.com` |
| `GMAIL_ECOMMERCE_ACCOUNT` | Email Akun Toko Online | `8m.shop.online@gmail.com` |
| `GMAIL_OWNER_ACCOUNT` | Email Enclave Owner | `kafnun84@gmail.com` |
| `GMAIL_APP_PASSWORD` | Google App Password (16 huruf) | `xxxx xxxx xxxx xxxx` |
| `GMAIL_AUTH_MODE` | Mode autentikasi | `app_password` |
| `GMAIL_CHECK_INTERVAL_SECONDS` | Interval scan inbox | `60` |
| `GEMINI_API_KEY` | Kunci API Google AI (Opsional) | `AIzaSy...` |
| `PORT` | Port HTTP Health Check | `8000` |
