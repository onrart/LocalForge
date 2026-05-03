"""
LocalForge — Coder Agent
Görev listesini alıp sırayla dosyaları üretir.
Syntax doğrulama, bağımlılık tespiti ve checkpoint yönetimini koordine eder.
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


@dataclass
class CoderSession:
    project_path: str
    total_tasks: int = 0
    completed_tasks: int = 0
    task_results: list[TaskResult] = field(default_factory=list)
    stopped: bool = False

    @property
    def progress_pct(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100


def _load_prompt() -> str:
    """prompts/coder.md dosyasını okur."""
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
        """UI'dan durdurma sinyali."""
        self._stop_requested = True

    def run(self) -> Generator[dict, None, None]:
        """
        Tüm görev döngüsünü çalıştırır.
        Her adımda durum dict'i yield eder — Streamlit UI bunu canlı gösterir.

        Yield edilen dict formatı:
        {
            "type": "task_start" | "token" | "task_done" | "approval_needed"
                    | "error" | "session_done",
            "task": str,
            "data": any
        }
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

            # Kod üret (retry döngüsü ile)
            result = yield from self._run_task_with_retry(task_name)

            if not result.success:
                yield {
                    "type": "error",
                    "task": task_name,
                    "data": {"error": result.error},
                }
                if self.approval_mode:
                    yield {
                        "type": "approval_needed",
                        "task": task_name,
                        "data": {
                            "action": "error_skip",
                            "message": f"Görev başarısız: {result.error}. Devam edilsin mi?",
                        },
                    }
                continue

            # Onay modu
            if self.approval_mode:
                yield {
                    "type": "approval_needed",
                    "task": task_name,
                    "data": {
                        "action": "approve_task",
                        "files": result.files_written,
                        "deps": result.deps_added,
                        "skipped": result.skipped_files,
                    },
                }
                # UI onay verinceye kadar bekler — generator dışarıdan .send() ile devam ettirilir
                approval = yield {
                    "type": "waiting_approval",
                    "task": task_name,
                    "data": {},
                }
                if approval == "skip":
                    yield {"type": "task_skipped", "task": task_name, "data": {}}
                    continue
                elif approval == "stop":
                    self._stop_requested = True
                    yield {"type": "stopped", "task": task_name, "data": {}}
                    break

            # Checkpoint kaydet
            self.ctx.save_checkpoint(task_name, result.files_written)

            # TASKS.md güncelle
            self.ctx.mark_task_done(task_name)

            # PROGRESS.md güncelle
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

        yield {
            "type": "session_done",
            "task": "",
            "data": {
                "completed": len(pending),
            },
        }

    def _run_task_with_retry(self, task_name: str) -> Generator[dict, None, TaskResult]:
        """
        Tek görevi çalıştırır. Syntax hatası varsa max 2 kez retry eder.
        """
        context = self.ctx.build_context(role="coder")
        user_message = f"Şu görevi kodla: **{task_name}**\n\n{context}"
        full_response = ""
        syntax_retries = 0

        for attempt in range(MAX_SYNTAX_RETRIES + 1):
            full_response = ""

            # Streaming ile LLM çağrısı
            for token in self.client.stream(
                system_prompt=self.system_prompt,
                user_message=user_message,
                max_tokens=2048,
                temperature=0.2,
            ):
                full_response += token
                yield {"type": "token", "task": task_name, "data": {"token": token}}

            # Dosyaları parse et
            parsed_files = parse_llm_output(full_response)

            if not parsed_files:
                return TaskResult(
                    task_name=task_name,
                    success=False,
                    error="LLM dosya bloğu üretmedi. Prompt veya model yanıtı beklenen formatta değil.",
                )

            # Syntax doğrulama
            has_error = False
            error_hints = []

            for pf in parsed_files:
                result = validate(pf.path, pf.content)
                if not result.valid:
                    has_error = True
                    error_hints.append(result.fix_hint)
                    yield {
                        "type": "syntax_error",
                        "task": task_name,
                        "data": {
                            "file": pf.path,
                            "error": result.error,
                            "attempt": attempt + 1,
                        },
                    }

            if has_error and attempt < MAX_SYNTAX_RETRIES:
                syntax_retries += 1
                fix_prompt = build_fix_prompt(
                    user_message,
                    full_response,
                    type("R", (), {"fix_hint": "\n".join(error_hints)})(),
                )
                user_message = fix_prompt
                yield {
                    "type": "retry",
                    "task": task_name,
                    "data": {"attempt": attempt + 2},
                }
                continue

            if has_error:
                # Max retry aşıldı → kullanıcıya devret
                yield {
                    "type": "syntax_failed",
                    "task": task_name,
                    "data": {
                        "message": "Syntax hatası düzeltilemedi. Manuel müdahale gerekiyor."
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

            # MEMORY.md güncelle (yeni bağımlılıklar)
            if all_deps_added:
                self.ctx.append_to_memory(
                    "Mimari Kararlar",
                    f"{task_name} görevi → requirements.txt'e eklendi: {', '.join(all_deps_added)}",
                )

            return TaskResult(
                task_name=task_name,
                success=session.success_count > 0,
                files_written=session.all_paths,
                deps_added=all_deps_added,
                skipped_files=session.files_skipped,
                syntax_retries=syntax_retries,
                error="" if session.success_count > 0 else "Hiçbir dosya yazılamadı.",
            )

        return TaskResult(
            task_name=task_name,
            success=False,
            error="Maksimum retry sayısı aşıldı.",
        )

    def _build_task_details(self, task_name: str) -> str:
        """CURRENT_TASK.md için görev detayı üretir."""
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

### Önemli Kurallar
- PROGRESS.md'de listeli dosyaları yeniden yazma
- MEMORY.md'deki pattern'leri değiştirme
- Her dosyayı `# Dosya: yol` başlığıyla ayrı kod bloğunda ver
"""
