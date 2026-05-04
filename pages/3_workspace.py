"""
LocalForge — Sayfa 3: Çalışma Alanı
"""

import json
import streamlit as st
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.components.styles import inject_styles
from core.state_manager import (
    init_session_state,
    persist_project_path,
    persist_planning_done,
    persist_coding_done,
    reset_project,
)
from core.llm_client import create_client
from core.context_manager import ContextManager
from agents.coder_agent import CoderAgent

inject_styles()

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def render_task_list(container, ctx: ContextManager, active_task: str = ""):
    """
    Görev listesini tek HTML bloğu olarak render eder.
    st.empty() container'ı birden fazla st.* çağrısını desteklemez,
    bu yüzden tüm liste tek markdown çağrısıyla yazılır.
    """
    tasks = ctx.get_all_tasks()
    completed = sum(1 for t in tasks if t["done"])
    total = len(tasks)

    if total == 0:
        container.markdown("*Görev listesi yüklenemedi.*")
        return

    pct = int((completed / total) * 100)

    # Progress bar HTML
    html_parts = [f"""
    <div style="margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="color:#6b6b80;font-size:0.75rem;">İlerleme</span>
            <span style="color:#f97316;font-size:0.75rem;font-weight:700;">{completed}/{total}</span>
        </div>
        <div style="background:#1e1e28;border-radius:4px;height:6px;">
            <div style="background:linear-gradient(90deg,#f97316,#fbbf24);width:{pct}%;height:6px;border-radius:4px;transition:width 0.3s ease;"></div>
        </div>
    </div>
    <div style="display:flex;flex-direction:column;gap:2px;">
    """]

    active_set = False
    for task in tasks:
        name = task["name"]
        if task["done"]:
            html_parts.append(
                f'<div style="color:#22c55e;text-decoration:line-through;opacity:0.6;font-size:0.83rem;padding:2px 4px;">✅ {name}</div>'
            )
        elif name == active_task or (not active_set and not task["done"]):
            active_set = True
            html_parts.append(
                f'<div style="color:#f97316;font-weight:700;font-size:0.88rem;padding:4px 8px;border-left:3px solid #f97316;background:#1e1e28;border-radius:0 6px 6px 0;margin:2px 0;">⚡ {name}</div>'
            )
        else:
            html_parts.append(
                f'<div style="color:#6b6b80;font-size:0.83rem;padding:2px 4px;">○ {name}</div>'
            )

    html_parts.append("</div>")
    container.markdown("".join(html_parts), unsafe_allow_html=True)


init_session_state(st)
cfg = load_config()

# ─── Kontroller ───
if not st.session_state.get("project_path"):
    st.error("❌ Önce Proje sayfasından projeyi tanımlayın.")
    if st.button("Proje Sayfasına Git"):
        st.switch_page("pages/2_requirements.py")
    st.stop()

if not st.session_state.get("planning_done"):
    st.error("❌ Önce planlama tamamlanmalı.")
    if st.button("Planlama Sayfasına Git"):
        st.switch_page("pages/2_requirements.py")
    st.stop()

project_path = Path(st.session_state.project_path)
ctx = ContextManager(project_path)
approval_mode = cfg.get("approval_mode", False)

# ─── Başlık ───
st.markdown("# ⚡ Çalışma Alanı")
project_name = (
    ctx.read_file("PROJECT.md").split("\n")[0].replace("# Proje:", "").strip()
)
st.caption(f"Proje: **{project_name}** | `{project_path}`")
st.divider()

