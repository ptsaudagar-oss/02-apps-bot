# PANDUAN DEPLOYMENT FLY.IO (REGION SINGAPORE - 24/7 ONLINE NON-STOP)

Dokumen ini adalah blueprint resmi deployment **Telegram Gmail Bot** (`02-TELEGRAM_BOT/00-GMAIL_BOT`) ke **Fly.io** pada region **Singapore (`sin`)** dengan konfigurasi **Full Always-On 24/7 (Zero Sleep / No Idle Shutdown)**.

---

## 1. Spesifikasi Infrastruktur Fly.io

| Parameter | Nilai Konfigurasi | Keterangan |
| :--- | :--- | :--- |
| **App Name** | `ptsaudagar-apps-bot` | Identifier unik di Fly.io |
| **Primary Region** | `sin` | Singapore (Latency terendah ke Indonesia) |
| **VM Sizing** | `shared-cpu-1x`, 256MB RAM | Standar micro container optimal |
| **Auto Stop Machines** | `false` | **Mencegah server tertidur (Zero Sleep)** |
| **Auto Start Machines** | `true` | Auto recovery jika terjadi restart |
| **Min Machines Running** | `1` | Minimal 1 VM aktif terus-menerus 24/7 |
| **Internal Port** | `8080` | Port HTTP internal untuk health check `/health` |
| **Protocol** | HTTP / HTTPS (TLS Termination) | Endpoint publik otomatis |

---

## 2. File Konfigurasi Terkait

- **`fly.toml`**: Berkas deklaratif arsitektur mesin Fly.io di root direktori `02-APPS_BOT`.
- **`Dockerfile.telegram`**: Resep container Python 3.11-slim terisolasi dan efisien.
- **`02-TELEGRAM_BOT/00-GMAIL_BOT/main.py`**: Mendukung auto-deteksi runtime Fly.io (`FLY_APP_NAME`) dan menjalankan micro HTTP server di port 8080 untuk memenuhi health check Fly.io.

---

## 3. Langkah Aktivasi Deployment (Pilih Salah Satu)

### Opsi A: Menggunakan Flyctl CLI (Rekomendasi dari Terminal Windows)

1. **Install flyctl di PowerShell**:
   ```powershell
   iwr https://fly.io/install.ps1 -useb | iex
   ```
2. **Login ke Fly.io**:
   ```powershell
   fly auth login
   ```
3. **Luncurkan / Daftarkan Aplikasi (Pertama kali)**:
   ```powershell
   fly launch --no-deploy --copy-config
   ```
4. **Set Environment Secrets dari Doppler**:
   Masukkan secrets yang dibutuhkan bot ke Fly.io:
   ```powershell
   fly secrets set TELEGRAM_BOT_TOKEN="<token>" TELEGRAM_AUTHORIZED_CHAT_IDS="<chat_id>" GMAIL_USER_EMAIL="<email>" GMAIL_APP_PASSWORD="<app_pass>"
   ```
5. **Deploy Container**:
   ```powershell
   fly deploy --dockerfile Dockerfile.telegram
   ```

---

### Opsi B: Menggunakan GitHub Actions (Otomatis Saat Git Push)

Jika repo `ptsaudagar-oss/02-apps-bot` dihubungkan ke GitHub Actions:
1. Buat token di Fly.io Dashboard: **Account Settings -> Access Tokens -> Create Token**.
2. Simpan token tersebut di GitHub Repo Secrets dengan nama `FLY_API_TOKEN`.
3. Gunakan action `superfly/flyctl-actions/setup-flyctl@master` untuk auto-deploy setiap kali branch `main` diperbarui.

---

## 4. Verifikasi Health Check & Status 24/7

Setelah deploy berhasil, status mesin dapat dipantau melalui:
- **CLI**: `fly status` atau `fly logs`
- **Browser**: Buka `https://ptsaudagar-apps-bot.fly.dev/health`
- Respon yang diharapkan:
  ```json
  {"status": "healthy", "service": "Telegram Gmail Bot", "timestamp": "..."}
  ```

Dengan setting `auto_stop_machines = false`, aplikasi Anda dijamin akan tetap hidup 24 jam sehari, 7 hari seminggu tanpa jeda sleep.
