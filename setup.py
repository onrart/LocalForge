"""
LocalForge — Kurulum
Bağımlılıkları kurar, klasör yapısını oluşturur, sistem kontrolü yapar.

Kullanım:
    python setup.py
"""

import subprocess
import sys
import json
import platform
from pathlib import Path

BANNER = """
╔══════════════════════════════════════════════╗
║           🔨 LocalForge Kurulum              ║
║    Yerel LLM ile Otomatik Proje Geliştir     ║
╚══════════════════════════════════════════════╝
"""

DEFAULT_CONFIG = {
    "planner_model": "",
    "coder_model": "",
    "backend": "ollama",
    "ollama_url": "http://localhost:11434",
    "lmstudio_url": "http://localhost:1234",
    "approval_mode": False,
    "last_project": "",
}

NO_INIT_DIRS = {
    "prompts",
    "templates",
    "templates/fastapi",
    "templates/fastapi/src",
    "templates/react",
    "templates/react/src",
    "templates/nextjs",
    "templates/nextjs/app",
    "templates/cli",
    "templates/cli/src",
    "ui/components",
}


def print_step(msg):
    print(f"\n  ▶  {msg}")


def print_ok(msg):
    print(f"  ✅  {msg}")


def print_warn(msg):
    print(f"  ⚠️   {msg}")


def print_err(msg):
    print(f"  ❌  {msg}")


def check_python_version():
    print_step("Python versiyonu kontrol ediliyor...")
    major, minor = sys.version_info.major, sys.version_info.minor
    ver = f"{major}.{minor}.{sys.version_info.micro}"
    if major < 3 or (major == 3 and minor < 10):
        print_err(f"Python {ver} desteklenmiyor. Python 3.10+ gerekli.")
        sys.exit(1)
    print_ok(f"Python {ver} — uyumlu.")


def install_requirements():
    print_step("Python bağımlılıkları kuruluyor...")
    req_path = Path(__file__).parent / "requirements.txt"
    if not req_path.exists():
        print_err("requirements.txt bulunamadı.")
        sys.exit(1)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_path), "--quiet"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print_ok("Bağımlılıklar kuruldu.")
    else:
        print_err(f"Kurulum başarısız: {result.stderr.strip()}")
        sys.exit(1)


def create_directories():
    print_step("Klasör yapısı oluşturuluyor...")
    dirs = [
        "core",
        "agents",
        "prompts",
        "templates",
        "templates/fastapi",
        "templates/fastapi/src",
        "templates/react",
        "templates/react/src",
        "templates/nextjs",
        "templates/nextjs/app",
        "templates/cli",
        "templates/cli/src",
        "ui",
        "ui/pages",
        "ui/components",
    ]
    base = Path(__file__).parent
    for d in dirs:
        path = base / d
        path.mkdir(parents=True, exist_ok=True)
        if d not in NO_INIT_DIRS:
            init = path / "__init__.py"
            if not init.exists():
                init.touch()
    print_ok("Klasörler oluşturuldu.")


def create_config():
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
            updated = False
            for k, v in DEFAULT_CONFIG.items():
                if k not in existing:
                    existing[k] = v
                    updated = True
            if updated:
                config_path.write_text(
                    json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                print_ok("config.json güncellendi.")
            else:
                print_ok("config.json zaten güncel.")
        except Exception:
            config_path.write_text(
                json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print_ok("config.json yeniden oluşturuldu.")
    else:
        print_step("config.json oluşturuluyor...")
        config_path.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print_ok("config.json oluşturuldu.")


def check_python_packages():
    print_step("Kritik paketler kontrol ediliyor...")
    missing = []
    for pkg in ["streamlit", "psutil", "requests", "rich"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print_err(f"Eksik paketler: {', '.join(missing)}")
        return False
    print_ok("Tüm kritik paketler mevcut.")
    return True


def check_ollama():
    print_step("Ollama kontrol ediliyor...")
    try:
        r = subprocess.run(
            ["ollama", "--version"], capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            print_ok(f"Ollama bulundu: {r.stdout.strip()}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        import requests

        r = requests.get("http://localhost:11434/api/version", timeout=3)
        if r.status_code == 200:
            print_ok(f"Ollama API çalışıyor: v{r.json().get('version','?')}")
            return True
    except Exception:
        pass
    print_warn("Ollama bulunamadı → https://ollama.ai")
    return False


def check_lmstudio():
    print_step("LM Studio kontrol ediliyor...")
    try:
        import requests

        r = requests.get("http://localhost:1234/v1/models", timeout=3)
        if r.status_code == 200:
            print_ok(f"LM Studio çalışıyor ({len(r.json().get('data',[]))} model).")
            return True
    except Exception:
        pass
    print_warn("LM Studio bulunamadı → https://lmstudio.ai")
    return False


def print_system_info():
    print_step("Sistem bilgisi...")
    print(f"       OS     : {platform.system()} {platform.release()}")
    print(f"       Python : {platform.python_version()}")
    print(f"       Mimari : {platform.machine()}")


def main():
    print(BANNER)
    print_system_info()
    check_python_version()
    create_directories()
    install_requirements()
    check_python_packages()
    create_config()

    print("\n  " + "─" * 44)
    ollama_ok = check_ollama()
    lmstudio_ok = check_lmstudio()

    print("\n" + "═" * 46)
    if ollama_ok or lmstudio_ok:
        print("  🎉  Kurulum tamamlandı!")
        print("\n      streamlit run app.py")
    else:
        print("  ⚠️   Kurulum tamamlandı ama LLM backend bulunamadı.")
        print("  Ollama → https://ollama.ai")
        print("  LM Studio → https://lmstudio.ai")
        print("\n  Backend kurulunca: streamlit run app.py")
    print("═" * 46 + "\n")


if __name__ == "__main__":
    main()
