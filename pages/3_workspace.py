"""
LocalForge — Sayfa 3: Çalışma Alanı
"""

import json
import streamlit as st
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm_client import create_client
from core.context_manager import ContextManager
from agents.coder_agent import CoderAgent

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


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
            for key in ["project_path", "requirements", "planning_done", "coding_done"]:
                st.session_state.pop(key, None)
            st.switch_page("pages/2_requirements.py")

    st.divider()

    # Tamamlanan görevler
    st.markdown("### 📋 Tamamlanan Görevler")
    for task in all_tasks:
        icon = "✅" if task["done"] else "❌"
        st.markdown(f"{icon} {task['name']}")

    # Üretilen dosyalar
    st.divider()
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

    all_tasks = ctx.get_all_tasks()
    completed_count = sum(1 for t in all_tasks if t["done"])
    total_count = len(all_tasks)

    if total_count > 0:
        st.progress(
            completed_count / total_count,
            text=f"{completed_count}/{total_count} tamamlandı",
        )
        st.markdown("")

        active_set = False
        for task in all_tasks:
            if task["done"]:
                st.markdown(f"✅ ~~{task['name']}~~")
            elif not active_set:
                st.markdown(f"⚡ **{task['name']}**")
                active_set = True
            else:
                st.markdown(f"○ {task['name']}")
    else:
        st.info("Görev listesi yüklenemedi.")

    st.divider()
    mode_label = "✋ Onay Modu" if approval_mode else "🤖 Otomatik Mod"
    st.caption(f"**Mod:** {mode_label}")

    st.divider()

    # Checkpoints
    st.markdown("### ⏪ Checkpoints")
    checkpoints = ctx.get_checkpoints()
    if checkpoints:
        for cp in reversed(checkpoints):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.caption(f"✅ {cp['task']}")
            with col_b:
                if st.button("↩️", key=f"rb_{cp['task']}", help="Geri dön"):
                    try:
                        ctx.restore_checkpoint(cp["task"])
                        st.success(f"↩️ Geri dönüldü!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")
    else:
        st.caption("Henüz checkpoint yok.")

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
                    live_output = ""
                    status_area.info(
                        f"⚡ [{data['index']}/{data['total']}] **{task}** işleniyor..."
                    )

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

                elif etype == "error":
                    status_area.error(f"❌ Hata ({task}): {data['error']}")

                elif etype == "stopped":
                    status_area.warning("⏹️ Durduruldu.")
                    st.session_state.coding_running = False
                    break

                elif etype == "session_done":
                    st.session_state.coding_done = True
                    st.session_state.coding_running = False
                    st.rerun()  # Tamamlanma ekranını göster
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
                    if etype == "waiting_approval":
                        event = runner.send(approval)
                    else:
                        event = next(runner)
                except StopIteration:
                    st.session_state.coding_running = False
                    break

        except Exception as e:
            status_area.error(f"❌ Beklenmeyen hata: {e}")
            import traceback

            output_area.code(traceback.format_exc())
            st.session_state.coding_running = False
