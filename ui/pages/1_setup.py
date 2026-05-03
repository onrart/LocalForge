"""
LocalForge — Sayfa 1: Kurulum
Sistem tarama, Ollama/LM Studio bağlantı kontrolü, model seçimi.
"""

import json
import streamlit as st
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.system_scanner import (
    scan,
    get_installed_ollama_models,
    get_installed_lmstudio_models,
)
from core.llm_recommender import recommend

st.set_page_config(page_title="Kurulum — LocalForge", page_icon="🖥️", layout="wide")

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"


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


# ─── Başlık ───
st.markdown("# 🖥️ Kurulum")
st.caption("Sisteminizi tarayın, backend ve model seçimlerini yapın.")
st.divider()

cfg = load_config()

# ─── Backend & Port Ayarları ───
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
        ollama_url = st.text_input(
            "Ollama URL",
            value=cfg.get("ollama_url", "http://localhost:11434"),
            placeholder="http://localhost:11434",
        )
        cfg["ollama_url"] = ollama_url
    else:
        lmstudio_url = st.text_input(
            "LM Studio URL",
            value=cfg.get("lmstudio_url", "http://localhost:1234"),
            placeholder="http://localhost:1234",
        )
        cfg["lmstudio_url"] = lmstudio_url

st.divider()

# ─── Sistem Tarama ───
st.markdown("## 🔍 Sistem Taraması")

if st.button("🔄 Sistemi Tara", type="primary"):
    with st.spinner("Sistem taranıyor..."):
        info = scan(
            ollama_url=cfg.get("ollama_url", "http://localhost:11434"),
            lmstudio_url=cfg.get("lmstudio_url", "http://localhost:1234"),
        )
        st.session_state.system_info = info
        rec = recommend(info)
        st.session_state.recommendations = rec

if st.session_state.get("system_info"):
    info = st.session_state.system_info

    # Sistem bilgisi kartları
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("İşletim Sistemi", info.os.split()[0])
    with c2:
        st.metric("RAM", f"{info.ram_gb} GB")
    with c3:
        gpu_label = f"{info.vram_gb} GB VRAM" if info.vram_gb > 0 else "CPU Only"
        st.metric("GPU", gpu_label)
    with c4:
        st.metric("CPU Çekirdek", info.cpu_cores)

    st.markdown(f"**🖥️ GPU:** {info.gpu_name}")

    # Backend durumu
    col1, col2 = st.columns(2)
    with col1:
        if info.ollama_available:
            st.success(f"✅ Ollama bağlı — {info.ollama_version}")
        else:
            st.error("❌ Ollama bulunamadı")
            st.caption("https://ollama.ai adresinden indirebilirsiniz")
    with col2:
        if info.lmstudio_available:
            st.success("✅ LM Studio bağlı")
        else:
            st.warning("⚠️ LM Studio bulunamadı")
            st.caption("https://lmstudio.ai adresinden indirebilirsiniz")

    st.divider()

    # ─── Model Seçimi ───
    st.markdown("## 🤖 Model Seçimi")
    st.caption("Planlama için akıllı, kodlama için hızlı bir model seçin.")

    rec = st.session_state.get("recommendations", recommend(info))

    # Kurulu modelleri al
    installed_models = []
    if backend == "ollama" and info.ollama_available:
        installed_models = get_installed_ollama_models(
            cfg.get("ollama_url", "http://localhost:11434")
        )
    elif backend == "lmstudio" and info.lmstudio_available:
        installed_models = get_installed_lmstudio_models(
            cfg.get("lmstudio_url", "http://localhost:1234")
        )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🧠 Planlama Modeli")
        st.caption("Mimari kararlar ve görev listesi üretimi için")

        planner_options = [m.name for m in rec["planner"]]
        planner_labels = []
        for m in rec["planner"]:
            label = f"{'⭐ ' if m.is_best else ''}{m.display_name}"
            if m.name in installed_models:
                label += " ✅"
            label += (
                f" ({m.vram_required_gb}GB)" if m.vram_required_gb > 0 else " (CPU)"
            )
            planner_labels.append(label)

        # Mevcut seçimi bul
        current_planner = cfg.get("planner_model", "")
        planner_idx = (
            planner_options.index(current_planner)
            if current_planner in planner_options
            else 0
        )

        selected_planner_idx = st.radio(
            "Planlama modeli seç",
            options=range(len(planner_options)),
            format_func=lambda i: planner_labels[i],
            index=planner_idx,
            label_visibility="collapsed",
        )

        # Manuel model girişi
        custom_planner = st.text_input(
            "Veya manuel model adı gir",
            value=(
                ""
                if planner_options[selected_planner_idx] == current_planner
                else current_planner
            ),
            placeholder="örn: llama3.2:latest",
            key="custom_planner",
        )

        final_planner = (
            custom_planner.strip()
            if custom_planner.strip()
            else planner_options[selected_planner_idx]
        )
        st.caption(f"Seçili: `{final_planner}`")
        cfg["planner_model"] = final_planner

    with col2:
        st.markdown("### ⚡ Kodlama Modeli")
        st.caption("Hızlı ve hassas kod üretimi için")

        coder_options = [m.name for m in rec["coder"]]
        coder_labels = []
        for m in rec["coder"]:
            label = f"{'⭐ ' if m.is_best else ''}{m.display_name}"
            if m.name in installed_models:
                label += " ✅"
            label += (
                f" ({m.vram_required_gb}GB)" if m.vram_required_gb > 0 else " (CPU)"
            )
            coder_labels.append(label)

        current_coder = cfg.get("coder_model", "")
        coder_idx = (
            coder_options.index(current_coder) if current_coder in coder_options else 0
        )

        selected_coder_idx = st.radio(
            "Kodlama modeli seç",
            options=range(len(coder_options)),
            format_func=lambda i: coder_labels[i],
            index=coder_idx,
            label_visibility="collapsed",
        )

        custom_coder = st.text_input(
            "Veya manuel model adı gir",
            value=(
                ""
                if coder_options[selected_coder_idx] == current_coder
                else current_coder
            ),
            placeholder="örn: qwen2.5-coder:7b",
            key="custom_coder",
        )

        final_coder = (
            custom_coder.strip()
            if custom_coder.strip()
            else coder_options[selected_coder_idx]
        )
        st.caption(f"Seçili: `{final_coder}`")
        cfg["coder_model"] = final_coder

    st.divider()

    # ─── Çalışma Modu ───
    st.markdown("## ⚙️ Çalışma Modu")
    approval_mode = st.toggle(
        "Onay Modu",
        value=cfg.get("approval_mode", False),
        help="Açık: Her görev sonrası onay bekler | Kapalı: Tamamen otomatik ilerler",
    )
    cfg["approval_mode"] = approval_mode
    if approval_mode:
        st.info(
            "✋ Her görev tamamlandığında üretilen dosyalar gösterilir → Onayla / Düzenle / Atla"
        )
    else:
        st.info("🤖 Ajan görevleri sırayla otomatik tamamlar, müdahale gerektirmez")

    st.divider()

    # ─── Kaydet ───
    if st.button("💾 Ayarları Kaydet", type="primary", use_container_width=True):
        save_config(cfg)
        st.success("✅ Ayarlar kaydedildi! Proje tanımlama sayfasına geçebilirsiniz.")
        st.balloons()

else:
    st.info("👆 Sistemi taramak için butona tıklayın.")
