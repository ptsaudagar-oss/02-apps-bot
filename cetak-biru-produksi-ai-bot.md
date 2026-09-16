# 🚀 Cetak Biru Produksi AI Bot: Dari Nol Sampai Jadi (Production Ready)

Document Version: 1.0.0  
Architecture Framework: APPS_BOT Multi-Channel Autonomous AI System  
Target Persona: Software & Ecosystem Production Manager  

---

## 🏛️ 1. Analogi Utama: Arsitektur Sistem Sebagai "Restoran Modern Berbintang"

Sistem bot AI otonom multisaluran ini bekerja layaknya sebuah **Restoran Modern Berbintang** yang melayani pesanan 24 jam nonstop tanpa pernah tutup:

* **Pelanggan (WhatsApp & Telegram)**: Konsumen yang memesan layanan dari pintu publik (WhatsApp) atau meja VIP (Telegram).
* **Kasir & Penerima Pesanan (n8n Middleware / FastAPI Webhook)**: Petugas depan yang memeriksa identitas (*handshake* & HMAC-SHA256), memberikan nota terima kasih instan (HTTP 200 OK < 150 ms), dan meneruskan tiket ke dapur.
* **Head Chef / Koki Utama (Hermes Agent & AI Engine)**: Otak dapur otonom yang mengingat profil pelanggan (*Long-Term Store* `MEMORY.md`), instruksi saat ini (*Short-Term Window*), serta meracik resep kerja baru secara otomatis (*Procedural Skill Memory* `SKILL.md`).
* **Pemasok Bahan & Penawar Harga (9Router AI Gateway)**: Manajer logistik yang menyediakan model AI, menghemat konsumsi token (RTK Token Saver 20%–40%), serta mengatur alur 3 pemasok cadangan (*3-Tier Fallback*) agar dapur tidak kehabisan bahan.
* **Kurir Pengantar Pesanan (Dual Dispatcher & Failover)**: Sistem pengiriman yang mencoba kurir resmi (Meta Cloud API) terlebih dahulu; jika kurir utama halangan/mogok, otomatis dialihkan ke kurir cadangan (*Local Gateway Bridge*) tanpa membuat restoran *crash*.
* **Gedung & Fasilitas Dapur (Koyeb Cloud Infrastructure)**: Bangunan fisik terisolasi di Singapore (`sin`) bersertifikat SSL dengan proses aktif 24/7 tanpa paywall kartu kredit.
* **Inspektur Mutu / Manager (Master CLI `apps_bot_manager.py`)**: Alat kendali pusat untuk memeriksa kesehatan dapur dan menjalankan pengujian otomatis (*Antigravity QC Protocol*) hingga 100% Lolos.

---

