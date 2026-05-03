"""
LocalForge — System Scanner
GPU, RAM, VRAM, OS ve LLM backend durumunu tespit eder.
"""

import platform
import subprocess
import psutil
import requests
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class SystemInfo:
    os: str
    cpu_cores: int
    ram_gb: float
    gpu_name: str
    vram_gb: float
    gpu_vendor: str          # "nvidia" | "amd" | "apple" | "none"
    ollama_available: bool
    ollama_version: str
    lmstudio_available: bool
    ollama_url: str
    lmstudio_url: str

    def to_dict(self) -> dict:
        return asdict(self)


def _detect_nvidia_gpu() -> tuple[str, float]:
    """nvidia-smi ile GPU adı ve VRAM döner. (name, vram_gb)"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            line = result.stdout.strip().split("\n")[0]
            parts = line.split(",")
            name = parts[0].strip()
            vram_mb = float(parts[1].strip())
            return name, round(vram_mb / 1024, 1)
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    return "", 0.0


def _detect_amd_gpu() -> tuple[str, float]:
    """rocm-smi ile AMD GPU bilgisi. (name, vram_gb)"""
    try:
        result = subprocess.run(
            ["rocm-smi", "--showproductname"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.splitlines():
                if "GPU" in line and ":" in line:
                    name = line.split(":", 1)[1].strip()
                    return name, 0.0  # VRAM AMD'de ayrı sorgu
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "", 0.0


def _detect_apple_gpu() -> tuple[str, float]:
    """Apple Silicon tespiti."""
    if platform.system() == "Darwin" and platform.processor() == "arm":
        cpu = platform.machine()
        # Unified memory paylaşımlı — toplam RAM'in yarısı GPU için kabul edilir
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        return f"Apple Silicon ({cpu})", round(ram_gb / 2, 1)
    return "", 0.0


def _check_ollama(url: str) -> tuple[bool, str]:
    """Ollama çalışıyor mu, versiyonu ne? (available, version)"""
    try:
        resp = requests.get(f"{url}/api/version", timeout=3)
        if resp.status_code == 200:
            version = resp.json().get("version", "bilinmiyor")
            return True, version
    except Exception:
        pass
    # CLI fallback
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
    except FileNotFoundError:
        pass
    return False, ""


def _check_lmstudio(url: str) -> bool:
    """LM Studio /v1/models endpoint'ine ping atar."""
    try:
        resp = requests.get(f"{url}/v1/models", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def scan(
    ollama_url: str = "http://localhost:11434",
    lmstudio_url: str = "http://localhost:1234"
) -> SystemInfo:
    """
    Tam sistem taraması yapar ve SystemInfo döner.
    """
    # OS
    os_name = f"{platform.system()} {platform.release()}"

    # CPU
    cpu_cores = psutil.cpu_count(logical=False) or psutil.cpu_count()

    # RAM
    ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)

    # GPU tespiti (öncelik sırası: NVIDIA → AMD → Apple → Yok)
    gpu_name, vram_gb, gpu_vendor = "", 0.0, "none"

    nvidia_name, nvidia_vram = _detect_nvidia_gpu()
    if nvidia_name:
        gpu_name, vram_gb, gpu_vendor = nvidia_name, nvidia_vram, "nvidia"
    else:
        amd_name, amd_vram = _detect_amd_gpu()
        if amd_name:
            gpu_name, vram_gb, gpu_vendor = amd_name, amd_vram, "amd"
        else:
            apple_name, apple_vram = _detect_apple_gpu()
            if apple_name:
                gpu_name, vram_gb, gpu_vendor = apple_name, apple_vram, "apple"

    # Backend kontrolü
    ollama_available, ollama_version = _check_ollama(ollama_url)
    lmstudio_available = _check_lmstudio(lmstudio_url)

    return SystemInfo(
        os=os_name,
        cpu_cores=cpu_cores,
        ram_gb=ram_gb,
        gpu_name=gpu_name or "Tespit edilemedi",
        vram_gb=vram_gb,
        gpu_vendor=gpu_vendor,
        ollama_available=ollama_available,
        ollama_version=ollama_version,
        lmstudio_available=lmstudio_available,
        ollama_url=ollama_url,
        lmstudio_url=lmstudio_url,
    )


def get_installed_ollama_models(ollama_url: str) -> list[str]:
    """Ollama'da kurulu modelleri listeler."""
    try:
        resp = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return [m["name"] for m in models]
    except Exception:
        pass
    return []


def get_installed_lmstudio_models(lmstudio_url: str) -> list[str]:
    """LM Studio'da yüklü modelleri listeler."""
    try:
        resp = requests.get(f"{lmstudio_url}/v1/models", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("data", [])
            return [m["id"] for m in models]
    except Exception:
        pass
    return []


if __name__ == "__main__":
    # Test
    info = scan()
    print(json.dumps(info.to_dict(), indent=2, ensure_ascii=False))
