"""
LocalForge Setup
Bağımlılıkları kurar ve ilk yapılandırmayı oluşturur.
"""

import subprocess
import sys
import json
import os
from pathlib import Path

BANNER = """
╔══════════════════════════════════════════╗
║         🔨 LocalForge Kurulum            ║
║   Yerel LLM ile Otomatik Proje Geliştir  ║
╚══════════════════════════════════════════╝
"""

DEFAULT_CONFIG = {
    "planner_model": "",
    "coder_model": "",
    "backend": "ollama",
    "ollama_url": "http://localhost:11434",
    "lmstudio_url": "http://localhost:1234",
    "approval_mode": False,
    "last_project": ""
}


def print_step(msg: str):
    print(f"\n  ▶  {msg}")


def print_ok(msg: str):
    print(f"  ✅  {msg}")


def print_err(msg: str):
    print(f"  ❌  {msg}")


def install_requirements():
    print_step("Python bağımlılıkları kuruluyor...")
    req_path = Path(__file__).parent / "requirements.txt"
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_path), "--quiet"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print_ok("Bağımlılıklar kuruldu.")
    else:
        print_err("Bağımlılık kurulumu başarısız:")
        print(result.stderr)
        sys.exit(1)


def create_config():
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        print_ok("config.json zaten mevcut, atlanıyor.")
        return
    print_step("config.json oluşturuluyor...")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
    print_ok("config.json oluşturuldu.")


def create_directories():
    print_step("Klasör yapısı oluşturuluyor...")
    dirs = [
        "core",
        "agents",
        "prompts",
        "templates/fastapi",
        "templates/react",
        "templates/nextjs",
        "templates/cli",
        "ui/pages",
        "ui/components",
    ]
    base = Path(__file__).parent
    for d in dirs:
        (base / d).mkdir(parents=True, exist_ok=True)
        (base / d / "__init__.py").touch(exist_ok=True)
    print_ok("Klasörler oluşturuldu.")


def check_ollama():
    print_step("Ollama kontrol ediliyor...")
    result = subprocess.run(
        ["ollama", "--version"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print_ok(f"Ollama bulundu: {result.stdout.strip()}")
    else:
        print("  ⚠️  Ollama bulunamadı. LM Studio kullanabilir veya Ollama kurabilirsiniz.")
        print("      https://ollama.ai")


def check_lmstudio():
    print_step("LM Studio kontrol ediliyor...")
    import requests
    try:
        resp = requests.get("http://localhost:1234/v1/models", timeout=2)
        if resp.status_code == 200:
            print_ok("LM Studio çalışıyor.")
        else:
            print("  ⚠️  LM Studio yanıt vermiyor.")
    except Exception:
        print("  ⚠️  LM Studio bulunamadı (port 1234 kapalı).")


def main():
    print(BANNER)
    create_directories()
    install_requirements()
    create_config()
    check_ollama()
    check_lmstudio()

    print("\n" + "═" * 46)
    print("  🎉  Kurulum tamamlandı!")
    print("  Başlatmak için: streamlit run app.py")
    print("═" * 46 + "\n")


if __name__ == "__main__":
    main()
