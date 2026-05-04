"""
LocalForge — Sayfa 2: Proje Tanımlama
Kullanıcıdan proje gereksinimlerini toplar, planlama ajanını çalıştırır.
"""

import json
import streamlit as st
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.components.styles import inject_styles, forge_header, forge_task_item
from core.requirements_collector import (
    ProjectRequirements,
    render_collection_form,
    init_session_state,
    _generate_requirements_md,
)
from core.llm_client import create_client
from core.context_manager import ContextManager
from core.template_manager import apply_template, build_placeholders, detect_template
from agents.planner_agent import PlannerAgent

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


cfg = load_config()
init_session_state(st)

inject_styles()

st.markdown("# 📋 Proje Tanımlama")
st.caption("Projenizi tanımlayın, ajan mimariyi ve görev listesini otomatik oluşturur.")
st.divider()

# Model kontrolü
if not cfg.get("planner_model"):
    st.error("❌ Önce Kurulum sayfasından model seçin.")
    if st.button("Kuruluma Git"):
        st.switch_page("pages/1_setup.py")
    st.stop()

st.caption(
    f"🧠 Planlama: `{cfg['planner_model']}` | ⚡ Kodlama: `{cfg['coder_model']}`"
)
st.divider()

# ─── Proje Klasörü ───
st.markdown("## 📁 Proje Konumu")
col1, col2 = st.columns([3, 1])
with col1:
    project_path_input = st.text_input(
        "Projenin oluşturulacağı klasör",
        value=st.session_state.get("project_path", ""),
        placeholder="C:/Users/kullanici/Projeler/benim-projem",
    )
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if project_path_input and st.button("✅ Onayla"):
        p = Path(project_path_input)
        p.mkdir(parents=True, exist_ok=True)
        st.session_state.project_path = str(p)
        st.rerun()

if st.session_state.get("project_path"):
    st.success(f"📁 `{st.session_state.project_path}`")
else:
    st.warning("Proje klasörünü girin ve onaylayın.")
    st.stop()

st.divider()

# ─── Form ───
completed_req = render_collection_form(st)

# ─── Planlama ───
if completed_req:
    st.divider()
    st.markdown("## 🧠 Planlama")

    project_path = Path(st.session_state.project_path)
    ctx = ContextManager(project_path)
    ctx.init(completed_req.to_dict())

    # REQUIREMENTS.md override kontrolü
    if "requirements_md_override" in st.session_state:
        ctx.update_requirements(st.session_state.requirements_md_override)

    # ─── Şablon Uygula ───
    if completed_req.detected_template and st.session_state.get("template_accepted"):
        with st.spinner(f"📦 {completed_req.detected_template} şablonu uygulanıyor..."):
            placeholders = build_placeholders(
                completed_req.name,
                completed_req.description,
            )
            copied = apply_template(
                completed_req.detected_template,
                project_path,
                placeholders,
            )
        if copied:
            st.success(f"✅ Şablon uygulandı — {len(copied)} dosya kopyalandı.")
        else:
            st.info("ℹ️ Şablon dosyaları zaten mevcut, atlandı.")

    # ─── Backend Kontrolü ───
    planner_client = create_client(cfg, role="planner")
    if not planner_client.is_alive():
        st.error(f"❌ {cfg['backend']} bağlantısı kurulamadı. Backend çalışıyor mu?")
        st.stop()

    st.info(f"🧠 `{cfg['planner_model']}` ile planlama başlıyor...")

    output_placeholder = st.empty()
    full_output = ""

    planner = PlannerAgent(planner_client, ctx)

    with st.spinner("Ajan mimariyi planlıyor..."):
        for chunk in planner.plan_stream(completed_req):
            full_output += chunk
            output_placeholder.code(full_output[-2000:], language="markdown")

    st.success("✅ Planlama tamamlandı!")
    st.session_state.requirements = completed_req
    st.session_state.planning_done = True

    st.divider()

    # Önizleme
    agent_dir = project_path / ".agent"
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📋 Görev Listesi")
        tasks_file = agent_dir / "TASKS.md"
        if tasks_file.exists():
            tasks_content = tasks_file.read_text(encoding="utf-8")
            st.code(tasks_content, language="markdown")
            task_count = tasks_content.count("- [ ]")
            st.metric("Toplam Görev", task_count)
        else:
            st.warning("TASKS.md oluşturulamadı.")

    with col2:
        st.markdown("### 🏗️ Mimari")
        arch_file = agent_dir / "ARCHITECTURE.md"
        if arch_file.exists():
            st.markdown(arch_file.read_text(encoding="utf-8"))
        else:
            st.warning("ARCHITECTURE.md oluşturulamadı.")

    st.divider()
    st.info("🚀 Kodlama sayfasına yönlendiriliyorsunuz...")
    st.switch_page("pages/3_workspace.py")
