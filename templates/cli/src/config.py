"""
CLI uygulama yapılandırması.
"""

from pathlib import Path

APP_NAME = "{project_name}"
APP_DIR = Path.home() / f".{APP_NAME.lower().replace(' ', '_')}"
CONFIG_FILE = APP_DIR / "config.json"


def ensure_app_dir():
    """Uygulama klasörünü oluşturur."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
