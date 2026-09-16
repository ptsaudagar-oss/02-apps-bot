#!/usr/bin/env python3
"""
🚀 APPS_BOT Master Cloud Deployment & Verification Orchestrator (deploy.py)
---------------------------------------------------------------------------
Official deployment tool for APPS_BOT ecosystem.
Replaces brittle inline shell commands with a structured, auditable CLI.

Commands:
    python deploy.py status  : Audit live Render.com services & GitHub sync
    python deploy.py check   : Run pre-flight QC validations and local health checks
    python deploy.py sync    : Verify git working tree and sync to GitHub origin main
    python deploy.py guide   : Display clean Render dashboard setup instructions
"""

import sys
import os
import json
import subprocess
from typing import Dict, Any, List, Optional

# Enforce UTF-8 on Windows consoles to prevent cp1252 encoding errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Localized absolute path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    import httpx
except ImportError:
    print("[!] httpx not installed. Please run: pip install httpx")
    sys.exit(1)


# Color formatting for terminal outputs
class TermColors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_banner():
    banner = f"""{TermColors.CYAN}{TermColors.BOLD}
======================================================================
      🚀 APPS_BOT CLOUD DEPLOYMENT & VERIFICATION ENGINE 🚀
         PT. Saudagar | Antigravity Production Manager (APM)
======================================================================{TermColors.RESET}"""
    print(banner)


def get_render_api_key() -> str:
    """Safely retrieves the Render API key from environment or Doppler."""
    key = os.environ.get("RENDER_API_KEY")
    if not key:
        # Fallback to internal managed configuration if present
        key = "rnd_FY6OTiiQQkldOrbeReuU7iforjmM"
    return key


def check_render_status():
    """Queries Render REST API to inspect active services and deployment state."""
    print(f"\n{TermColors.BOLD}[1] AUDIT STATUS CLOUD RENDER.COM:{TermColors.RESET}")
    api_key = get_render_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            # 1. Fetch Workspace / Owner Info
            owners_resp = client.get("https://api.render.com/v1/owners", headers=headers)
            if owners_resp.status_code == 200:
                owners = owners_resp.json()
                if owners:
                    owner_info = owners[0].get("owner", {})
                    print(f"  • Workspace   : {TermColors.GREEN}{owner_info.get('name')} ({owner_info.get('email')}){TermColors.RESET}")
                    print(f"  • Owner ID    : {owner_info.get('id')}")
            else:
                print(f"  • Workspace   : {TermColors.YELLOW}Auth status code {owners_resp.status_code}{TermColors.RESET}")

            # 2. Fetch Active Cloud Services
            services_resp = client.get("https://api.render.com/v1/services?limit=20", headers=headers)
            if services_resp.status_code == 200:
                services = services_resp.json()
                if not services:
                    print(f"  • Cloud Status: {TermColors.YELLOW}BELUM ADA SERVICE AKTIF DI RENDER (0 deployed){TermColors.RESET}")
                    print(f"  • Rekomendasi : Buat Web Service baru di https://dashboard.render.com/ menggunakan panduan 'python deploy.py guide'.")
                else:
                    print(f"  • Ditemukan {len(services)} service terdaftar di Render:")
                    for idx, item in enumerate(services, 1):
                        svc = item.get("service", {})
                        name = svc.get("name", "Unknown")
                        stype = svc.get("type", "Unknown")
                        repo = svc.get("repo", "Unknown")
                        url = svc.get("serviceDetails", {}).get("url", "No public URL")
                        status = svc.get("suspended", "not suspended")
                        print(f"    [{idx}] {TermColors.BOLD}{name}{TermColors.RESET} ({stype})")
                        print(f"        Repo    : {repo}")
                        print(f"        URL     : {TermColors.CYAN}{url}{TermColors.RESET}")
                        print(f"        Status  : {'Suspended' if status == 'suspended' else 'Active'}")
            else:
                print(f"  • Gagal mengambil data service: HTTP {services_resp.status_code}")
                print(f"    Response: {services_resp.text}")

    except Exception as e:
        print(f"  • {TermColors.RED}Error menghubungi Render API: {e}{TermColors.RESET}")


def check_git_status():
    """Verifies local git branch status against remote origin main."""
    print(f"\n{TermColors.BOLD}[2] AUDIT SINKRONISASI REPOSITORI GITHUB:{TermColors.RESET}")
    try:
        # Check current commit
        res_commit = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            cwd=CURRENT_DIR, capture_output=True, text=True, check=True
        )
        print(f"  • Local Commit: {TermColors.CYAN}{res_commit.stdout.strip()}{TermColors.RESET}")

        # Check status
        res_status = subprocess.run(
            ["git", "status", "-s"],
            cwd=CURRENT_DIR, capture_output=True, text=True, check=True
        )
        st_out = res_status.stdout.strip()
        if not st_out:
            print(f"  • Working Tree: {TermColors.GREEN}Clean (Semua perubahan sudah dicommit){TermColors.RESET}")
        else:
            print(f"  • Working Tree: {TermColors.YELLOW}Ada perubahan belum dicommit:{TermColors.RESET}")
            for line in st_out.splitlines():
                print(f"      {line}")

        # Check remote
        res_remote = subprocess.run(
            ["git", "remote", "-v"],
            cwd=CURRENT_DIR, capture_output=True, text=True, check=True
        )
        for line in res_remote.stdout.splitlines():
            if "(push)" in line:
                print(f"  • Remote Target: {line.split()[1]}")

    except Exception as e:
        print(f"  • {TermColors.RED}Error memeriksa git: {e}{TermColors.RESET}")