## 🗺️ 2. Panduan Cetak Biru: 5 Fase Dari Nol Sampai Jadi

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   CETAK BIRU DARI NOL SAMPAI JADI                      │
│                                                                        │
│  [FASE 1] Perencanaan & Arsitektur 4 Layer                             │
│     └── Layer 1: Core ➔ Layer 2: Telegram ➔ Layer 3: WA ➔ Layer 4: CLI │
│                                                                        │
│  [FASE 2] Persiapan Perangkat & Gateway Lokal                          │
│     └── Node.js, Python, 9Router Proxy (Port 20128)                    │
│                                                                        │
│  [FASE 3] Testing QC & Mode Simulasi (Sandbox)                         │
│     └── python apps_bot_manager.py test (100% PASSED)                  │
│                                                                        │
│  [FASE 4] Integrasi Kredensial Asli                                    │
│     └── App Password Gmail, Token BotFather, Meta WABA Token           │
│                                                                        │
│  [FASE 5] Deployment Cloud & Pemeliharaan (24/7)                       │
│     └── koyeb.yaml / Dockerfile di Koyeb Cloud (Singapore)             │
└────────────────────────────────────────────────────────────────────────┘
```

### 📌 FASE 1: Perencanaan & Arsitektur Modular (4 Layer Framework)
Sebagai Production Manager, bagi sistem ke dalam **4 Layer Terisolasi**:
1. **Layer 1: Shared Core Engine (`core/`)**  
   Menyimpan konfigurasi jalur relatif (`config.py`), pencatat riwayat *logger* UTF-8 (`logger.py`), dan mesin AI utama (Gemini 3.6 Flash di `ai_helper.py`).
2. **Layer 2: Telegram & Gmail Bot (`00-TELEGRAM_BOT/00-G-MAIL_BOT/`)**  
   Memantau email masuk via IMAP/SMTP SSL Google App Password setiap 60 detik (*Push Watcher*), merangkum isi email, dan mengirim kartu tombol interaktif ke Telegram.
3. **Layer 3: WhatsApp Bot Server (`01-WHATSAPP_BOT/`)**  
   FastAPI Webhook server yang mengelola *Session Manager* (15 interaksi terakhir), REST API `/api/send`, serta kebijakan *Dual Dispatcher* ("Meta Cloud API dahulu ➔ Failover ke Local Gateway").
4. **Layer 4: Master CLI Orchestrator (`apps_bot_manager.py`)**  
   Pusat kendali tunggal untuk memeriksa status, menjalankan unit test, dan mengeksekusi seluruh bot secara bersamaan (*multi-process concurrency*).

### 📌 FASE 2: Persiapan Perangkat & Gateway Lokal (Di Laptop)
Siapkan perkakas di laptop Anda sebelum menghubungkan layanan internet:
1. **Instal Runtime Pemrograman**: Pastikan laptop memiliki **Node.js (v20+)** dan **Python (v3.10+)**.
2. **Jalankan 9Router (Local AI Gateway)**:
   * Pasang 9Router secara global via terminal: `npm install -g 9router` lalu jalankan `9router`.
   * Buka dashboard di `http://localhost:20128`. Daftarkan akun AI (seperti OpenAI, Claude, atau penyedia gratisan). 9Router menyediakan satu endpoint terpadu OpenAI-compatible `/v1` di port 20128 dengan kompresi token RTK.
3. **Buka Workspace Proyek**: Masuk ke direktori utama di terminal PowerShell:
   ```powershell
   cd "C:\Users\kafnu\Downloads\00-ANTIGRAVITY AI\00-APPS\02-APPS_BOT"
   ```

### 📌 FASE 3: Pengujian QC & Mode Simulasi (Sandbox Safe)
Sebelum mempublikasikan aplikasi, uji integritas kode secara otomatis tanpa risiko salah kirim:
1. **Duplikasi Konfigurasi Lingkungan**: Salin `.env.example` menjadi `.env`: `cp .env.example .env`
2. **Pemeriksaan Status Diagnostik**: Jalankan `python apps_bot_manager.py status`. Pastikan seluruh modul terdeteksi dalam `[MODE SIMULASI]`.
3. **Eksekusi Antigravity QC Protocol (Suite 17–18 Unit Tests)**: Jalankan pengujian mutu menyeluruh:
   ```powershell
   python apps_bot_manager.py test
   ```
   *Indikator Sukses*: Seluruh layer menyatakan **`✓ PASSED (Code 0)`**.
4. **Jalankan Seluruh Bot Lokal**: Jalankan `python apps_bot_manager.py run all`. Sistem akan mengaktifkan *long-polling* Telegram dan server Uvicorn WhatsApp di `http://127.0.0.1:8080` secara paralel.

### 📌 FASE 4: Menghubungkan Kredensial Asli (Live Integration)
Setelah mode simulasi 100% lolos uji, ganti kredensial simulasi di file `.env` dengan kredensial asli:
1. **Telegram Bot**: Buat bot baru via **@BotFather** untuk mendapatkan *Telegram Bot Token*, lalu ambil ID Anda via **@userinfobot**.
2. **Gmail Bot (Google App Password)**: Buat *App Password* 16 karakter di `myaccount.google.com/apppasswords` untuk koneksi IMAP/SMTP SSL yang aman dan bebas kadaluarsa.
3. **WhatsApp Cloud API**: Ambil *Phone Number ID*, *WABA ID*, dan *System User Token* dari Meta for Developers Console.

