# 📬 00-GMAIL_BOT — Telegram Gmail Assistant (Autonomous 24/7 Cloud Engine)

Komponen utama ekosistem bot Telegram untuk pemantauan, triase, dan notifikasi email multi-akun (`pt.saudagar@gmail.com`, `8m.shop.online@gmail.com`, dan Privacy Enclave `kafnun84@gmail.com`) secara real-time.

---

## 🌟 Fitur Utama
1. **Multi-Account IMAP/SMTP Engine**: Mendukung triase otomatis email bisnis B2B, order e-commerce, dan isolasi akun pribadi owner.
2. **Interactive Inline Keyboards**: Baca email, tandai sudah dibaca (*mark as read*), balas cepat via AI Gemini, dan refresh inbox langsung dari chat Telegram.
3. **Privacy Enclave Guard**: Mengisolasi email personal owner agar tidak ter-broadcast ke grup publik atau channel umum.
4. **Cloud-Ready HTTP Health Check**: Dilengkapi micro HTTP server bawaan (`0.0.0.0:${PORT}`) untuk memenuhi persyaratan Web Service di Render.com / Railway / Fly.io.

---

## 🚀 Menjalankan Secara Lokal

```bash
# Menggunakan Doppler (Rekomendasi Utama)
doppler run -- python 02-TELEGRAM_BOT/00-GMAIL_BOT/main.py

# Atau menggunakan venv lokal
python 02-TELEGRAM_BOT/00-GMAIL_BOT/main.py
```

---

## ☁️ Deployment ke Render.com (Solusi Santai 24/7)

### Opsi A: Render Web Service (Free Tier Compatible)
- **Environment**: `Python 3` atau `Docker`
- **Root Directory**: `.` (Root repository)
- **Dockerfile Path**: `./Dockerfile.telegram` (jika menggunakan runtime Docker)
- **Build Command**: `pip install -r requirements.txt` (jika native Python)
- **Start Command**: `python 02-TELEGRAM_BOT/00-GMAIL_BOT/main.py`
- **Health Check Path**: `/health`

### Opsi B: Render Background Worker (Starter Tier)
- **Start Command**: `python 02-TELEGRAM_BOT/00-GMAIL_BOT/main.py`

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
| `PORT` | Port HTTP Health Check (Render) | `10000` |
