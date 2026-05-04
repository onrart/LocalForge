"""
LocalForge — State Manager
Session state'i config.json üzerinden kalıcı hale getirir.
Sayfa yenilendiğinde veya Streamlit rerun'da state kaybolmaz.
"""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"

# State anahtarları ve varsayılan değerleri
STATE_KEYS = {
    "project_path": "",
    "planning_done": False,
    "coding_done": False,
    "coding_running": False,
    "stop_requested": False,
    "skip_task": False,
    "template_accepted": None,
    "collection_step": 1,
}


def load_config() -> dict:
    """config.json'dan tam konfigürasyonu okur."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(cfg: dict):
    """Konfigürasyonu config.json'a yazar."""
    CONFIG_PATH.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def init_session_state(st) -> None:
    """
    Streamlit session_state'i başlatır.
    config.json'dan proje durumunu geri yükler.
    Her sayfa başında çağrılmalı.
    """
    cfg = load_config()

    # Config'den gelen değerler
    if "config" not in st.session_state:
        st.session_state.config = cfg

    # Proje durumu — config.json'dan geri yükle
    if "project_path" not in st.session_state:
        st.session_state.project_path = cfg.get("last_project", "")

    if "planning_done" not in st.session_state:
        # Proje klasörü varsa ve .agent/TASKS.md varsa planning_done=True
        project_path = st.session_state.get("project_path", "")
        if project_path:
            tasks_file = Path(project_path) / ".agent" / "TASKS.md"
            st.session_state.planning_done = tasks_file.exists()
        else:
            st.session_state.planning_done = False

    if "coding_done" not in st.session_state:
        # Sadece config.json'da explicit olarak kaydedilmişse True say
        # TASKS.md'den otomatik tespit etme — yanlış proje okuyabilir
        project_path = st.session_state.get("project_path", "")
        saved_done = cfg.get("coding_done_project", "")
        # Aynı proje için daha önce coding_done kaydedildiyse True
        if project_path and project_path == saved_done:
            st.session_state.coding_done = True
        else:
            st.session_state.coding_done = False

    # Runtime state — her zaman sıfırla (güvenli)
    for key, default in [
        ("coding_running", False),
        ("stop_requested", False),
        ("skip_task", False),
        ("template_accepted", None),
        ("collection_step", 1),
        ("requirements", None),
        ("system_info", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


def persist_project_path(st, project_path: str) -> None:
    """
    Proje klasörünü hem session_state'e hem config.json'a yazar.
    Sayfa yenilense bile kaybolmaz.
    """
    st.session_state.project_path = project_path
    cfg = load_config()
    cfg["last_project"] = project_path
    save_config(cfg)


def persist_planning_done(st) -> None:
    """Planning tamamlandığını işaretle."""
    st.session_state.planning_done = True


def persist_coding_done(st) -> None:
    """Coding tamamlandığını işaretle — proje yolu ile birlikte kaydet."""
    st.session_state.coding_done = True
    st.session_state.coding_running = False
    # Hangi projenin tamamlandığını config.json'a kaydet
    cfg = load_config()
    cfg["coding_done_project"] = st.session_state.get("project_path", "")
    save_config(cfg)


def reset_project(st) -> None:
    """Yeni proje için tüm state'i sıfırla."""
    for key in [
        "project_path",
        "planning_done",
        "coding_done",
        "coding_running",
        "requirements",
        "template_accepted",
    ]:
        st.session_state.pop(key, None)

    cfg = load_config()
    cfg["last_project"] = ""
    cfg["coding_done_project"] = ""
    save_config(cfg)
