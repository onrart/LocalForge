"""
LocalForge — Sayfa 4: Düzenleme
Doğal dil ile kod düzenleme, diff görünümü, onay/red.
"""

import json
import streamlit as st
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.llm_client import create_client
from core.context_manager import ContextManager
from agents.editor_agent import EditorAgent, EditRequest

st.set_page_config(page_title="Düzenleme — LocalForge", page_icon="✏️", layout="wide")

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


cfg = load_config()

if not st.session_state.get("project_path"):
    st.error("❌ Önce Proje sayfasından projeyi tanımlayın.")
    st.stop()

project_path = Path(st.session_state.project_path)
ctx = ContextManager(project_path)

st.markdown("# ✏️ Düzenleme")
st.caption("Doğal dil ile değişiklik isteyin veya kodu direkt düzenleyin.")
st.divider()

# ─── Dosya Ağacı ───
st.markdown("## 📁 Proje Dosyaları")

all_files = []
for f in sorted(project_path.rglob("*")):
    if f.is_file() and ".agent" not in f.parts and "__pycache__" not in f.parts:
        rel = str(f.relative_to(project_path))
        all_files.append(rel)

if not all_files:
    st.info("Henüz dosya üretilmedi. Önce kodlama aşamasını tamamlayın.")
    st.stop()

selected_file = st.selectbox(
    "Düzenlenecek dosyayı seç",
    options=all_files,
    format_func=lambda x: f"📄 {x}",
)

st.divider()

# ─── Dosya İçeriği ───
tab1, tab2 = st.tabs(["🤖 LLM ile Düzenle", "✍️ Direkt Düzenle"])

file_path = project_path / selected_file
current_content = file_path.read_text(encoding="utf-8") if file_path.exists() else ""

# ── Tab 1: LLM ile Düzenleme ──
with tab1:
    st.markdown("### Düzenleme İsteği")
    instruction = st.text_area(
        "Ne değiştirilsin?",
        placeholder="örn: Login endpoint'ine rate limiting ekle, dakikada max 5 istek olsun",
        height=80,
        label_visibility="collapsed",
    )

    context_hint = st.text_input(
        "Ek bağlam (opsiyonel)",
        placeholder="örn: slowapi kütüphanesi kullanılsın",
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        edit_btn = st.button(
            "🤖 Düzenle", type="primary", disabled=not instruction.strip()
        )

    if edit_btn and instruction.strip():
        coder_client = create_client(cfg, role="coder")

        if not coder_client.is_alive():
            st.error(f"❌ {cfg['backend']} bağlantısı kurulamadı.")
            st.stop()

        editor = EditorAgent(coder_client, ctx, project_path)
        request = EditRequest(
            instruction=instruction,
            target_file=selected_file,
            context_hint=context_hint,
        )

        st.markdown("### 🖥️ LLM Çıktısı")
        output_placeholder = st.empty()
        full_output = ""

        edit_result = None
        gen = editor.edit_stream(request)

        try:
            while True:
                chunk = next(gen)
                if isinstance(chunk, str):
                    full_output += chunk
                    output_placeholder.code(full_output[-2000:], language="python")
                else:
                    edit_result = chunk
                    break
        except StopIteration as e:
            edit_result = e.value

        if edit_result and edit_result.success:
            st.divider()
            st.markdown("### 📊 Değişiklik Özeti")
            st.info(f"**{edit_result.change_summary}**")

            d = edit_result.diff_summary
            col1, col2 = st.columns(2)
            col1.metric("Eklenen Satır", f"+{d['added']}", delta=d["added"])
            col2.metric(
                "Silinen Satır",
                f"-{d['removed']}",
                delta=-d["removed"],
                delta_color="inverse",
            )

            st.markdown("### 📋 Diff")
            st.code(edit_result.diff, language="diff")

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                if st.button(
                    "✅ Onayla ve Kaydet", type="primary", use_container_width=True
                ):
                    if editor.apply_edit(edit_result):
                        st.success(
                            "✅ Değişiklikler kaydedildi! MEMORY.md güncellendi."
                        )
                        st.rerun()
                    else:
                        st.error("❌ Kaydetme başarısız.")
            with c2:
                if st.button("❌ Reddet", use_container_width=True):
                    st.info("Değişiklikler reddedildi.")
                    st.rerun()

        elif edit_result:
            st.error(f"❌ Düzenleme başarısız: {edit_result.error}")

# ── Tab 2: Direkt Düzenleme ──
with tab2:
    st.markdown(f"### 📄 `{selected_file}`")
    st.caption(
        "Direkt düzenlediğinizde değişiklikler MEMORY.md'ye kaydedilir, LLM bu dosyaya bir daha dokunmaz."
    )

    ext = Path(selected_file).suffix.lstrip(".")
    lang_map = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "json": "json",
        "md": "markdown",
        "html": "html",
        "css": "css",
    }
    lang = lang_map.get(ext, "text")

    edited_content = st.text_area(
        "Dosya içeriği",
        value=current_content,
        height=500,
        label_visibility="collapsed",
        key=f"editor_{selected_file}",
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        save_btn = st.button(
            "💾 Kaydet",
            type="primary",
            disabled=(edited_content == current_content),
        )

    if save_btn and edited_content != current_content:
        coder_client = create_client(cfg, role="coder")
        editor = EditorAgent(coder_client, ctx, project_path)
        result = editor.apply_manual_edit(
            selected_file, edited_content, current_content
        )

        if result["success"]:
            d = result["diff_summary"]
            st.success(
                f"✅ Kaydedildi — +{d['added']}/{d['removed']} satır. MEMORY.md güncellendi."
            )
            st.code(result["diff"], language="diff")
            st.rerun()
        else:
            st.error(f"❌ Kaydetme hatası: {result['error']}")

    # Mevcut dosyayı göster
    st.divider()
    st.markdown("**Mevcut içerik:**")
    st.code(current_content, language=lang)
