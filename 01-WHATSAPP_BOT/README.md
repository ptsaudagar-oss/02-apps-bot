# WHATSAPP BOT & GATEWAY (01-WHATSAPP_BOT)

Modul ini bertanggung jawab atas integrasi komunikasi WhatsApp dua arah, mencakup:
1. **Local Gateway Bridge (Node.js + Baileys)**: Engine soket WhatsApp Web untuk nomor terverifikasi (`081808630730`).
2. **Cloud/Meta WhatsApp Business API Integration**: Failover otomatis antara cloud Meta API dan local gateway.
3. **Hybrid Authentication Backend (Firebase Firestore + Local Fallback)**.

---

## Arsitektur Autentikasi: Firebase Firestore Auth State

Untuk mendukung deployment di lingkungan stateless (cloud container tanpa persistent disk berbayar) dan memastikan sesi login tidak hilang saat server restart:

### 1. Mekanisme Kerja
- **Primary Backend (Firestore)**:
  - Koleksi: `wa_sessions`
  - Dokumen Kredensial: `session_081808630730`
  - Subkoleksi Kunci: `keys` (menyimpan cryptographic signal keys, pre-keys, dan identity keys).
- **Secondary Fallback (Local Multi-File)**:
  - Jika koneksi atau izin Firestore belum tersedia, sistem secara otomatis beralih ke direktori lokal `baileys_auth_info/` tanpa menghentikan service bot.

### 2. Konfigurasi Environment Variables (Doppler `apps-bot`)
| Variable | Deskripsi | Default / Nilai |
| :--- | :--- | :--- |
| `FIREBASE_PROJECT_ID` | Google Cloud / Firebase Project ID | `laporan-investigasi-mwp-2026` |
| `FIREBASE_SERVICE_ACCOUNT_BASE64` | JSON Service account dalam format string / base64 | Diinjeksi aman via Doppler |
| `WA_USE_FIRESTORE` | Flag aktivasi Firestore (`true`/`false`) | `true` |
| `WA_SESSION_ID` | Identifier unik dokumen sesi WhatsApp | `session_081808630730` |

---

## Menjalankan Gateway

```powershell
# Melalui Doppler Wrapper
cd 01-WHATSAPP_BOT/local_wa_bridge
doppler run -- node server.js
```

Endpoint yang tersedia:
- `GET http://127.0.0.1:3000/status`: Memeriksa status koneksi dan backend auth yang aktif.
- `GET http://127.0.0.1:3000/qr`: Menampilkan visual QR Code jika sesi baru dibutuhkan.
- `POST http://127.0.0.1:3000/api/send`: Mengirim pesan WhatsApp teks.
