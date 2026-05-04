"""
LocalForge — Sayfa 1: Kurulum
"""

import json
import streamlit as st
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.components.styles import inject_styles, forge_header, forge_task_item
from core.state_manager import (
    init_session_state,
    persist_project_path,
    persist_planning_done,
    persist_coding_done,
    reset_project,
)
from core.system_scanner import (
    scan,
    get_installed_ollama_models,
    get_installed_lmstudio_models,
)
from core.llm_recommender import recommend

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        "backend": "ollama",
        "ollama_url": "http://localhost:11434",
        "lmstudio_url": "http://localhost:1234",
        "planner_model": "",
        "coder_model": "",
        "approval_mode": False,
    }


def save_config(cfg: dict):
    CONFIG_PATH.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    st.session_state.config = cfg


inject_styles()

st.markdown("# 🖥️ Kurulum")
st.caption("Sisteminizi tarayın, backend ve model seçimlerini yapın.")
st.divider()

init_session_state(st)
cfg = load_config()

# ─── Backend ───
st.markdown("## 🔌 Backend Ayarları")
col1, col2 = st.columns(2)
with col1:
    backend = st.radio(
        "LLM Backend",
        options=["ollama", "lmstudio"],
        format_func=lambda x: "🟢 Ollama" if x == "ollama" else "🔵 LM Studio",
        index=0 if cfg.get("backend", "ollama") == "ollama" else 1,
        horizontal=True,
    )
    cfg["backend"] = backend

with col2:
    if backend == "ollama":
        cfg["ollama_url"] = st.text_input(
            "Ollama URL", value=cfg.get("ollama_url", "http://localhost:11434")
        )
    else:
        cfg["lmstudio_url"] = st.text_input(
            "LM Studio URL", value=cfg.get("lmstudio_url", "http://localhost:1234")
        )

if backend == "lmstudio":
    st.info(
        "ℹ️ **LM Studio'da aynı anda yalnızca 1 model aktif olabilir.** Planlama ve kodlama için aynı modeli seçmeniz önerilir."
    )

st.divider()

# ─── Sistem Tarama ───
st.markdown("## 🔍 Sistem Taraması")

if st.button("🔄 Sistemi Tara", type="primary"):
    with st.spinner("Taranıyor..."):
        info = scan(
            ollama_url=cfg.get("ollama_url", "http://localhost:11434"),
            lmstudio_url=cfg.get("lmstudio_url", "http://localhost:1234"),
        )
        st.session_state.system_info = info
        st.session_state.recommendations = recommend(info)
    st.rerun()