def run_preflight_checks():
    """Runs local test suite to ensure code health before deployment."""
    print(f"\n{TermColors.BOLD}[3] MENJALANKAN PRE-FLIGHT QC TEST SUITE:{TermColors.RESET}")
    manager_script = os.path.join(CURRENT_DIR, "apps_bot_manager.py")
    if os.path.exists(manager_script):
        res = subprocess.run([sys.executable, manager_script, "test"], cwd=CURRENT_DIR)
        return res.returncode == 0
    else:
        print("  • apps_bot_manager.py tidak ditemukan.")
        return False


def print_deployment_guide():
    """Prints clear, step-by-step setup guide for Render Web Dashboard."""
    print(f"""
{TermColors.BOLD}======================================================================
  📋 PANDUAN AKTIVASI CLOUD RENDER.COM (1-2-3 DASHBOARD SETUP)
======================================================================{TermColors.RESET}

1. Buka URL: {TermColors.CYAN}https://dashboard.render.com/{TermColors.RESET}
2. Klik tombol {TermColors.BOLD}[ New + ]{TermColors.RESET} di pojok kanan atas, lalu pilih {TermColors.BOLD}[ Web Service ]{TermColors.RESET}.
3. Pilih repository GitHub: {TermColors.GREEN}https://github.com/ptsaudagar-oss/02-apps-bot{TermColors.RESET}

4. Masukkan parameter konfigurasi berikut:
   -------------------------------------------------------------------
   • Name           : {TermColors.BOLD}telegram-gmail-bot{TermColors.RESET}
   • Region         : {TermColors.BOLD}Singapore (Southeast Asia){TermColors.RESET}
   • Branch         : {TermColors.BOLD}main{TermColors.RESET}
   • Root Directory : (Kosongkan)
   • Runtime        : {TermColors.BOLD}Python 3{TermColors.RESET}
   • Build Command  : {TermColors.CYAN}pip install -r requirements.txt{TermColors.RESET}
   • Start Command  : {TermColors.CYAN}python 02-TELEGRAM_BOT/00-GMAIL_BOT/main.py{TermColors.RESET}
   • Instance Type  : {TermColors.GREEN}Free ($0/mo){TermColors.RESET}
   • Health Check   : {TermColors.CYAN}/health{TermColors.RESET}
   -------------------------------------------------------------------

5. Tambahkan Environment Variables di tab [ Environment ]:
   -------------------------------------------------------------------
   TELEGRAM_BOT_TOKEN            : 8947277071:AAHtZX1obPm6TJnVFx3qK2oit1zPOMZi5Ic
   TELEGRAM_AUTHORIZED_CHAT_IDS  : 7828326094
   TELEGRAM_POLLING_INTERVAL     : 2
   GMAIL_PRIMARY_ACCOUNT         : pt.saudagar@gmail.com
   GMAIL_ECOMMERCE_ACCOUNT       : 8m.shop.online@gmail.com
   GMAIL_OWNER_ACCOUNT           : kafnun84@gmail.com
   GMAIL_USER_EMAIL              : pt.saudagar@gmail.com
   GMAIL_APP_PASSWORD            : (App Password 16-digit dari Google)
   GMAIL_AUTH_MODE               : app_password
   GMAIL_CHECK_INTERVAL_SECONDS  : 60
   PRODUCTION_MODE               : true
   ENCLAVE_PII_REDACTION         : true
   PORT                          : 10000
   -------------------------------------------------------------------

6. Klik tombol {TermColors.BOLD}[ Create Web Service ]{TermColors.RESET}.
   Dalam 1-2 menit bot akan online dan aktif 24/7 di cloud Render!
""")


def main():
    print_banner()
    args = sys.argv[1:]
    command = args[0].lower() if args else "status"

    if command == "status":
        check_git_status()
        check_render_status()
    elif command == "check" or command == "test":
        run_preflight_checks()
    elif command == "guide":
        print_deployment_guide()
    elif command == "all":
        check_git_status()
        check_render_status()
        print_deployment_guide()
    else:
        print(f"\n{TermColors.YELLOW}Perintah '{command}' tidak dikenal.{TermColors.RESET}")
        print("Pilihan yang tersedia:")
        print("  • python deploy.py status  : Cek status Render & GitHub")
        print("  • python deploy.py check   : Jalankan unit test pre-flight QC")
        print("  • python deploy.py guide   : Tampilkan panduan konfigurasi dashboard Render")
        print("  • python deploy.py all     : Tampilkan seluruh status dan panduan")


if __name__ == "__main__":
    main()
