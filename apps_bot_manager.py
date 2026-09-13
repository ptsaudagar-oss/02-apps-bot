"""
APPS_BOT Orchestrator and Management CLI.
Central command interface to control, diagnose, test, and monitor all bot engines in the ecosystem.
"""

import os
import sys
import argparse
import asyncio
import subprocess
import unittest

# Ensure path localization
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from core.config import settings, ROOT_DIR
from core.logger import setup_logger, Colors

logger = setup_logger("APPS_BOT_MANAGER")


def print_banner():
    """Prints a high-contrast executive banner."""
    print(f"{Colors.BLUE}{Colors.BOLD}")
    print("=" * 70)
    print("      🚀 APPS_BOT - MULTI-SYSTEM BOT ECOSYSTEM MANAGER 🚀")
    print("          Telegram (Gmail Bot) & WhatsApp Bot Framework")
    print("=" * 70)
    print(f"{Colors.RESET}")


def cmd_status():
    """Performs deep environmental diagnosis and prints tabular health report."""
    print_banner()
    summary = settings.get_summary()

    print(f"{Colors.BOLD}[1] LINGKUNGAN & DIREKTORI WORKSPACE:{Colors.RESET}")
    print(f"  • Root Directory       : {Colors.CYAN}{summary['ROOT_DIR']}{Colors.RESET}")
    print(f"  • Logs Directory       : {Colors.CYAN}{summary['LOGS_DIR']}{Colors.RESET}")
    print(f"  • Debug Mode           : {Colors.GREEN if summary['DEBUG'] else Colors.YELLOW}{summary['DEBUG']}{Colors.RESET}")
    print()

    print(f"{Colors.BOLD}[2] STATUS KONFIGURASI MODUL & KREDENSIAL:{Colors.RESET}")

    # Telegram & Gmail
    tg_icon = f"{Colors.GREEN}[KONFIGURASI LENGKAP]{Colors.RESET}" if summary["TELEGRAM_CONFIGURED"] else f"{Colors.YELLOW}[MODE SIMULASI]{Colors.RESET}"
    gm_icon = f"{Colors.GREEN}[KONFIGURASI LENGKAP]{Colors.RESET}" if summary["GMAIL_CONFIGURED"] else f"{Colors.YELLOW}[MODE SIMULASI]{Colors.RESET}"
    wa_icon = f"{Colors.GREEN}[KONFIGURASI LENGKAP]{Colors.RESET}" if summary["WHATSAPP_CONFIGURED"] else f"{Colors.YELLOW}[MODE SIMULASI]{Colors.RESET}"
    ai_icon = f"{Colors.GREEN}[AKTIF (Gemini 3.6 Flash)]{Colors.RESET}" if summary["GEMINI_CONFIGURED"] else f"{Colors.YELLOW}[OFFLINE HEURISTIK]{Colors.RESET}"

    print(f"  • 00-TELEGRAM_BOT      : {tg_icon}")
    print(f"    - Telegram Token     : {'TERPASANG' if settings.TELEGRAM_BOT_TOKEN else 'Belum diisi (.env)'}")
    print(f"    - Whitelist Chat ID  : {settings.TELEGRAM_AUTHORIZED_CHAT_IDS or 'Semua Chat Diizinkan'}")
    print(f"  • 00-G-MAIL_BOT        : {gm_icon}")
    print(f"    - Akun Email         : {settings.GMAIL_USER_EMAIL or 'Belum diisi (.env)'}")
    print(f"    - Metode Auth        : {settings.GMAIL_AUTH_MODE.upper()} {'(Direkomendasikan: App Password)' if settings.GMAIL_AUTH_MODE == 'app_password' else ''}")
    print(f"  • 01-WHATSAPP_BOT      : {wa_icon}")
    print(f"    - Server Endpoint    : http://{settings.WHATSAPP_SERVER_HOST}:{settings.WHATSAPP_SERVER_PORT}")
    print(f"    - Webhook Verify     : {'TERPASANG' if settings.WHATSAPP_VERIFY_TOKEN else 'Kosong'}")
    print(f"    - Kebijakan Provider : Meta Cloud API (Utama) -> Local Gateway Failover ({'AKTIF' if settings.WHATSAPP_FAILOVER_TO_LOCAL else 'NONAKTIF'})")
    print(f"    - Local Bridge URL   : {settings.WHATSAPP_LOCAL_GATEWAY_URL}")
    print(f"  • KECERDASAN BUATAN    : {ai_icon}")
    print()

    print(f"{Colors.BOLD}[3] REKOMENDASI PENGGUNAAN:{Colors.RESET}")
    print(f"  1. Untuk menguji semua unit test:  {Colors.CYAN}python apps_bot_manager.py test{Colors.RESET}")
    print(f"  2. Untuk menjalankan Telegram Bot:  {Colors.CYAN}python apps_bot_manager.py run telegram{Colors.RESET}")
    print(f"  3. Untuk menjalankan WhatsApp Bot:  {Colors.CYAN}python apps_bot_manager.py run whatsapp{Colors.RESET}")
    print(f"  4. Untuk menjalankan Semua Bot:     {Colors.CYAN}python apps_bot_manager.py run all{Colors.RESET}")
    print("=" * 70 + "\n")