# ─── Tamamlanma Ekranı ───
if st.session_state.get("coding_done"):
    all_tasks = ctx.get_all_tasks()
    total = len(all_tasks)
    done = sum(1 for t in all_tasks if t["done"])

    st.success(f"🎉 Kodlama tamamlandı! **{done}/{total}** görev başarıyla üretildi.")
    st.progress(1.0, text="Tüm görevler tamamlandı")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✏️ Düzenlemeye Geç", type="primary", use_container_width=True):
            st.switch_page("pages/4_editor.py")
    with col2:
        if st.button("📁 Proje Klasörünü Aç", use_container_width=True):
            import subprocess, platform

            if platform.system() == "Windows":
                subprocess.Popen(f'explorer "{project_path}"')
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(project_path)])
            else:
                subprocess.Popen(["xdg-open", str(project_path)])
    with col3:
        if st.button("🔄 Yeni Proje", use_container_width=True):
            reset_project(st)
            st.switch_page("pages/2_requirements.py")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 📋 Görevler")
        for task in all_tasks:
            icon = "✅" if task["done"] else "❌"
            st.markdown(f"{icon} {task['name']}")
    with c2:
        st.markdown("### 📁 Üretilen Dosyalar")
        all_files = [
            str(f.relative_to(project_path))
            for f in sorted(project_path.rglob("*"))
            if f.is_file() and ".agent" not in f.parts and "__pycache__" not in f.parts
        ]
        for f in all_files:
            st.caption(f"📄 {f}")

    st.stop()

# ─── Layout ───
left_col, right_col = st.columns([1, 2])

# ─── SOL PANEL ───
with left_col:
    st.markdown("### 📋 Görevler")

    # Canlı güncellenebilir container
    task_list_container = st.empty()
    render_task_list(task_list_container, ctx)

    st.divider()
    mode_label = "✋ Onay Modu" if approval_mode else "🤖 Otomatik Mod"
    st.caption(f"**Mod:** {mode_label}")

    st.divider()

    # Checkpoints — canlı güncellenebilir
    st.markdown("### ⏪ Checkpoints")
    checkpoint_container = st.empty()

    def render_checkpoints(container):
        """Checkpoint listesini salt HTML olarak render eder — widget yok, key çakışması yok."""
        checkpoints = ctx.get_checkpoints()
        if not checkpoints:
            container.markdown(
                '<div style="color:#6b6b80;font-size:0.8rem;">Henüz checkpoint yok.</div>',
                unsafe_allow_html=True,
            )
            return
        html = '<div style="display:flex;flex-direction:column;gap:3px;">'
        for cp in reversed(checkpoints[-8:]):
            ts = (
                cp.get("timestamp", "")[:16].replace("T", " ")
                if cp.get("timestamp")
                else ""
            )
            html += (
                f'<div style="color:#22c55e;font-size:0.8rem;padding:2px 0;">'
                f'✅ {cp["task"]}'
                f'<span style="color:#6b6b80;font-size:0.7rem;margin-left:6px;">{ts}</span>'
                f"</div>"
            )
        html += "</div>"
        container.markdown(html, unsafe_allow_html=True)

    render_checkpoints(checkpoint_container)

    # Rollback butonları — statik, key çakışması olmaz
    checkpoints_static = ctx.get_checkpoints()
    if checkpoints_static:
        st.markdown("**Geri dön:**")
        for cp in reversed(checkpoints_static[-5:]):
            task_name = cp["task"]
            if st.button(
                f"↩️ {task_name[:20]}",
                key=f"static_rb_{task_name}",
                use_container_width=True,
                help=f"Checkpoint: {task_name}",
            ):
                try:
                    ctx.restore_checkpoint(task_name)
                    st.success(f"↩️ {task_name}'e dönüldü!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")

