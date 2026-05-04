"""
LocalForge — Ana Sayfa
"""

import json
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="LocalForge",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys

sys.path.insert(0, str(Path(__file__).parent))
from ui.components.styles import inject_styles, forge_header
from core.state_manager import init_session_state, reset_project

inject_styles()

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    st.session_state.config = config


# Session state — state_manager ile kalıcı
init_session_state(st)
if "config" not in st.session_state:
    st.session_state.config = load_config()
if "system_info" not in st.session_state:
    st.session_state.system_info = None
if "requirements" not in st.session_state:
    st.session_state.requirements = None

cfg = st.session_state.config

# ─── Sidebar ───
with st.sidebar:
    st.markdown("## 🔨 LocalForge")
    st.caption("Yerel LLM ile otomatik proje geliştirme")
    st.divider()

    if st.session_state.project_path:
        pname = Path(st.session_state.project_path).name
        st.markdown(
            f"""
        <div style="background:#1e1e28;border:1px solid #f97316;border-radius:8px;padding:10px 14px;margin-bottom:8px;">
            <div style="color:#f97316;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;">Aktif Proje</div>
            <div style="color:#e2e2e8;font-weight:700;margin-top:2px;">{pname}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
        <div style="background:#1e1e28;border:1px solid #2a2a38;border-radius:8px;padding:10px 14px;margin-bottom:8px;">
            <div style="color:#6b6b80;font-size:0.85rem;">Proje seçilmedi</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    if cfg.get("planner_model"):
        st.markdown(f"🧠 `{cfg['planner_model']}`")
    if cfg.get("coder_model") and cfg.get("coder_model") != cfg.get("planner_model"):
        st.markdown(f"⚡ `{cfg['coder_model']}`")
    if cfg.get("backend"):
        icon = "🟢" if cfg.get("backend") == "ollama" else "🔵"
        st.markdown(f"{icon} **{cfg['backend'].upper()}**")

    st.divider()
    st.caption("v0.2.0 · LocalForge")

# ─── Ana Sayfa ───
forge_header("LocalForge", "Yerel LLM ile otomatik proje geliştirme ajanı", "BETA")

st.markdown(
    """
<div style="height:2px;background:linear-gradient(90deg,#f97316,#fbbf24,transparent);margin:16px 0 24px 0;border-radius:2px;"></div>
""",
    unsafe_allow_html=True,
)

# Adım kartları
col1, col2, col3, col4 = st.columns(4)

steps = [
    (
        "1️⃣",
        "Kurulum",
        "Sistemi tara, LLM seç",
        "pages/1_setup.py",
        bool(cfg.get("planner_model")),
        False,
    ),
    (
        "2️⃣",
        "Proje",
        "Gereksinimler & planlama",
        "pages/2_requirements.py",
        bool(st.session_state.requirements),
        not bool(cfg.get("planner_model")),
    ),
    (
        "3️⃣",
        "Kodla",
        "Ajan otomatik yazar",
        "pages/3_workspace.py",
        st.session_state.coding_done,
        not st.session_state.planning_done,
    ),
    (
        "4️⃣",
        "Düzenle",
        "Doğal dil ile revize",
        "pages/4_editor.py",
        False,
        not st.session_state.coding_done,
    ),
]

for col, (icon, title, caption, page, done, disabled) in zip(
    [col1, col2, col3, col4], steps
):
    with col:
        status = "✅ " if done else ""
        border = "#22c55e" if done else ("#f97316" if not disabled else "#2a2a38")
        st.markdown(
            f"""
        <div style="
            background:#16161d;
            border:1px solid {border};
            border-radius:10px;
            padding:18px;
            margin-bottom:8px;
            min-height:90px;
        ">
            <div style="font-size:1.4rem;">{icon}</div>
            <div style="font-family:'Syne',sans-serif;font-weight:700;color:{'#22c55e' if done else '#e2e2e8'};margin:4px 0 2px;">{status}{title}</div>
            <div style="color:#6b6b80;font-size:0.78rem;">{caption}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button(
            f"{'Görüntüle →' if done else 'Başla →'}",
            key=f"btn_{title}",
            use_container_width=True,
            disabled=disabled,
            type="primary" if not disabled and not done else "secondary",
        ):
            st.switch_page(page)

st.divider()

# Bilgi kartları
st.markdown("### 🧠 Nasıl Çalışır?")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        """
    <div style="background:#16161d;border:1px solid #2a2a38;border-radius:10px;padding:18px;">
        <div style="color:#f97316;font-size:1.2rem;margin-bottom:8px;">📋</div>
        <div style="font-family:'Syne',sans-serif;font-weight:700;margin-bottom:6px;">Token-Safe Hafıza</div>
        <div style="color:#6b6b80;font-size:0.82rem;">Tüm bağlam MD dosyalarında yaşar. Bağlam sıfırlansa bile kaldığı yerden devam eder.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        """
    <div style="background:#16161d;border:1px solid #2a2a38;border-radius:10px;padding:18px;">
        <div style="color:#f97316;font-size:1.2rem;margin-bottom:8px;">🤖</div>
        <div style="font-family:'Syne',sans-serif;font-weight:700;margin-bottom:6px;">Çift Model Stratejisi</div>
        <div style="color:#6b6b80;font-size:0.82rem;">Planlama için büyük model, kodlama için hızlı model. 8GB VRAM'e optimize.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        """
    <div style="background:#16161d;border:1px solid #2a2a38;border-radius:10px;padding:18px;">
        <div style="color:#f97316;font-size:1.2rem;margin-bottom:8px;">⏪</div>
        <div style="font-family:'Syne',sans-serif;font-weight:700;margin-bottom:6px;">Checkpoint & Rollback</div>
        <div style="color:#6b6b80;font-size:0.82rem;">Her görev sonrası snapshot. İstediğin noktaya tek tıkla geri dön.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
