"""
LocalForge — Sayfa 3: Çalışma Alanı
Coder ajanını çalıştırır, görev takibi, canlı çıktı, checkpoint geçmişi.
"""

import json
import time
import streamlit as st
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.llm_client import create_client
from core.context_manager import ContextManager
from agents.coder_agent import CoderAgent

st.set_page_config(
    page_title="Çalışma Alanı — LocalForge", page_icon="⚡", layout="wide"
)

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


cfg = load_config()

# Kontroller
if not st.session_state.get("project_path"):
    st.error("❌ Önce Proje sayfasından projeyi tanımlayın.")
    st.stop()

if not st.session_state.get("planning_done"):
    st.error("❌ Önce planlama tamamlanmalı.")
    st.stop()

project_path = Path(st.session_state.project_path)
ctx = ContextManager(project_path)

# ─── Başlık ───
st.markdown("# ⚡ Çalışma Alanı")
project_name = (
    ctx.read_file("PROJECT.md").split("\n")[0].replace("# Proje:", "").strip()
)
st.caption(f"Proje: **{project_name}** | `{project_path}`")
st.divider()

# ─── Layout ───
left_col, right_col = st.columns([1, 2])

# ─── SOL: Görev Takibi & Checkpoints ───
with left_col:
    st.markdown("### 📋 Görevler")

    all_tasks = ctx.get_all_tasks()
    if all_tasks:
        for task in all_tasks:
            icon = "✅" if task["done"] else "⏳"
            active = not task["done"] and all(
                t["done"]
                for t in all_tasks
                if all_tasks.index(t) < all_tasks.index(task)
            )
            if active:
                st.markdown(f"**→ {icon} {task['name']}**")
            else:
                st.markdown(f"{icon} {task['name']}")
    else:
        st.info("Görev listesi yüklenemedi.")

    st.divider()

    # Çalışma Modu
    approval_mode = cfg.get("approval_mode", False)
    mode_label = "✋ Onay Modu" if approval_mode else "🤖 Otomatik Mod"
    st.markdown(f"**Mod:** {mode_label}")

    st.divider()

    # Checkpoint Geçmişi
    st.markdown("### ⏪ Checkpoints")
    checkpoints = ctx.get_checkpoints()

    if checkpoints:
        for cp in reversed(checkpoints):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.caption(f"✅ {cp['task']}")
            with col2:
                if st.button(
                    "↩️", key=f"rollback_{cp['task']}", help=f"Geri dön: {cp['task']}"
                ):
                    try:
                        ctx.restore_checkpoint(cp["task"])
                        st.success(f"✅ {cp['task']} checkpoint'ine dönüldü!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Rollback hatası: {e}")
    else:
        st.caption("Henüz checkpoint yok.")

# ─── SAĞ: LLM Çıktısı & Kontroller ───
with right_col:
    st.markdown("### 🖥️ LLM Çıktısı")

    # Kontrol butonları
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
        if st.button(
            "✏️ Düzenle →",
            use_container_width=True,
            disabled=not st.session_state.get("coding_done", False),
        ):
            st.switch_page("ui/pages/4_editor.py")

    st.divider()

    # Progress bar
    completed = sum(1 for t in all_tasks if t["done"])
    total = len(all_tasks)
    if total > 0:
        st.progress(completed / total, text=f"{completed}/{total} görev tamamlandı")

    # LLM çıktı alanı
    output_area = st.empty()
    status_area = st.empty()
    approval_area = st.empty()

    # ─── KODLAMA DÖNGÜSÜ ───
    if start_btn and not st.session_state.get("coding_running", False):
        st.session_state.coding_running = True
        st.session_state.coding_done = False

        coder_client = create_client(cfg, role="coder")

        if not coder_client.is_alive():
            st.error(f"❌ {cfg['backend']} bağlantısı kurulamadı.")
            st.session_state.coding_running = False
            st.stop()

        agent = CoderAgent(
            client=coder_client,
            context_manager=ctx,
            project_path=project_path,
            approval_mode=approval_mode,
        )

        if stop_btn:
            agent.stop()

        live_output = ""
        current_task = ""
        waiting_approval = False
        approval_result = None

        runner = agent.run()

        try:
            event = next(runner)

            while True:
                etype = event.get("type", "")
                task = event.get("task", "")
                data = event.get("data", {})

                if etype == "session_start":
                    status_area.info(f"🚀 Kodlama başlıyor — {data['total']} görev")

                elif etype == "task_start":
                    current_task = task
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
                    status_area.warning(
                        f"🔄 Düzeltme deneniyor ({data['attempt']}/3)..."
                    )

                elif etype == "syntax_failed":
                    status_area.error(f"❌ {data['message']}")

                elif etype == "task_done":
                    files_str = ", ".join(f"`{f}`" for f in data["files"])
                    deps_str = (
                        f" | Yeni paket: {', '.join(data['deps'])}"
                        if data["deps"]
                        else ""
                    )
                    status_area.success(
                        f"✅ **{task}** tamamlandı — {files_str}{deps_str}"
                    )
                    st.rerun()

                elif etype == "approval_needed":
                    if data.get("action") == "approve_task":
                        with approval_area.container():
                            st.markdown(f"### ✋ Onay Bekleniyor: `{task}`")
                            st.markdown("**Üretilen dosyalar:**")
                            for f in data.get("files", []):
                                fpath = project_path / f
                                if fpath.exists():
                                    with st.expander(f"📄 {f}"):
                                        st.code(
                                            fpath.read_text(encoding="utf-8"),
                                            language=f.split(".")[-1],
                                        )

                            if data.get("deps"):
                                st.info(
                                    f"📦 Eklenen bağımlılıklar: {', '.join(data['deps'])}"
                                )

                            c1, c2, c3 = st.columns(3)
                            approved = c1.button("✅ Onayla", type="primary")
                            edited = c2.button("✏️ Düzenle")
                            skipped = c3.button("⏭️ Atla")

                            if approved:
                                approval_result = "approve"
                                approval_area.empty()
                            elif edited:
                                st.switch_page("ui/pages/4_editor.py")
                            elif skipped:
                                approval_result = "skip"
                                approval_area.empty()

                elif etype == "error":
                    status_area.error(f"❌ Hata: {data['error']}")

                elif etype == "stopped":
                    status_area.warning("⏹️ Durduruldu.")
                    break

                elif etype == "session_done":
                    status_area.success("🎉 Tüm görevler tamamlandı!")
                    st.session_state.coding_done = True
                    st.session_state.coding_running = False
                    st.balloons()
                    break

                # Generator'ı ilerlet
                try:
                    if etype == "waiting_approval":
                        event = runner.send(approval_result or "approve")
                        approval_result = None
                    else:
                        event = next(runner)
                except StopIteration:
                    break

        except Exception as e:
            status_area.error(f"❌ Beklenmeyen hata: {e}")
            st.session_state.coding_running = False

        st.session_state.coding_running = False
        st.rerun()