def cmd_test():
    """Runs all QC test suites across Core, Telegram Gmail Bot, and WhatsApp Bot."""
    print_banner()
    print(f"{Colors.BOLD}MENJALANKAN SELURUH SUITE PENGUJIAN QUALITY CONTROL (QC)...{Colors.RESET}\n")

    test_scripts = [
        ("Layer 1: Core Framework", os.path.join(ROOT_DIR, "core", "tests", "test_core.py")),
        ("Layer 2: Telegram Gmail Bot", os.path.join(ROOT_DIR, "00-TELEGRAM_BOT", "00-G-MAIL_BOT", "tests", "test_gmail_bot.py")),
        ("Layer 3: WhatsApp Bot", os.path.join(ROOT_DIR, "01-WHATSAPP_BOT", "tests", "test_whatsapp_bot.py")),
    ]

    all_passed = True
    for label, script_path in test_scripts:
        print(f"{Colors.CYAN}▶ Pengujian: {label}{Colors.RESET}")
        print(f"  Script: {script_path}")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode == 0:
            print(f"  {Colors.GREEN}✓ PASSED (Code 0){Colors.RESET}\n")
        else:
            print(f"  {Colors.RED}✗ FAILED (Code {result.returncode}){Colors.RESET}")
            print(f"  Output:\n{result.stderr}\n{result.stdout}\n")
            all_passed = False

    print("=" * 70)
    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 SELURUH MODUL DINYATAKAN LOLOS UJI QUALITY CONTROL (QC 100% OK){Colors.RESET}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}⚠️ TERDAPAT PENGUJIAN GAGAL. HARAP PERIKSA LOG INVESTIGASI.{Colors.RESET}")
    print("=" * 70 + "\n")
    return all_passed


def cmd_run(target: str):
    """Launches target bot engine(s)."""
    target = target.lower()
    print_banner()

    if target == "telegram":
        print(f"{Colors.GREEN}▶ Memulai Telegram Gmail Bot Engine...{Colors.RESET}")
        script_path = os.path.join(ROOT_DIR, "00-TELEGRAM_BOT", "00-G-MAIL_BOT", "main.py")
        subprocess.run([sys.executable, script_path])

    elif target == "whatsapp":
        print(f"{Colors.GREEN}▶ Memulai WhatsApp Bot Webhook Server...{Colors.RESET}")
        script_path = os.path.join(ROOT_DIR, "01-WHATSAPP_BOT", "main.py")
        subprocess.run([sys.executable, script_path])

    elif target == "all":
        print(f"{Colors.GREEN}▶ Memulai Seluruh Bot (Telegram + WhatsApp) secara Paralel...{Colors.RESET}")
        p1 = subprocess.Popen([sys.executable, os.path.join(ROOT_DIR, "00-TELEGRAM_BOT", "00-G-MAIL_BOT", "main.py")])
        p2 = subprocess.Popen([sys.executable, os.path.join(ROOT_DIR, "01-WHATSAPP_BOT", "main.py")])
        try:
            p1.wait()
            p2.wait()
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Menghentikan seluruh proses bot...{Colors.RESET}")
            p1.terminate()
            p2.terminate()
            p1.wait()
            p2.wait()
            print(f"{Colors.GREEN}Seluruh bot berhasil dihentikan.{Colors.RESET}")

    else:
        print(f"{Colors.RED}Target '{target}' tidak valid. Pilihan: telegram | whatsapp | all{Colors.RESET}")


def main():
    parser = argparse.ArgumentParser(description="APPS_BOT Orchestrator & CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Status
    subparsers.add_parser("status", help="Tampilkan diagnosis status dan konfigurasi bot")

    # Test
    subparsers.add_parser("test", help="Jalankan semua unit dan integration tests")

    # Run
    run_parser = subparsers.add_parser("run", help="Jalankan bot tertentu")
    run_parser.add_argument("target", choices=["telegram", "whatsapp", "all"], help="Bot target")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "test":
        success = cmd_test()
        sys.exit(0 if success else 1)
    elif args.command == "run":
        cmd_run(args.target)
    else:
        cmd_status()


if __name__ == "__main__":
    main()
