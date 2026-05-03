"""
LocalForge — Ana Streamlit Uygulaması
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

# ─── Config yükle ───
CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

# Session state başlat
if "config" not in st.session_state:
    st.session_state.config = load_config()
if "project_path" not in st.session_state:
    st.session_state.project_path = ""
if "system_info" not in st.session_state:
    st.session_state.system_info = None
if "requirements" not in st.session_state:
    st.session_state.requirements = None
if "planning_done" not in st.session_state:
    st.session_state.planning_done = False
if "coding_done" not in st.session_state:
    st.session_state.coding_done = False

# ─── Sidebar ───
with st.sidebar:
    st.markdown("# 🔨 LocalForge")
    st.caption("Yerel LLM ile otomatik proje geliştirme")
    st.divider()

    # Aktif proje
    if st.session_state.project_path:
        st.success(f"📁 **{Path(st.session_state.project_path).name}**")
    else:
        st.info("📁 Henüz proje seçilmedi")

    st.divider()

    # Model durumu
    cfg = st.session_state.config
    if cfg.get("planner_model"):
        st.markdown(f"🧠 **Planlama:** `{cfg['planner_model']}`")
    if cfg.get("coder_model"):
        st.markdown(f"⚡ **Kodlama:** `{cfg['coder_model']}`")
    if cfg.get("backend"):
        backend_icon = "🟢" if cfg.get("backend") == "ollama" else "🔵"
        st.markdown(f"{backend_icon} **Backend:** `{cfg['backend']}`")

    st.divider()
    st.caption("v0.1.0 — Faz 4")

# ─── Ana sayfa ───
st.markdown("# 🔨 LocalForge")
st.markdown("**Yerel LLM ile otomatik proje geliştirme ajanı**")
st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 1️⃣ Kurulum")
    st.caption("Sistemi tara, LLM seç")
    if st.button("Kuruluma Git →", use_container_width=True, type="primary"):
        st.switch_page("ui/pages/1_setup.py")

with col2:
    st.markdown("### 2️⃣ Proje")
    st.caption("Gereksinimler & şablon")
    disabled = not (cfg.get("planner_model") and cfg.get("coder_model"))
    if st.button("Proje Tanımla →", use_container_width=True, disabled=disabled):
        st.switch_page("ui/pages/2_requirements.py")

with col3:
    st.markdown("### 3️⃣ Kodla")
    st.caption("Ajan otomatik yazar")
    disabled = not st.session_state.requirements
    if st.button("Kodlamayı Başlat →", use_container_width=True, disabled=disabled):
        st.switch_page("ui/pages/3_workspace.py")

with col4:
    st.markdown("### 4️⃣ Düzenle")
    st.caption("Doğal dil ile revize")
    disabled = not st.session_state.coding_done
    if st.button("Düzenlemeye Git →", use_container_width=True, disabled=disabled):
        st.switch_page("ui/pages/4_editor.py")

st.divider()

# Hızlı başlangıç
st.markdown("### 🚀 Hızlı Başlangıç")
st.markdown("""
1. **Kurulum** sayfasında sisteminizi tarayın ve LLM modellerinizi seçin
2. **Proje** sayfasında projenizi tanımlayın
3. **Kodla** sayfasında ajanın otomatik çalışmasını izleyin
4. **Düzenle** sayfasında doğal dil ile değişiklik isteyin
""")