if st.session_state.get("system_info"):
    info = st.session_state.system_info

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("OS", info.os.split()[0])
    c2.metric("RAM", f"{info.ram_gb} GB")
    c3.metric("GPU", f"{info.vram_gb} GB VRAM" if info.vram_gb > 0 else "CPU Only")
    c4.metric("CPU", f"{info.cpu_cores} çekirdek")
    st.markdown(f"**🖥️ GPU:** {info.gpu_name}")

    col1, col2 = st.columns(2)
    with col1:
        if info.ollama_available:
            st.success(f"✅ Ollama — {info.ollama_version}")
        else:
            st.error("❌ Ollama bulunamadı")
    with col2:
        if info.lmstudio_available:
            st.success("✅ LM Studio bağlı")
        else:
            st.warning("⚠️ LM Studio bulunamadı")

    st.divider()

    # ─── Model Seçimi ───
    st.markdown("## 🤖 Model Seçimi")

    rec = st.session_state.get("recommendations", recommend(info))
    installed_models = []
    if backend == "ollama" and info.ollama_available:
        installed_models = get_installed_ollama_models(
            cfg.get("ollama_url", "http://localhost:11434")
        )
    elif backend == "lmstudio" and info.lmstudio_available:
        installed_models = get_installed_lmstudio_models(
            cfg.get("lmstudio_url", "http://localhost:1234")
        )

    if backend == "lmstudio" and installed_models:
        active_model = installed_models[0]
        st.success(f"🔵 Aktif model: `{active_model}`")

        use_same = st.checkbox(
            "Planlama ve kodlama için aynı modeli kullan (önerilen)", value=True
        )
        if use_same:
            cfg["planner_model"] = active_model
            cfg["coder_model"] = active_model
            st.caption(f"✅ Her ikisi için `{active_model}` kullanılacak.")
        else:
            st.warning(
                "⚠️ Farklı model seçerseniz LM Studio'da manuel değiştirmeniz gerekir."
            )
            col1, col2 = st.columns(2)
            with col1:
                cfg["planner_model"] = st.selectbox(
                    "Planlama", options=installed_models, key="planner_select"
                )
            with col2:
                cfg["coder_model"] = st.selectbox(
                    "Kodlama", options=installed_models, key="coder_select"
                )

    elif backend == "ollama":
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🧠 Planlama")
            planner_opts = [m.name for m in rec["planner"]]
            planner_labels = [
                f"{'⭐ ' if m.is_best else ''}{m.display_name}"
                + (" ✅" if m.name in installed_models else "")
                + (f" ({m.vram_required_gb}GB)" if m.vram_required_gb > 0 else " (CPU)")
                for m in rec["planner"]
            ]
            idx = (
                planner_opts.index(cfg.get("planner_model", ""))
                if cfg.get("planner_model") in planner_opts
                else 0
            )
            sel = st.radio(
                "Planlama",
                range(len(planner_opts)),
                format_func=lambda i: planner_labels[i],
                index=idx,
                label_visibility="collapsed",
            )
            custom = st.text_input(
                "Manuel gir", placeholder="örn: llama3.2:latest", key="custom_planner"
            )
            cfg["planner_model"] = (
                custom.strip() if custom.strip() else planner_opts[sel]
            )
            st.caption(f"Seçili: `{cfg['planner_model']}`")

        with col2:
            st.markdown("### ⚡ Kodlama")
            coder_opts = [m.name for m in rec["coder"]]
            coder_labels = [
                f"{'⭐ ' if m.is_best else ''}{m.display_name}"
                + (" ✅" if m.name in installed_models else "")
                + (f" ({m.vram_required_gb}GB)" if m.vram_required_gb > 0 else " (CPU)")
                for m in rec["coder"]
            ]
            idx2 = (
                coder_opts.index(cfg.get("coder_model", ""))
                if cfg.get("coder_model") in coder_opts
                else 0
            )
            sel2 = st.radio(
                "Kodlama",
                range(len(coder_opts)),
                format_func=lambda i: coder_labels[i],
                index=idx2,
                label_visibility="collapsed",
            )
            custom2 = st.text_input(
                "Manuel gir", placeholder="örn: qwen2.5-coder:7b", key="custom_coder"
            )
            cfg["coder_model"] = (
                custom2.strip() if custom2.strip() else coder_opts[sel2]
            )
            st.caption(f"Seçili: `{cfg['coder_model']}`")
    else:
        st.warning(
            "⚠️ Hiçbir model bulunamadı. LM Studio'da bir model yükleyin ve server'ı başlatın."
        )

    st.divider()

    # ─── Çalışma Modu ───
    st.markdown("## ⚙️ Çalışma Modu")
    approval_mode = st.toggle(
        "Onay Modu",
        value=cfg.get("approval_mode", False),
        help="Açık: Her görev sonrası onay | Kapalı: Tamamen otomatik",
    )
    cfg["approval_mode"] = approval_mode
    st.caption(
        "✋ Onay Modu: Her görev sonrası dosyalar gösterilir, onaylarsın."
        if approval_mode
        else "🤖 Otomatik Mod: Ajan durmadan ilerler."
    )

    st.divider()

    # ─── Kaydet & İlerle ───
    if st.button(
        "💾 Ayarları Kaydet ve Devam Et →", type="primary", use_container_width=True
    ):
        if not cfg.get("planner_model") or not cfg.get("coder_model"):
            st.error("❌ Model seçimi yapılmadı.")
        else:
            save_config(cfg)
            st.success("✅ Kaydedildi! Proje sayfasına yönlendiriliyorsunuz...")
            st.switch_page("pages/2_requirements.py")  # ← Otomatik ilerleme

else:
    st.info("👆 Başlamak için sistemi tarayın.")