# ─── SAĞ PANEL ───
with right_col:
    st.markdown("### 🖥️ LLM Çıktısı")

    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        start_btn = st.button(
            "▶️ Başlat",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.get("coding_running", False),
        )
    with btn_col2:
        stop_btn = st.button(
            "⏹️ Durdur",
            use_container_width=True,
            disabled=not st.session_state.get("coding_running", False),
        )
    with btn_col3:
        if st.button("✏️ Düzenle →", use_container_width=True):
            st.switch_page("pages/4_editor.py")

    st.divider()

    output_area = st.empty()
    status_area = st.empty()

    if stop_btn:
        st.session_state.stop_requested = True

    # ─── KODLAMA DÖNGÜSÜ ───
    if start_btn and not st.session_state.get("coding_running", False):
        st.session_state.coding_running = True
        st.session_state.coding_done = False
        st.session_state.stop_requested = False

        coder_client = create_client(cfg, role="coder")

        if not coder_client.is_alive():
            st.session_state.coding_running = False
            status_area.error(f"❌ {cfg['backend']} bağlantısı kurulamadı.")
            st.stop()

        agent = CoderAgent(
            client=coder_client,
            context_manager=ctx,
            project_path=project_path,
            approval_mode=approval_mode,
        )

        live_output = ""
        current_task = ""
        runner = agent.run()

        try:
            event = next(runner)

            while True:
                if st.session_state.get("stop_requested", False):
                    agent.stop()

                etype = event.get("type", "")
                task = event.get("task", "")
                data = event.get("data", {})

                if etype == "session_start":
                    status_area.info(f"🚀 Kodlama başlıyor — {data['total']} görev")

                elif etype == "task_start":
                    current_task = task
                    live_output = ""
                    output_area.empty()
                    status_area.info(
                        f"⚡ [{data['index']}/{data['total']}] **{task}** işleniyor..."
                    )
                    # Sol paneli güncelle — aktif görevi vurgula
                    render_task_list(task_list_container, ctx, active_task=task)

                elif etype == "token":
                    live_output += data["token"]
                    output_area.code(live_output[-3000:], language="python")

                elif etype == "syntax_error":
                    status_area.warning(
                        f"⚠️ Syntax hatası: `{data['file']}` — Deneme {data['attempt']}/2"
                    )

                elif etype == "retry":
                    status_area.warning(f"🔄 Düzeltiliyor ({data['attempt']}/3)...")

                elif etype == "syntax_failed":
                    status_area.error(f"❌ {data['message']}")

                elif etype == "task_done":
                    files_str = ", ".join(f"`{f}`" for f in data["files"])
                    deps_str = (
                        f" | 📦 {', '.join(data['deps'])}" if data["deps"] else ""
                    )
                    status_area.success(f"✅ **{task}** — {files_str}{deps_str}")
                    live_output = ""
                    output_area.empty()
                    # Sol paneli güncelle — tamamlanan görev işaretlendi
                    render_task_list(task_list_container, ctx, active_task="")
                    # Checkpoint listesini güncelle
                    render_checkpoints(checkpoint_container)

                elif etype == "error":
                    status_area.error(f"❌ Hata ({task}): {data['error']}")

                elif etype == "stopped":
                    status_area.warning("⏹️ Durduruldu.")
                    render_task_list(task_list_container, ctx)
                    st.session_state.coding_running = False
                    break

                elif etype == "session_done":
                    persist_coding_done(st)
                    st.rerun()
                    break

                elif (
                    etype == "approval_needed" and data.get("action") == "approve_task"
                ):
                    status_area.warning(f"✋ **{task}** onay bekliyor...")
                    with output_area.container():
                        st.markdown(f"#### ✋ Onay: `{task}`")
                        for f in data.get("files", []):
                            fpath = project_path / f
                            if fpath.exists():
                                with st.expander(f"📄 {f}"):
                                    st.code(
                                        fpath.read_text(encoding="utf-8"),
                                        language=f.split(".")[-1],
                                    )
                        if data.get("deps"):
                            st.info(f"📦 {', '.join(data['deps'])}")
                        c1, c2, c3 = st.columns(3)
                        if c1.button("✅ Onayla", type="primary", key=f"ap_{task}"):
                            pass
                        if c3.button("⏭️ Atla", key=f"sk_{task}"):
                            st.session_state.skip_task = True

                # Generator ilerlet
                try:
                    approval = (
                        "skip" if st.session_state.get("skip_task") else "approve"
                    )
                    st.session_state.skip_task = False
                    event = (
                        runner.send(approval)
                        if etype == "waiting_approval"
                        else next(runner)
                    )
                except StopIteration:
                    st.session_state.coding_running = False
                    break

        except Exception as e:
            status_area.error(f"❌ Beklenmeyen hata: {e}")
            import traceback

            output_area.code(traceback.format_exc())
            st.session_state.coding_running = False
