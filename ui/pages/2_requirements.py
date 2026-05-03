"""
LocalForge — Sayfa 2: Proje Tanımlama
Kullanıcıdan proje gereksinimlerini toplar, planlama ajanını çalıştırır.
"""

import json
import streamlit as st
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.requirements_collector import (
    ProjectRequirements,
    detect_template,
    get_template_description,
    render_collection_form,
    init_session_state,
    _generate_requirements_md,
)
from core.llm_client import create_client
from core.context_manager import ContextManager
from agents.planner_agent import PlannerAgent

st.set_page_config(page_title="Proje — LocalForge", page_icon="📋", layout="wide")

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


cfg = load_config()
init_session_state(st)

st.markdown("# 📋 Proje Tanımlama")
st.caption("Projenizi tanımlayın, ajan mimariyi ve görev listesini otomatik oluşturur.")
st.divider()

# Model kontrolü
if not cfg.get("planner_model"):
    st.error("❌ Önce Kurulum sayfasından model seçin.")
    st.stop()

st.caption(
    f"🧠 Planlama: `{cfg['planner_model']}` | ⚡ Kodlama: `{cfg['coder_model']}`"
)
st.divider()

# ─── Proje Klasörü ───
st.markdown("## 📁 Proje Konumu")
col1, col2 = st.columns([3, 1])
with col1:
    project_path = st.text_input(
        "Projenin oluşturulacağı klasör",
        value=st.session_state.get("project_path", ""),
        placeholder="C:/Users/kullanici/Projeler/benim-projem",
    )
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if project_path and st.button("✅ Klasörü Onayla"):
        p = Path(project_path)
        p.mkdir(parents=True, exist_ok=True)
        st.session_state.project_path = str(p)
        st.success(f"Klasör hazır: `{p}`")

if not st.session_state.get("project_path"):
    st.warning("Proje klasörünü girin ve onaylayın.")
    st.stop()

st.divider()

# ─── Form ───
completed_req = render_collection_form(st)

# ─── Planlama ───
if completed_req:
    st.divider()
    st.markdown("## 🧠 Planlama")

    # Context manager başlat
    ctx = ContextManager(st.session_state.project_path)
    ctx.init(completed_req.to_dict())

    # REQUIREMENTS.md override kontrolü
    if "requirements_md_override" in st.session_state:
        ctx.update_requirements(st.session_state.requirements_md_override)

    planner_client = create_client(cfg, role="planner")

    if not planner_client.is_alive():
        st.error(f"❌ {cfg['backend']} bağlantısı kurulamadı. Backend çalışıyor mu?")
        st.stop()

    planner = PlannerAgent(planner_client, ctx)

    st.info(f"🧠 `{cfg['planner_model']}` ile planlama başlıyor...")

    output_placeholder = st.empty()
    full_output = ""

    with st.spinner("Ajan mimariyi planlıyor..."):
        for chunk in planner.plan_stream(completed_req):
            full_output += chunk
            output_placeholder.markdown(
                f"```\n{full_output[-2000:]}\n```"  # Son 2000 karakter göster
            )

    st.success("✅ Planlama tamamlandı!")
    st.session_state.requirements = completed_req
    st.session_state.planning_done = True

    st.divider()

    # TASKS.md ve ARCHITECTURE.md önizleme
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📋 Görev Listesi")
        tasks_content = (
            Path(st.session_state.project_path) / ".agent" / "TASKS.md"
        ).read_text(encoding="utf-8")
        st.code(tasks_content, language="markdown")

        task_count = tasks_content.count("- [ ]")
        st.metric("Toplam Görev", task_count)

    with col2:
        st.markdown("### 🏗️ Mimari")
        arch_content = (
            Path(st.session_state.project_path) / ".agent" / "ARCHITECTURE.md"
        ).read_text(encoding="utf-8")
        st.markdown(arch_content)

    st.divider()
    if st.button("⚡ Kodlamaya Geç →", type="primary", use_container_width=True):
        st.switch_page("ui/pages/3_workspace.py")
