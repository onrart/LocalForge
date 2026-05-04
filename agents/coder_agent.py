"""
LocalForge — Coder Agent
Görev listesini alıp sırayla dosyaları üretir.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

from core.llm_client import LLMClient
from core.context_manager import ContextManager
from core.syntax_validator import validate, build_fix_prompt
from core.dependency_scanner import scan_and_update
from core.file_writer import parse_llm_output, write_files, WriteSession

MAX_SYNTAX_RETRIES = 2


@dataclass
class TaskResult:
    task_name: str
    success: bool
    files_written: list[str] = field(default_factory=list)
    deps_added: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    error: str = ""
    syntax_retries: int = 0


def _load_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "coder.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return (
        "Sen bir yazılım geliştiricisin. "
        "Verilen görevi kodla. Her dosyayı '# Dosya: yol' başlığıyla "
        "ayrı bir kod bloğu içinde ver."
    )


class CoderAgent:
    def __init__(
        self,
        client: LLMClient,
        context_manager: ContextManager,
        project_path: str | Path,
        approval_mode: bool = False,
    ):
        self.client = client
        self.ctx = context_manager
        self.project_path = Path(project_path)
        self.approval_mode = approval_mode
        self.system_prompt = _load_prompt()
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self) -> Generator[dict, None, None]:
        """
        Tüm görev döngüsünü çalıştırır.
        Onay modu: her task_done sonrası "approval_needed" yield eder.
        UI tarafı next() çağırmadan önce kullanıcıdan onay alır.
        """
        pending = self.ctx.get_pending_tasks()
        total = len(pending)

        if total == 0:
            yield {
                "type": "session_done",
                "task": "",
                "data": {"message": "Tüm görevler zaten tamamlanmış."},
            }
            return

        yield {"type": "session_start", "task": "", "data": {"total": total}}

        for i, task_name in enumerate(pending):
            if self._stop_requested:
                yield {"type": "stopped", "task": task_name, "data": {}}
                break

            yield {
                "type": "task_start",
                "task": task_name,
                "data": {"index": i + 1, "total": total},
            }

            # CURRENT_TASK.md güncelle
            task_details = self._build_task_details(task_name)
            self.ctx.set_current_task(task_name, task_details)

            # Kod üret
            result = yield from self._run_task_with_retry(task_name)

            if not result.success:
                yield {
                    "type": "error",
                    "task": task_name,
                    "data": {"error": result.error},
                }
                continue

            # Checkpoint kaydet
            self.ctx.save_checkpoint(task_name, result.files_written)
            self.ctx.mark_task_done(task_name)
            self.ctx.append_to_progress(task_name, result.files_written)

            yield {
                "type": "task_done",
                "task": task_name,
                "data": {
                    "files": result.files_written,
                    "deps": result.deps_added,
                    "skipped": result.skipped_files,
                    "retries": result.syntax_retries,
                },
            }

            # Onay modu — UI next() çağırmadan önce kullanıcıdan onay alır
            # Generator burada yield ile durur, UI istediği zaman devam ettirir
            if self.approval_mode:
                yield {
                    "type": "approval_needed",
                    "task": task_name,
                    "data": {
                        "files": result.files_written,
                        "deps": result.deps_added,
                    },
                }

        yield {
            "type": "session_done",
            "task": "",
            "data": {
                "completed": len(pending),
            },
        }

    def _run_task_with_retry(self, task_name: str) -> Generator[dict, None, TaskResult]:
        """Tek görevi çalıştırır. Syntax hatası varsa max 2 kez retry eder."""
        context = self.ctx.build_context(role="coder")
        user_message = f"Şu görevi kodla: **{task_name}**\n\n{context}"
        syntax_retries = 0

        for attempt in range(MAX_SYNTAX_RETRIES + 1):
            full_response = ""

            for token in self.client.stream(
                system_prompt=self.system_prompt,
                user_message=user_message,
                max_tokens=2048,
                temperature=0.2,
            ):
                full_response += token
                yield {"type": "token", "task": task_name, "data": {"token": token}}

            parsed_files = parse_llm_output(full_response)

            if not parsed_files:
                if attempt < MAX_SYNTAX_RETRIES:
                    yield {
                        "type": "retry",
                        "task": task_name,
                        "data": {"attempt": attempt + 2},
                    }
                    user_message = (
                        f"{user_message}\n\nÖNCEKİ YANIT HATALI: Dosya bloğu bulunamadı.\n"
                        f"'# Dosya: yol' formatında, her dosyayı ayrı ```python bloğunda yaz."
                    )
                    continue
                return TaskResult(
                    task_name=task_name,
                    success=False,
                    error="LLM dosya bloğu üretmedi.",
                )

            # Syntax doğrulama
            has_error = False
            error_hints = []

            for pf in parsed_files:
                vr = validate(pf.path, pf.content)
                if not vr.valid:
                    has_error = True
                    error_hints.append(vr.fix_hint)
                    yield {
                        "type": "syntax_error",
                        "task": task_name,
                        "data": {
                            "file": pf.path,
                            "error": vr.error,
                            "attempt": attempt + 1,
                        },
                    }

            if has_error and attempt < MAX_SYNTAX_RETRIES:
                syntax_retries += 1
                fix_hint = "\n".join(error_hints)
                user_message = (
                    f"Aşağıdaki kodda syntax hatası var. SADECE hatayı düzelt:\n\n"
                    f"HATA:\n{fix_hint}\n\n"
                    f"Düzeltilmiş kodun tamamını # Dosya: yol formatında yaz."
                )
                yield {
                    "type": "retry",
                    "task": task_name,
                    "data": {"attempt": attempt + 2},
                }
                continue

            if has_error:
                yield {
                    "type": "syntax_failed",
                    "task": task_name,
                    "data": {
                        "message": f"{task_name}: Syntax hatası düzeltilemedi, dosyalar yine de kaydedildi."
                    },
                }

            # Dosyaları yaz
            manually_edited = self.ctx.get_manually_edited_files()
            session: WriteSession = write_files(
                parsed_files, self.project_path, manually_edited
            )

            # Bağımlılık tara
            all_deps_added = []
            for pf in parsed_files:
                if pf.language == "python":
                    added = scan_and_update(pf.content, self.project_path)
                    all_deps_added.extend(added)

            if all_deps_added:
                self.ctx.append_to_memory(
                    "Mimari Kararlar",
                    f"{task_name} → requirements.txt'e eklendi: {', '.join(all_deps_added)}",
                )

            return TaskResult(
                task_name=task_name,
                success=session.success_count > 0 or bool(parsed_files),
                files_written=session.all_paths,
                deps_added=all_deps_added,
                skipped_files=session.files_skipped,
                syntax_retries=syntax_retries,
                error="" if session.success_count > 0 else "Dosya yazılamadı.",
            )

        return TaskResult(
            task_name=task_name,
            success=False,
            error="Maksimum retry sayısı aşıldı.",
        )

    def _build_task_details(self, task_name: str) -> str:
        all_tasks = self.ctx.get_all_tasks()
        index = next((i for i, t in enumerate(all_tasks) if t["name"] == task_name), 0)
        total = len(all_tasks)
        completed = [t["name"] for t in all_tasks if t["done"]]
        completed_str = (
            "\n".join(f"- ✅ {t}" for t in completed) if completed else "- Henüz yok"
        )

        return f"""### Sıra: {index + 1} / {total}

### Tamamlanan Görevler
{completed_str}

### Bu Görevde Yapılacaklar
`{task_name}` ile ilgili dosyaları üret.
ARCHITECTURE.md'deki yapıya ve MEMORY.md'deki kararlara uy.

### Kurallar
- PROGRESS.md'de listeli dosyaları yeniden yazma
- MEMORY.md'deki pattern'leri değiştirme
- Her dosyayı `# Dosya: yol` başlığıyla ayrı kod bloğunda ver
- Tüm import'ların eksiksiz olduğunu kontrol et
"""
