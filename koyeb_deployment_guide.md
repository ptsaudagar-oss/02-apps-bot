# 🚀 PANDUAN DEPLOYMENT KOYEB (24/7 CLOUD HOSTING NONSTOP)

Dokumentasi resmi untuk mendeploy ekosistem bot **APPS_BOT** ke **Koyeb (koyeb.com)** di Region Singapore (`sin`) secara gratis tanpa memerlukan kartu kredit.

---

## 🌟 Kenapa Memilih Koyeb?
1. **Bebas Paywall Kartu Kredit**: Akun Hobby gratis tanpa kewajiban memasukkan kartu kredit/Stripe.
2. **Region Singapore (`sin`)**: Latensi ultra-rendah (~18ms) langsung ke Indonesia.
3. **Long-Running Process & WebSockets**: Mendukung bot Telegram polling dan socket WhatsApp tanpa terputus secara sepihak.
4. **Native Dockerfile Support**: Otomatis mendeteksi `Dockerfile.telegram` atau `koyeb.yaml`.

---

## 📋 3 Langkah Mudah Aktivasi di Dashboard Koyeb

### Langkah 1: Hubungkan Repositori GitHub
1. Buka [app.koyeb.com](https://app.koyeb.com/) dan login/daftar (bisa langsung pakai akun GitHub).
2. Klik tombol **Create Service** (atau **Create App**).
3. Pilih sumber deployment: **GitHub**.
4. Pilih repositori: `ptsaudagar-oss/02-apps-bot` (Branch: `main`).

---

### Langkah 2: Konfigurasi Builder, Region & Port
Pada formulir konfigurasi layanan:
- **Service Name**: `telegram-gmail-bot`
- **Region**: Pilih **Singapore (`sin`)**
- **Instance Type**: Pilih **Nano** (Gratis / Free Tier)
- **Builder**: Pilih **Dockerfile**
  - **Dockerfile location**: `Dockerfile.telegram`
- **Exposed Port**:
  - **Port**: `8000`
  - **Protocol**: `HTTP`
  - **Path**: `/`
- **Health Check**:
  - **Protocol**: `HTTP`
  - **Path**: `/health`
  - **Port**: `8000`

---

### Langkah 3: Masukkan Environment Variables (Dari Doppler)
Buka tab **Environment variables** di halaman yang sama, lalu tambahkan kunci-kunci berikut yang sudah tersimpan di Doppler:

| Variable | Value (Sesuai Doppler) |
| :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | `8947277071:AAHtZX1obPm6TJnVFx3qK2oit1zPOMZi5Ic` |
| `TELEGRAM_AUTHORIZED_CHAT_IDS` | `7828326094` |
| `TELEGRAM_POLLING_INTERVAL` | `2` |
| `GMAIL_PRIMARY_ACCOUNT` | `pt.saudagar@gmail.com` |
| `GMAIL_ECOMMERCE_ACCOUNT` | `8m.shop.online@gmail.com` |
| `GMAIL_OWNER_ACCOUNT` | `kafnun84@gmail.com` |
| `GMAIL_USER_EMAIL` | `pt.saudagar@gmail.com` |
| `GMAIL_APP_PASSWORD` | *(16 karakter App Password dari Google)* |
| `GMAIL_AUTH_MODE` | `app_password` |
| `GMAIL_CHECK_INTERVAL_SECONDS` | `60` |
| `PRODUCTION_MODE` | `true` |
| `ENCLAVE_PII_REDACTION` | `true` |
| `PORT` | `8000` |

Klik **Deploy**. Dalam ~1-2 menit, layanan Telegram Gmail Bot Anda akan langsung **LIVE & ACTIVE 24/7** dengan URL publik Koyeb (contoh: `https://<app>-<org>.koyeb.app`).

---

## 📱 Roadmap Deploy Bertahap WhatsApp Bot (`01-WHATSAPP_BOT`)
- **Tahap 1 (Saat ini)**: WhatsApp Bot tetap menggunakan Local Gateway di port 3000 pada laptop untuk stabilitas sesi Baileys.
- **Tahap 2 (Cloud WhatsApp)**: Jika ingin memindahkan WhatsApp ke Koyeb juga, cukup masukkan `WHATSAPP_ACCESS_TOKEN` dan `WHATSAPP_PHONE_NUMBER_ID` dari Meta Cloud Developer API. Modul `01-WHATSAPP_BOT` otomatis memproses webhook Meta langsung di cloud Koyeb tanpa perlu scan QR lagi!
