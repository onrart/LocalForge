"""
LocalForge — Editor Agent
Kullanıcının doğal dil isteğine göre mevcut dosyaları düzenler.
Diff üretir, kullanıcı onayı alır, MEMORY.md'ye kaydeder.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Generator

from core.llm_client import LLMClient
from core.context_manager import ContextManager
from core.syntax_validator import validate
from core.file_writer import (
    parse_llm_output,
    write_file,
    _generate_diff,
    summarize_diff,
)


@dataclass
class EditRequest:
    instruction: str  # Kullanıcının doğal dil isteği
    target_file: str  # Düzenlenecek dosya yolu (göreli)
    context_hint: str = ""  # Ek bağlam (opsiyonel)


@dataclass
class EditResult:
    success: bool
    file_path: str
    diff: str = ""
    diff_summary: dict = None
    new_content: str = ""
    error: str = ""
    change_summary: str = ""  # LLM'in ürettiği değişiklik özeti

    def __post_init__(self):
        if self.diff_summary is None:
            self.diff_summary = {"added": 0, "removed": 0}


def _load_prompt() -> str:
    """prompts/editor.md dosyasını okur."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "editor.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return (
        "Sen bir yazılım geliştiricisin. Mevcut dosyayı kullanıcının isteğine göre düzenle. "
        "Önce '## Değişiklikler:' başlığıyla 1-2 cümle özet yaz, "
        "sonra '# Dosya: yol' başlığıyla tam dosya içeriğini ver."
    )


class EditorAgent:
    def __init__(
        self,
        client: LLMClient,
        context_manager: ContextManager,
        project_path: str | Path,
    ):
        self.client = client
        self.ctx = context_manager
        self.project_path = Path(project_path)
        self.system_prompt = _load_prompt()

    def edit_stream(self, request: EditRequest) -> Generator[str, None, EditResult]:
        """
        Düzenleme isteğini streaming olarak işler.
        Her token yield edilir (UI canlı gösterim için).
        Bittikten sonra EditResult döner.
        """
        # Mevcut dosya içeriğini oku
        file_path = self.project_path / request.target_file
        if not file_path.exists():
            yield f"❌ Dosya bulunamadı: {request.target_file}"
            return EditResult(
                success=False,
                file_path=request.target_file,
                error=f"Dosya bulunamadı: {request.target_file}",
            )

        old_content = file_path.read_text(encoding="utf-8")

        # Bağlam hazırla
        memory = self.ctx.read_file("MEMORY.md")
        project = self.ctx.read_file("PROJECT.md")

        user_message = self._build_user_message(
            request=request,
            old_content=old_content,
            memory=memory,
            project=project,
        )

        # Streaming
        full_response = ""
        for token in self.client.stream(
            system_prompt=self.system_prompt,
            user_message=user_message,
            max_tokens=2048,
            temperature=0.2,
        ):
            full_response += token
            yield token

        # Parse
        parsed_files = parse_llm_output(full_response)

        if not parsed_files:
            return EditResult(
                success=False,
                file_path=request.target_file,
                error="LLM dosya bloğu üretmedi.",
            )

        parsed = parsed_files[0]  # Editörde tek dosya beklenir

        # Değişiklik özeti ayıkla
        change_summary = self._extract_summary(full_response)

        # Syntax doğrula
        validation = validate(parsed.path, parsed.content)
        if not validation.valid:
            return EditResult(
                success=False,
                file_path=request.target_file,
                error=f"Syntax hatası: {validation.error}",
                new_content=parsed.content,
            )

        # Diff üret (henüz yazmadan)
        diff = _generate_diff(old_content, parsed.content, parsed.path)
        diff_summary = summarize_diff(diff)

        return EditResult(
            success=True,
            file_path=parsed.path,
            diff=diff,
            diff_summary=diff_summary,
            new_content=parsed.content,
            change_summary=change_summary,
        )

    def apply_edit(self, result: EditResult) -> bool:
        """
        Kullanıcı onayladıktan sonra düzenlemeyi diske yazar.
        MEMORY.md'ye not düşer.
        """
        from core.file_writer import ParsedFile

        if not result.success or not result.new_content:
            return False

        pf = ParsedFile(
            path=result.file_path,
            content=result.new_content,
            language="python",
        )

        write_result = write_file(pf, self.project_path)

        if write_result.success:
            # MEMORY.md'ye düzenleme notu
            diff_s = result.diff_summary
            summary = f"+{diff_s['added']}/-{diff_s['removed']} satır"
            self.ctx.record_manual_edit(
                result.file_path, f"{result.change_summary} ({summary})"
            )
            return True

        return False

    def apply_manual_edit(
        self,
        file_path: str,
        new_content: str,
        old_content: str,
    ) -> dict:
        """
        Kullanıcı UI'dan direkt kod düzenlediğinde çağrılır.
        Diske yazar ve MEMORY.md'ye not düşer.
        LLM bağlamına sync edilmesi için kullanılır.
        """
        from core.file_writer import ParsedFile

        pf = ParsedFile(path=file_path, content=new_content, language="python")
        write_result = write_file(pf, self.project_path)

        if not write_result.success:
            return {"success": False, "error": write_result.error}

        # Diff üret
        diff = _generate_diff(old_content, new_content, file_path)
        diff_summary = summarize_diff(diff)
        summary = f"+{diff_summary['added']}/-{diff_summary['removed']} satır"

        # MEMORY.md'ye kaydet (LLM bir sonraki çağrıda görecek)
        self.ctx.record_manual_edit(file_path, f"Direkt UI düzenlemesi — {summary}")

        return {
            "success": True,
            "diff": diff,
            "diff_summary": diff_summary,
        }

    def _build_user_message(
        self,
        request: EditRequest,
        old_content: str,
        memory: str,
        project: str,
    ) -> str:
        context_section = (
            f"\n### Ek Bağlam\n{request.context_hint}" if request.context_hint else ""
        )

        return f"""## Proje
{project}

## Mimari Kararlar (MEMORY)
{memory}

## Düzenleme İsteği
{request.instruction}
{context_section}

## Mevcut Dosya: {request.target_file}
```
{old_content}
```

Yukarıdaki dosyayı isteğe göre düzenle.
Önce '## Değişiklikler:' başlığıyla kısa özet yaz.
Sonra '# Dosya: {request.target_file}' başlığıyla dosyanın tamamını ver."""

    def _extract_summary(self, response: str) -> str:
        """LLM yanıtından '## Değişiklikler:' bölümünü ayıklar."""
        if "## Değişiklikler:" in response:
            lines = response.split("## Değişiklikler:")[1].strip().splitlines()
            summary_lines = []
            for line in lines:
                if line.startswith("#") or line.startswith("```"):
                    break
                if line.strip():
                    summary_lines.append(line.strip())
            return " ".join(summary_lines[:2])
        return "Düzenleme yapıldı."
