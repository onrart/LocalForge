"""
LocalForge — Sayfa 4: Düzenleme
"""

import json
import streamlit as st
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm_client import create_client
from core.context_manager import ContextManager
from agents.editor_agent import EditorAgent, EditRequest, EditResult

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


cfg = load_config()

if not st.session_state.get("project_path"):
    st.error("❌ Önce Proje sayfasından projeyi tanımlayın.")
    if st.button("Proje Sayfasına Git"):
        st.switch_page("pages/2_requirements.py")
    st.stop()

project_path = Path(st.session_state.project_path)
ctx = ContextManager(project_path)

# ─── Başlık ───
st.markdown("# ✏️ Düzenleme")
project_name = (
    ctx.read_file("PROJECT.md").split("\n")[0].replace("# Proje:", "").strip()
)
st.caption(f"Proje: **{project_name}** | `{project_path}`")
st.divider()

# Geri dön butonu
col_back, col_space = st.columns([1, 5])
with col_back:
    if st.button("← Çalışma Alanı"):
        st.switch_page("pages/3_workspace.py")

st.divider()

# ─── Dosya Ağacı ───
all_files = [
    str(f.relative_to(project_path))
    for f in sorted(project_path.rglob("*"))
    if f.is_file() and ".agent" not in f.parts and "__pycache__" not in f.parts
]

if not all_files:
    st.info("Henüz dosya üretilmedi. Önce kodlama aşamasını tamamlayın.")
    if st.button("Çalışma Alanına Git"):
        st.switch_page("pages/3_workspace.py")
    st.stop()

# Dosya seçici — sol sidebar gibi iki kolon
file_col, content_col = st.columns([1, 3])

with file_col:
    st.markdown("### 📁 Dosyalar")

    # Uzantıya göre ikon
    def file_icon(f: str) -> str:
        ext = Path(f).suffix
        icons = {
            ".py": "🐍",
            ".json": "📋",
            ".md": "📝",
            ".txt": "📄",
            ".html": "🌐",
            ".css": "🎨",
            ".ts": "🔷",
            ".tsx": "🔷",
            ".js": "🟨",
        }
        return icons.get(ext, "📄")

    selected_file = st.radio(
        "Dosya seç",
        options=all_files,
        format_func=lambda x: f"{file_icon(x)} {x}",
        label_visibility="collapsed",
    )

with content_col:
    if not selected_file:
        st.info("Sol panelden bir dosya seçin.")
        st.stop()

    file_path = project_path / selected_file
    current_content = (
        file_path.read_text(encoding="utf-8") if file_path.exists() else ""
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
        "txt": "text",
    }
    lang = lang_map.get(ext, "text")

    tab1, tab2 = st.tabs(["🤖 LLM ile Düzenle", "✍️ Direkt Düzenle"])

    # ── Tab 1: LLM ile Düzenleme ──
    with tab1:
        st.markdown(f"**Seçili dosya:** `{selected_file}`")

        instruction = st.text_area(
            "Ne değiştirilsin?",
            placeholder="örn: Login endpoint'ine rate limiting ekle, dakikada max 5 istek olsun",
            height=100,
            key="llm_instruction",
        )

        context_hint = st.text_input(
            "Ek bağlam (opsiyonel)",
            placeholder="örn: slowapi kütüphanesi kullanılsın",
            key="llm_context_hint",
        )

        edit_btn = st.button(
            "🤖 Düzenle",
            type="primary",
            disabled=not instruction.strip(),
            use_container_width=True,
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

            # Streaming çıktı
            output_placeholder = st.empty()
            with st.spinner("🤖 LLM düzenleme yapıyor..."):
                full_response, edit_result = editor.edit_sync(request)
                if full_response:
                    output_placeholder.code(full_response[-2000:], language=lang)

            output_placeholder.empty()

            # Sonuç işle
            if edit_result is None:
                st.error("❌ LLM yanıtı parse edilemedi.")
            elif not edit_result.success:
                st.error(f"❌ Düzenleme başarısız: {edit_result.error}")
                if edit_result.new_content:
                    with st.expander("Üretilen kod (hatalı)"):
                        st.code(edit_result.new_content, language=lang)
            else:
                st.success(f"✅ {edit_result.change_summary}")

                # Metrikler
                d = edit_result.diff_summary
                m1, m2 = st.columns(2)
                m1.metric("Eklenen", f"+{d['added']} satır", delta=d["added"])
                m2.metric(
                    "Silinen",
                    f"-{d['removed']} satır",
                    delta=-d["removed"],
                    delta_color="inverse",
                )

                # Diff
                with st.expander("📋 Diff göster", expanded=True):
                    st.code(edit_result.diff, language="diff")

                # Onayla / Reddet
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(
                        "✅ Onayla ve Kaydet", type="primary", use_container_width=True
                    ):
                        if editor.apply_edit(edit_result):
                            st.success("✅ Kaydedildi! MEMORY.md güncellendi.")
                            st.rerun()
                        else:
                            st.error("❌ Kaydetme başarısız.")
                with c2:
                    if st.button("❌ Reddet", use_container_width=True):
                        st.rerun()

        # Mevcut dosya önizleme
        st.divider()
        with st.expander("👁️ Mevcut dosya içeriği", expanded=False):
            st.code(current_content, language=lang)

    # ── Tab 2: Direkt Düzenleme ──
    with tab2:
        st.caption(
            "Direkt düzenlediğinizde MEMORY.md'ye not düşülür, LLM bu dosyaya bir daha dokunmaz."
        )

        edited_content = st.text_area(
            "Dosya içeriği",
            value=current_content,
            height=500,
            label_visibility="collapsed",
            key=f"direct_edit_{selected_file}",
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            save_btn = st.button(
                "💾 Kaydet",
                type="primary",
                disabled=(edited_content == current_content),
                use_container_width=True,
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
                    f"✅ Kaydedildi — +{d['added']}/-{d['removed']} satır. MEMORY.md güncellendi."
                )
                with st.expander("📋 Diff"):
                    st.code(result["diff"], language="diff")
                st.rerun()
            else:
                st.error(f"❌ Kaydetme hatası: {result['error']}")