### 📌 FASE 5: Cloud Deployment & Pemeliharaan Production (24/7 di Koyeb Platform)
Agar bot beroperasi 24 jam nonstop tanpa mengandalkan laptop, lakukan *deployment* ke Koyeb Cloud (Region Singapore) secara gratis tanpa kartu kredit:
1. **Manifest Blueprint (`koyeb.yaml`)**: Konfigurasikan layanan di `koyeb.yaml` atau Dockerfile:
   * **Telegram Gmail Bot Web Service**: Meng-host webhook publik HTTPS dan long-polling bot dengan HTTP Health Check di port 8000 (`/health`).
   * **Hermes & Ingestion Worker**: Meng-host penalaran AI otonom di latar belakang.
   * **9Router AI Gateway**: Proxy AI privat dengan RTK token compression.
2. **Push ke GitHub & Deploy**: Hubungkan repositori GitHub Anda ke Koyeb App untuk otomatisasi *build* & *deploy* bebas repot.
3. **Pemeliharaan Harian**:
   * **Rotasi Log**: File `logs/apps_bot.log` otomatis berotasi saat mencapai 10MB sehingga ruang penyimpanan tidak pernah penuh.
   * **Skill Extension**: Jika ada alur bisnis baru, buat file `SKILL.md` baru untuk Hermes Agent tanpa mengubah fondasi kode.

---

## 🧠 3. Skema Pengolahan Pesan Gmail Dinamis oleh AI Agentic

AI Agentic (Hermes Agent / Gemini 3.6 Flash) mengolah pesan masuk menjadi **JSON Schema Dinamis** yang langsung diterjemahkan n8n ke tombol WhatsApp/Telegram:

```json
{
  "email_metadata": {
    "sender": "pengirim@domain.com",
    "received_at": "2026-09-13T12:00:00Z",
    "subject": "Undangan Rapat Anggaran Q3"
  },
  "classification": {
    "category": "INVITATION_APPROVAL",
    "priority": "HIGH",
    "summary_keypoints": "Permintaan rapat peninjauan anggaran Q3 pada Senin jam 10:00 WIB."
  },
  "action_payload": {
    "type": "INTERACTIVE_BUTTONS",
    "options": [
      {"label": "✅ Setujui & Calendar", "action_id": "approve_and_add_cal"},
      {"label": "❌ Tolak", "action_id": "decline_request"}
    ]
  }
}
```

---

## 📊 4. Breakdown Tabular: 5 Fase "Nol Sampai Jadi"

| Fase Production | Kegiatan Utama | Tools / Perintah Utama | Indikator Keberhasilan (*Output*) | Analogi Restoran |
| :--- | :--- | :--- | :--- | :--- |
| **Fase 1: Planning** | Merancang arsitektur 4 Layer terisolasi | VS Code / Antigravity IDE | Struktur folder & modul terikat rapi | Merancang denah dapur & buku resep utama |
| **Fase 2: Local Setup** | Pasang runtime & AI Gateway lokal | Node 20+, Python 3.10+, 9router | Gateway aktif di `localhost:20128` | Menata mesin bubut & meja kerja di dapur |
| **Fase 3: QC & Testing** | Uji otomatis suite 17 unit tests | `python apps_bot_manager.py test` | **100% PASSED (Code 0)** | Penguji QC mencicipi & meloloskan seluruh resep |
| **Fase 4: Live Credentials** | Isi token asli Telegram, Gmail, & WA | BotFather, App Password, Meta Console | File `.env` terisi token produksi aman | Membuka pintu gerbang untuk pelanggan asli |
| **Fase 5: Production Deploy** | Deploy cloud 24/7 di jaringan privat | Koyeb Cloud & `koyeb.yaml` | Bot beroperasi 24/7 tanpa *downtime* | Restoran cabang cloud resmi buka 24 jam |

---

## 💡 5. Resume & Kesimpulan Operasional

1. **Jalan Pintas Bebas Bingung**: Sebagai Production Manager, pegang teguh **4 Layer Framework** dan jalankan pengujian otomatis via `apps_bot_manager.py`.
2. **Jaminan Keandalan 100%**: Kebijakan *Dual Dispatcher* WhatsApp ("Meta dahulu ➔ Failover ke Local Gateway") dan *3-Tier Fallback* 9Router menjamin bot Anda melayani pengguna tanpa pernah *crash*.
3. **Pemberdayaan AI Agentic**: Fleksibilitas email acak/kompleks ditangani penuh oleh penalaran AI (Hermes / Gemini) yang mengembalikan JSON Schema terstruktur untuk mengeksekusi tombol *Confirm*, *Calendar*, atau *Resume* secara otomatis.
