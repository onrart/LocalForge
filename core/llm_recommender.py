"""
LocalForge — LLM Recommender
Sistem bilgisine göre uygun modelleri önerir.
"""

from dataclasses import dataclass
from typing import Optional
from core.system_scanner import SystemInfo


@dataclass
class ModelRecommendation:
    name: str               # Örn: "qwen2.5-coder:7b"
    display_name: str       # Örn: "Qwen2.5 Coder 7B"
    role: str               # "planner" | "coder" | "both"
    vram_required_gb: float
    pull_command: str       # "ollama pull qwen2.5-coder:7b"
    description: str
    is_best: bool = False   # Önerilen birincil seçim mi?


# ─────────────────────────────────────────
# Model Kataloğu
# ─────────────────────────────────────────

PLANNER_MODELS = [
    ModelRecommendation(
        name="qwen2.5:32b",
        display_name="Qwen2.5 32B",
        role="planner",
        vram_required_gb=16.0,
        pull_command="ollama pull qwen2.5:32b",
        description="En güçlü planlama modeli, karmaşık mimari kararlar için."
    ),
    ModelRecommendation(
        name="qwen2.5:14b",
        display_name="Qwen2.5 14B",
        role="planner",
        vram_required_gb=10.0,
        pull_command="ollama pull qwen2.5:14b",
        description="Güçlü akıl yürütme, mimari planlama için ideal."
    ),
    ModelRecommendation(
        name="mistral:7b",
        display_name="Mistral 7B",
        role="planner",
        vram_required_gb=5.5,
        pull_command="ollama pull mistral:7b",
        description="Hızlı ve yetenekli, orta ölçekli projeler için yeterli."
    ),
    ModelRecommendation(
        name="qwen2.5:7b",
        display_name="Qwen2.5 7B",
        role="planner",
        vram_required_gb=5.0,
        pull_command="ollama pull qwen2.5:7b",
        description="Dengeli planlama modeli, 8GB VRAM için uygun."
    ),
    ModelRecommendation(
        name="qwen2.5:3b",
        display_name="Qwen2.5 3B",
        role="planner",
        vram_required_gb=2.5,
        pull_command="ollama pull qwen2.5:3b",
        description="Düşük VRAM için hafif planlama modeli."
    ),
    ModelRecommendation(
        name="phi3:mini",
        display_name="Phi-3 Mini",
        role="planner",
        vram_required_gb=0.0,  # CPU
        pull_command="ollama pull phi3:mini",
        description="GPU gerektirmez, CPU'da çalışır. En temel seçenek."
    ),
]

CODER_MODELS = [
    ModelRecommendation(
        name="deepseek-coder-v2:16b",
        display_name="DeepSeek Coder V2 16B",
        role="coder",
        vram_required_gb=12.0,
        pull_command="ollama pull deepseek-coder-v2:16b",
        description="Kod üretiminde en güçlü seçenek."
    ),
    ModelRecommendation(
        name="qwen2.5-coder:7b",
        display_name="Qwen2.5 Coder 7B",
        role="coder",
        vram_required_gb=5.0,
        pull_command="ollama pull qwen2.5-coder:7b",
        description="Hızlı, hassas, çok dilli kod üretimi. 8GB VRAM için ideal."
    ),
    ModelRecommendation(
        name="deepseek-coder:6.7b",
        display_name="DeepSeek Coder 6.7B",
        role="coder",
        vram_required_gb=5.0,
        pull_command="ollama pull deepseek-coder:6.7b",
        description="Kod odaklı, güçlü tamamlama yeteneği."
    ),
    ModelRecommendation(
        name="qwen2.5-coder:3b",
        display_name="Qwen2.5 Coder 3B",
        role="coder",
        vram_required_gb=2.5,
        pull_command="ollama pull qwen2.5-coder:3b",
        description="Düşük VRAM için hafif kodlama modeli."
    ),
    ModelRecommendation(
        name="phi3:mini",
        display_name="Phi-3 Mini",
        role="coder",
        vram_required_gb=0.0,
        pull_command="ollama pull phi3:mini",
        description="CPU'da çalışır. GPU yoksa tek seçenek."
    ),
]


# ─────────────────────────────────────────
# Öneri Motoru
# ─────────────────────────────────────────

def _effective_vram(info: SystemInfo) -> float:
    """
    Kullanılabilir VRAM hesaplar.
    Apple Unified Memory → RAM'in %60'ı.
    NVIDIA/AMD → direkt VRAM.
    CPU only → 0.
    """
    if info.gpu_vendor == "apple":
        return info.ram_gb * 0.6
    if info.gpu_vendor in ("nvidia", "amd"):
        return info.vram_gb
    return 0.0


def recommend(info: SystemInfo) -> dict:
    """
    SystemInfo'ya göre planlama ve kodlama model önerilerini döner.

    Returns:
        {
            "planner": [ModelRecommendation, ...],  # En uygundan en azına
            "coder":   [ModelRecommendation, ...],
            "effective_vram_gb": float
        }
    """
    vram = _effective_vram(info)

    def filter_models(models: list) -> list:
        # VRAM'e sığan modelleri filtrele, büyükten küçüğe sırala
        fitting = [
            m for m in models
            if m.vram_required_gb <= vram or m.vram_required_gb == 0.0
        ]
        fitting.sort(key=lambda m: m.vram_required_gb, reverse=True)
        return fitting if fitting else [models[-1]]  # En az gereksinimlisi

    planner_list = filter_models(PLANNER_MODELS)
    coder_list = filter_models(CODER_MODELS)

    # En iyi seçimi işaretle
    if planner_list:
        planner_list[0].is_best = True
    if coder_list:
        coder_list[0].is_best = True

    return {
        "planner": planner_list,
        "coder": coder_list,
        "effective_vram_gb": vram,
    }


def get_all_model_names() -> list[str]:
    """Tüm bilinen model isimlerini döner (manuel giriş için referans)."""
    names = [m.name for m in PLANNER_MODELS + CODER_MODELS]
    return sorted(set(names))


if __name__ == "__main__":
    from core.system_scanner import scan
    info = scan()
    result = recommend(info)
    print(f"\nEfektif VRAM: {result['effective_vram_gb']} GB")
    print("\nPlanlama Modelleri:")
    for m in result["planner"]:
        star = "⭐" if m.is_best else "  "
        print(f"  {star} {m.display_name} ({m.vram_required_gb}GB) — {m.description}")
    print("\nKodlama Modelleri:")
    for m in result["coder"]:
        star = "⭐" if m.is_best else "  "
        print(f"  {star} {m.display_name} ({m.vram_required_gb}GB) — {m.description}")
