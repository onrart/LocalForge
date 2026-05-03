"""
LocalForge — LLM Client
Ollama ve LM Studio için tek arayüz.
Her ikisi de OpenAI-uyumlu /v1/chat/completions kullanır.
"""

import json
import time
import requests
from typing import Generator, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model: str
    total_tokens: int
    success: bool
    error: str = ""


class LLMClient:
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # saniye

    def __init__(
        self,
        backend: str,  # "ollama" | "lmstudio"
        model: str,
        base_url: str,
    ):
        self.backend = backend
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._endpoint = f"{self.base_url}/v1/chat/completions"

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """
        Tek seferlik tamamlama. Hata durumunda MAX_RETRIES kez dener.
        """
        messages = self._build_messages(system_prompt, user_message)
        payload = self._build_payload(messages, max_tokens, temperature, stream=False)

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                resp = requests.post(self._endpoint, json=payload, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)
                return LLMResponse(
                    content=content, model=self.model, total_tokens=tokens, success=True
                )
            except requests.exceptions.ConnectionError:
                error = f"Bağlantı hatası ({self.backend} çalışıyor mu?)"
            except requests.exceptions.Timeout:
                error = "Zaman aşımı (model çok yavaş yanıt veriyor)"
            except requests.exceptions.HTTPError as e:
                error = f"HTTP hatası: {e}"
            except (KeyError, json.JSONDecodeError) as e:
                error = f"Yanıt parse hatası: {e}"

            if attempt < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY)

        return LLMResponse(
            content="", model=self.model, total_tokens=0, success=False, error=error
        )

    def stream(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        """
        Streaming tamamlama. Her token geldiğinde yield eder.
        UI'da canlı gösterim için kullanılır.
        """
        messages = self._build_messages(system_prompt, user_message)
        payload = self._build_payload(messages, max_tokens, temperature, stream=True)

        try:
            with requests.post(
                self._endpoint, json=payload, stream=True, timeout=120
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]":
                        break
                    try:
                        data = json.loads(line)
                        delta = data["choices"][0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError):
                        continue
        except requests.exceptions.ConnectionError:
            yield f"\n\n❌ Bağlantı hatası: {self.backend} çalışıyor mu?"
        except requests.exceptions.Timeout:
            yield "\n\n❌ Zaman aşımı."
        except Exception as e:
            yield f"\n\n❌ Hata: {e}"

    def is_alive(self) -> bool:
        """Backend'in ayakta olup olmadığını kontrol eder."""
        try:
            if self.backend == "ollama":
                resp = requests.get(f"{self.base_url}/api/version", timeout=3)
            else:
                resp = requests.get(f"{self.base_url}/v1/models", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """Backend'deki mevcut modelleri listeler."""
        try:
            if self.backend == "ollama":
                resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
                if resp.status_code == 200:
                    return [m["name"] for m in resp.json().get("models", [])]
            else:
                resp = requests.get(f"{self.base_url}/v1/models", timeout=5)
                if resp.status_code == 200:
                    return [m["id"] for m in resp.json().get("data", [])]
        except Exception:
            pass
        return []

    # ─────────────────────────────────────────
    # Private Helpers
    # ─────────────────────────────────────────

    def _build_messages(self, system_prompt: str, user_message: str) -> list:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        return messages

    def _build_payload(
        self, messages: list, max_tokens: int, temperature: float, stream: bool
    ) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }


# ─────────────────────────────────────────
# Factory
# ─────────────────────────────────────────


def create_client(config: dict, role: str = "coder") -> LLMClient:
    """
    config.json'dan LLMClient oluşturur.
    role: "planner" | "coder"
    """
    backend = config.get("backend", "ollama")
    model_key = f"{role}_model"
    model = config.get(model_key, "")

    if backend == "ollama":
        base_url = config.get("ollama_url", "http://localhost:11434")
    else:
        base_url = config.get("lmstudio_url", "http://localhost:1234")

    return LLMClient(backend=backend, model=model, base_url=base_url)


if __name__ == "__main__":
    import json

    with open("config.json") as f:
        config = json.load(f)

    client = create_client(config, role="coder")
    print(f"Backend: {client.backend}")
    print(f"Model: {client.model}")
    print(f"Alive: {client.is_alive()}")
    print(f"Models: {client.list_models()}")
