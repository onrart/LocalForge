"""
LocalForge — Planner Agent
Proje gereksinimlerini alıp ARCHITECTURE.md ve TASKS.md üretir.
Planlama modeli kullanır (genellikle daha büyük model).
"""

import re
from pathlib import Path
from typing import Generator, Optional

from core.llm_client import LLMClient
from core.context_manager import ContextManager
from core.requirements_collector import ProjectRequirements, _generate_requirements_md


def _load_prompt() -> str:
    """prompts/planner.md dosyasını okur."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "planner.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    # Fallback: inline prompt
    return (
        "Sen bir yazılım mimarısın. Proje gereksinimlerini alıp "
        "ARCHITECTURE.md ve TASKS.md içeriği üret. "
        "Yanıtını ===ARCHITECTURE=== ve ===TASKS=== ayraçlarıyla böl."
    )


def _parse_response(response: str) -> tuple[str, str]:
    """
    LLM yanıtından ARCHITECTURE ve TASKS içeriklerini ayıklar.
    Returns: (architecture_md, tasks_md)
    """
    arch_match = re.search(r"===ARCHITECTURE===(.*?)===TASKS===", response, re.DOTALL)
    tasks_match = re.search(r"===TASKS===(.*?)$", response, re.DOTALL)

    architecture = arch_match.group(1).strip() if arch_match else ""
    tasks = tasks_match.group(1).strip() if tasks_match else ""

    # Fallback: Ayraç yoksa tüm yanıtı architecture say
    if not architecture and not tasks:
        architecture = response.strip()
        tasks = _generate_default_tasks()

    return architecture, tasks


def _generate_default_tasks() -> str:
    """LLM parse başarısız olursa minimum görev listesi üretir."""
    return """## Görevler

- [ ] 01_proje_iskeleti        # Temel klasör yapısı ve bağımlılıklar
- [ ] 02_ana_modul             # Ana uygulama modülü
- [ ] 03_ozellikler            # Temel özellikler
- [ ] 04_testler               # Temel testler
- [ ] 05_readme                # Dokümantasyon
"""


def _validate_tasks_md(tasks_md: str) -> str:
    """
    TASKS.md formatını doğrular ve düzeltir.
    Her satırın doğru formatta olduğunu kontrol eder.
    """
    lines = tasks_md.splitlines()
    result = []
    has_header = False

    for line in lines:
        stripped = line.strip()
        # Başlık satırı
        if stripped.startswith("## Görevler"):
            has_header = True
            result.append(stripped)
        # Görev satırı
        elif stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
            result.append(stripped)
        # Diğer satırlar (boş veya yorum)
        elif not stripped or stripped.startswith("#"):
            result.append(stripped)

    if not has_header:
        result.insert(0, "## Görevler\n")

    return "\n".join(result)


class PlannerAgent:
    def __init__(self, client: LLMClient, context_manager: ContextManager):
        self.client = client
        self.ctx = context_manager
        self.system_prompt = _load_prompt()

    def plan(self, requirements: ProjectRequirements) -> dict:
        """
        Senkron planlama. ARCHITECTURE.md ve TASKS.md üretir.

        Returns:
            {
                "success": bool,
                "architecture": str,
                "tasks": str,
                "task_count": int,
                "error": str
            }
        """
        user_message = self._build_user_message(requirements)

        response = self.client.complete(
            system_prompt=self.system_prompt,
            user_message=user_message,
            max_tokens=3000,
            temperature=0.3,
        )

        if not response.success:
            return {
                "success": False,
                "architecture": "",
                "tasks": "",
                "task_count": 0,
                "error": response.error,
            }

        architecture, tasks = _parse_response(response.content)
        tasks = _validate_tasks_md(tasks)

        # Context manager'a yaz
        self.ctx.write_architecture(architecture)
        self.ctx.write_tasks(tasks)

        task_count = tasks.count("- [ ]")

        return {
            "success": True,
            "architecture": architecture,
            "tasks": tasks,
            "task_count": task_count,
            "error": "",
        }

    def plan_stream(
        self, requirements: ProjectRequirements
    ) -> Generator[str, None, None]:
        """
        Streaming planlama. UI'da canlı gösterim için.
        Tam yanıt bittikten sonra dosyalara yazar.
        """
        user_message = self._build_user_message(requirements)
        full_response = ""

        yield "🧠 Mimari planlanıyor...\n\n"

        for token in self.client.stream(
            system_prompt=self.system_prompt,
            user_message=user_message,
            max_tokens=3000,
            temperature=0.3,
        ):
            full_response += token
            yield token

        # Streaming bitti, parse et ve kaydet
        architecture, tasks = _parse_response(full_response)
        tasks = _validate_tasks_md(tasks)

        self.ctx.write_architecture(architecture)
        self.ctx.write_tasks(tasks)

        task_count = tasks.count("- [ ]")
        yield f"\n\n✅ Planlama tamamlandı — {task_count} görev oluşturuldu."

    def _build_user_message(self, requirements: ProjectRequirements) -> str:
        """LLM'e gönderilecek kullanıcı mesajını hazırlar."""
        summary = requirements.to_summary()
        template_note = ""
        if requirements.detected_template:
            template_note = (
                f"\n\nNOT: Kullanıcı '{requirements.detected_template}' şablonunu seçti. "
                f"Mimariyi bu şablona uygun planla ama gereksinim farklılıklarını yansıt."
            )

        return f"""Aşağıdaki proje için ARCHITECTURE.md ve TASKS.md içeriği üret:

{summary}{template_note}

Yanıtını ===ARCHITECTURE=== ve ===TASKS=== ayraçlarıyla böl."""

    def get_task_details(self, task_name: str) -> str:
        """
        Belirli bir görev için CURRENT_TASK.md içeriği üretir.
        Ayrı bir LLM çağrısı yapmadan, architecture'dan çıkarım yapar.
        """
        architecture = self.ctx.read_file("ARCHITECTURE.md")
        tasks = self.ctx.read_file("TASKS.md")

        # Görev sırasını bul
        all_tasks = self.ctx.get_all_tasks()
        task_index = next(
            (i for i, t in enumerate(all_tasks) if t["name"] == task_name), 0
        )
        total = len(all_tasks)

        return f"""## Görev: {task_name}
### Sıra: {task_index + 1} / {total}

### Mimari Bağlam
{architecture[:500]}...

### Bu Görevde Yapılacaklar
Görev adından anlaşıldığı üzere `{task_name}` ile ilgili dosyaları üret.
Mimari kararlara ve MEMORY.md'deki pattern'lere uy.

### Dikkat Edilecekler
- Önceki görevlerde oluşturulan dosyaları import edebilirsin (PROGRESS.md'ye bak)
- Yeni bir bağımlılık ekliyorsan requirements.txt'e de ekle
- Dosya isimleri ve klasör yapısı ARCHITECTURE.md ile tutarlı olmalı
"""
